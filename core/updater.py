"""
Self-update logic against GitHub Releases.
All functions are pure / non-UI so they can run in background threads.
"""
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from version import __version__

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
            fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="GitSwitcher_update_")
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


def apply_update(new_exe: Path) -> None:
    """
    Spawn a detached batch script that:
      1. Waits for this process (by PID) to exit
      2. Moves the downloaded exe over the current exe
      3. Relaunches the updated exe
      4. Self-deletes the script

    Raises RuntimeError when not running as a frozen .exe.
    """
    if not is_frozen():
        raise RuntimeError("Self-update is only available in the packaged .exe build.")

    current_exe = Path(sys.executable)
    pid = os.getpid()

    fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="gitswitcher_upd_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"""@echo off
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto wait
)
move /Y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
