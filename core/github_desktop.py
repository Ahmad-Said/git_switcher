import shutil
import subprocess
import sys
import time
from typing import Tuple

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

from utils.paths import (
    get_github_desktop_config_dir,
    get_profile_backup_dir,
    get_github_desktop_exe,
)


class GitHubDesktopManager:
    @staticmethod
    def kill() -> bool:
        try:
            subprocess.run(
                ["taskkill", "/F", "/FI", "IMAGENAME eq GitHubDesktop.exe"],
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
