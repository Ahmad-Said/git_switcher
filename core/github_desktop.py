import base64
import ctypes
import ctypes.wintypes as wintypes
import json
import shutil
import subprocess
import sys
import time
from typing import Optional, Tuple

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

from utils.paths import (
    get_github_desktop_config_dir,
    get_profile_backup_dir,
    get_profile_credentials_file,
    get_github_desktop_exe,
)

# ── Windows Credential Manager (AdvAPI32) ─────────────────────────────────────
# GitHub Desktop stores its OAuth token in the Credential Manager under targets
# matching "GitHub - *" or "git:https://github.com*".  We snapshot those entries
# alongside the AppData backup so that a restored profile never gets a token
# mismatch ("Invalidated account token").
if sys.platform == "win32":
    _CRED_TYPE_GENERIC = 1
    _CRED_PERSIST_LOCAL_MACHINE = 2
    _GH_CRED_PREFIXES = ("GitHub - ", "git:https://github.com", "GitHub Desktop")

    class _FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class _CREDATTR(ctypes.Structure):
        _fields_ = [
            ("Keyword", ctypes.c_wchar_p),
            ("Flags", wintypes.DWORD),
            ("ValueSize", wintypes.DWORD),
            ("Value", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    class _CRED(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", ctypes.c_wchar_p),
            ("Comment", ctypes.c_wchar_p),
            ("LastWritten", _FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.POINTER(_CREDATTR)),
            ("TargetAlias", ctypes.c_wchar_p),
            ("UserName", ctypes.c_wchar_p),
        ]

    _PCRED = ctypes.POINTER(_CRED)
    _PPCRED = ctypes.POINTER(_PCRED)

    _adv = ctypes.windll.advapi32
    _adv.CredEnumerateW.argtypes = [
        ctypes.c_wchar_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(_PPCRED),
    ]
    _adv.CredEnumerateW.restype = wintypes.BOOL
    _adv.CredReadW.argtypes = [
        ctypes.c_wchar_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_PCRED),
    ]
    _adv.CredReadW.restype = wintypes.BOOL
    _adv.CredWriteW.argtypes = [ctypes.POINTER(_CRED), wintypes.DWORD]
    _adv.CredWriteW.restype = wintypes.BOOL
    _adv.CredFree.argtypes = [ctypes.c_void_p]
    _adv.CredFree.restype = None

    def _enum_github_targets():
        count, arr = wintypes.DWORD(0), _PPCRED()
        if not _adv.CredEnumerateW(None, 0, ctypes.byref(count), ctypes.byref(arr)):
            return []
        try:
            return [
                arr[i].contents.TargetName
                for i in range(count.value)
                if arr[i].contents.TargetName
                and any(arr[i].contents.TargetName.startswith(p) for p in _GH_CRED_PREFIXES)
            ]
        finally:
            _adv.CredFree(arr)

    def _cred_to_dict(target: str, ctype: int) -> Optional[dict]:
        ptr = _PCRED()
        if not _adv.CredReadW(target, ctype, 0, ctypes.byref(ptr)):
            return None
        try:
            c = ptr.contents
            size = c.CredentialBlobSize
            blob = bytes(bytearray(c.CredentialBlob[i] for i in range(size))) if size else b""
            return {
                "target": c.TargetName,
                "type": c.Type,
                "username": c.UserName or "",
                "comment": c.Comment or "",
                "persist": c.Persist,
                "blob": base64.b64encode(blob).decode(),
            }
        finally:
            _adv.CredFree(ptr)

    def _dict_to_cred(entry: dict) -> bool:
        blob = base64.b64decode(entry["blob"])
        c = _CRED()
        c.Flags = 0
        c.Type = entry["type"]
        c.TargetName = entry["target"]
        c.Comment = entry.get("comment") or None
        c.UserName = entry.get("username") or None
        c.Persist = entry.get("persist", _CRED_PERSIST_LOCAL_MACHINE)
        c.AttributeCount = 0
        c.Attributes = None
        c.TargetAlias = None
        if blob:
            blob_arr = (ctypes.c_ubyte * len(blob))(*blob)
            c.CredentialBlobSize = len(blob)
            c.CredentialBlob = blob_arr
        else:
            c.CredentialBlobSize = 0
            c.CredentialBlob = None
        return bool(_adv.CredWriteW(ctypes.byref(c), 0))


class GitHubDesktopManager:
    @staticmethod
    def kill() -> bool:
        """Gracefully close GitHub Desktop; force-kill only if it stays alive after 5 s.

        A force-kill while Chromium is mid-write can corrupt Local State, which
        causes GitHub Desktop to fail DPAPI decryption and invalidate the session.
        """
        try:
            # Signal all GitHubDesktop.exe processes to close normally
            subprocess.run(
                ["taskkill", "/IM", "GitHubDesktop.exe"],
                capture_output=True, timeout=10,
                creationflags=_NO_WINDOW,
            )
            # Poll up to 5 s for a clean exit so Chromium can flush its writes
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if not GitHubDesktopManager.is_running():
                    time.sleep(0.5)  # let file handles drain before we copy
                    return True
                time.sleep(0.3)
            # Still alive — force kill as last resort
            subprocess.run(
                ["taskkill", "/F", "/IM", "GitHubDesktop.exe"],
                capture_output=True, timeout=10,
                creationflags=_NO_WINDOW,
            )
            time.sleep(1)
            return True
        except Exception:
            return False

    @staticmethod
    def launch() -> bool:
        exe = get_github_desktop_exe()
        if not exe.exists():
            return False
        try:
            subprocess.Popen([str(exe)])
            return True
        except Exception:
            return False

    @staticmethod
    def backup_config(profile_name: str) -> Tuple[bool, str]:
        src = get_github_desktop_config_dir()
        dst = get_profile_backup_dir(profile_name)
        if not src.exists():
            return False, f"Config folder not found: {src}"
        try:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            return True, f"Backed up to {dst.name}"
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def restore_config(profile_name: str) -> Tuple[bool, str]:
        src = get_profile_backup_dir(profile_name)
        dst = get_github_desktop_config_dir()
        if not src.exists():
            return False, f"No backup found for '{profile_name}'"
        try:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            return True, f"Restored config for '{profile_name}'"
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def backup_credentials(profile_name: str) -> bool:
        """Snapshot Credential Manager entries for the current GitHub account."""
        if sys.platform != "win32":
            return True
        try:
            targets = _enum_github_targets()
            entries = []
            for target in targets:
                # Generic is the common type; fall back to domain-password (type 2)
                entry = _cred_to_dict(target, _CRED_TYPE_GENERIC) or _cred_to_dict(target, 2)
                if entry:
                    entries.append(entry)
            dest = get_profile_credentials_file(profile_name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(entries, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    @staticmethod
    def restore_credentials(profile_name: str) -> bool:
        """Write back the Credential Manager entries saved for this profile."""
        if sys.platform != "win32":
            return True
        src = get_profile_credentials_file(profile_name)
        if not src.exists():
            return True  # first-time profile — nothing to restore
        try:
            entries = json.loads(src.read_text(encoding="utf-8"))
            for entry in entries:
                _dict_to_cred(entry)
            return True
        except Exception:
            return False

    @staticmethod
    def has_backup(profile_name: str) -> bool:
        return get_profile_backup_dir(profile_name).exists()

    @staticmethod
    def is_running() -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq GitHubDesktop.exe"],
                capture_output=True, text=True, timeout=5,
                creationflags=_NO_WINDOW,
            )
            return "GitHubDesktop.exe" in result.stdout
        except Exception:
            return False

    @staticmethod
    def is_installed() -> bool:
        return get_github_desktop_exe().exists()
