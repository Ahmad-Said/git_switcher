"""
Self-update logic against GitHub Releases.
All functions are pure / non-UI so they can run in background threads.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from version import __version__

# CLI flag used to put a freshly-downloaded exe into "updater" mode.
# Usage (hidden from users):
#   <new_exe> --apply-update <target_exe> <old_pid>
APPLY_UPDATE_FLAG = "--apply-update"
_UPDATE_TMP_PREFIX = "GitSwitcher_update_"
_UPDATE_LOG_NAME = "GitSwitcher_update.log"

RELEASES_API = "https://api.github.com/repos/Ahmad-Said/git_switcher/releases/latest"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "GitSwitcher-App",
}


# ── Data ──────────────────────────────────────────────────────────────────────

@dataclass
class ReleaseInfo:
    tag: str            # e.g. "v1.2.0"
    version_str: str    # e.g. "1.2.0"
    name: str           # human release title
    download_url: str   # direct URL to the .exe asset
    release_notes: str


# ── Version comparison ────────────────────────────────────────────────────────

def _semver(v: str) -> tuple:
    """'v1.2.3-beta' → (1, 2, 3). 'dev' → (0, 0, 0)."""
    base = v.lstrip("v").split("-")[0]
    try:
        return tuple(int(x) for x in base.split("."))
    except ValueError:
        return (0, 0, 0)


def is_newer(release: ReleaseInfo) -> bool:
    return _semver(release.tag) > _semver(__version__)


# ── Network ───────────────────────────────────────────────────────────────────

def fetch_latest_release() -> Tuple[Optional[ReleaseInfo], Optional[str]]:
    """Returns (ReleaseInfo, None) on success or (None, error_message) on failure."""
    try:
        with urlopen(Request(RELEASES_API, headers=_HEADERS), timeout=10) as resp:
            data = json.loads(resp.read().decode())

        asset = next(
            (a for a in data.get("assets", []) if a["name"].lower().endswith(".exe")),
            None,
        )
        if not asset:
            return None, "No .exe asset found in the latest release."

        return ReleaseInfo(
            tag=data["tag_name"],
            version_str=data["tag_name"].lstrip("v"),
            name=data.get("name", data["tag_name"]),
            download_url=asset["browser_download_url"],
            release_notes=(data.get("body") or "").strip(),
        ), None

    except URLError as exc:
        return None, f"Network error: {exc.reason}"
    except Exception as exc:
        return None, str(exc)


ProgressCallback = Callable[[int, int], None]   # (bytes_downloaded, total_bytes)


def download_release(
    release: ReleaseInfo,
    on_progress: Optional[ProgressCallback] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    """Download the .exe to a temp file. Returns (path, None) or (None, error)."""
    try:
        req = Request(release.download_url, headers=_HEADERS)
        with urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix=_UPDATE_TMP_PREFIX)
            downloaded = 0
            with os.fdopen(fd, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(downloaded, total)
        return Path(tmp_path), None
    except Exception as exc:
        return None, str(exc)


# ── Self-replace ──────────────────────────────────────────────────────────────

def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _update_log_path() -> Path:
    return Path(tempfile.gettempdir()) / _UPDATE_LOG_NAME


def _log(msg: str) -> None:
    try:
        with open(_update_log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def cleanup_stale_update_files() -> None:
    """
    Called at app startup. Removes leftover GitSwitcher_update_*.exe files
    from the temp directory (previous update's downloaded installer).
    Silent on failure — a locked file just stays for the next run.
    """
    tmp = Path(tempfile.gettempdir())
    try:
        candidates = list(tmp.glob(f"{_UPDATE_TMP_PREFIX}*.exe"))
    except Exception:
        return
    # Don't delete ourselves if we're currently running from temp.
    try:
        self_path = Path(sys.executable).resolve()
    except Exception:
        self_path = None
    for p in candidates:
        try:
            if self_path is not None and p.resolve() == self_path:
                continue
            p.unlink()
        except Exception:
            pass
    # Also trim the update log if it got large.
    log = _update_log_path()
    try:
        if log.exists() and log.stat().st_size > 256 * 1024:
            log.unlink()
    except Exception:
        pass


def _wait_for_pid_exit(pid: int, timeout: float = 30.0) -> bool:
    """Poll until the given PID is gone. Returns True if it exited within timeout."""
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259

    kernel32 = ctypes.windll.kernel32
    OpenProcess = kernel32.OpenProcess
    OpenProcess.restype = wintypes.HANDLE
    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    GetExitCodeProcess = kernel32.GetExitCodeProcess
    GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    CloseHandle = kernel32.CloseHandle

    deadline = time.time() + timeout
    while time.time() < deadline:
        h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            # Process doesn't exist (or access denied — treat as gone).
            return True
        try:
            code = wintypes.DWORD()
            if GetExitCodeProcess(h, ctypes.byref(code)) and code.value != STILL_ACTIVE:
                return True
        finally:
            CloseHandle(h)
        time.sleep(0.25)
    return False


def _replace_file_with_retry(
    src: Path, dst: Path, attempts: int = 40, delay: float = 0.5
) -> None:
    """
    Copy src → dst, retrying while dst is locked (e.g. AV scan / slow exit).
    Uses copy2 + os.replace so we never end up with a half-written file.
    """
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        try:
            # Stage alongside the target so os.replace is atomic on the same volume.
            staged = dst.with_name(dst.name + ".new")
            shutil.copy2(src, staged)
            os.replace(staged, dst)
            return
        except PermissionError as exc:
            last_exc = exc
            time.sleep(delay)
        except OSError as exc:
            last_exc = exc
            time.sleep(delay)
    raise RuntimeError(
        f"Could not replace {dst} after {attempts} attempts: {last_exc}"
    )


def apply_update(new_exe: Path) -> None:
    """
    Launch the freshly-downloaded exe in "updater" mode. It will:
      1. Wait for this process (by PID) to exit.
      2. Copy itself over the currently-installed exe (with retries).
      3. Relaunch the installed exe.
      4. Exit. Its own temp file is cleaned up by the new process at next start.

    Raises RuntimeError when not running as a frozen .exe.
    """
    if not is_frozen():
        raise RuntimeError("Self-update is only available in the packaged .exe build.")

    current_exe = Path(sys.executable).resolve()
    pid = os.getpid()

    # DETACHED_PROCESS + no-window so the helper survives us and stays invisible.
    creationflags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW

    subprocess.Popen(
        [str(new_exe), APPLY_UPDATE_FLAG, str(current_exe), str(pid)],
        creationflags=creationflags,
        close_fds=True,
        cwd=str(Path(tempfile.gettempdir())),
    )


def run_updater_mode(target_exe: str, old_pid_str: str) -> int:
    """
    Entry point when this exe was started with --apply-update.
    Returns an exit code.
    """
    _log(f"updater start: target={target_exe} old_pid={old_pid_str} self={sys.executable}")
    try:
        old_pid = int(old_pid_str)
    except ValueError:
        _log("bad pid argument")
        return 2

    target = Path(target_exe)

    if not _wait_for_pid_exit(old_pid, timeout=30.0):
        _log(f"old process {old_pid} did not exit within timeout; continuing anyway")

    # Extra grace period — Windows often holds the file briefly after exit.
    time.sleep(0.4)

    try:
        _replace_file_with_retry(Path(sys.executable), target)
        _log(f"replaced {target} successfully")
    except Exception as exc:
        _log(f"replace failed: {exc}\n{traceback.format_exc()}")
        return 3

    try:
        creationflags = 0
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creationflags |= subprocess.DETACHED_PROCESS
        subprocess.Popen(
            [str(target)],
            creationflags=creationflags,
            close_fds=True,
            cwd=str(target.parent),
        )
        _log("relaunched target")
    except Exception as exc:
        _log(f"relaunch failed: {exc}")
        return 4

    return 0



