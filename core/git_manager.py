import subprocess
import sys
from typing import Tuple

# Prevent console windows from flashing when spawning subprocesses in a
# frozen/built application on Windows.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class GitManager:
    @staticmethod
    def get_current_user() -> Tuple[str, str]:
        name = GitManager._get("user.name")
        email = GitManager._get("user.email")
        return name, email

    @staticmethod
    def set_user(name: str, email: str) -> bool:
        try:
            subprocess.run(
                ["git", "config", "--global", "user.name", name],
                check=True, capture_output=True,
                creationflags=_NO_WINDOW,
            )
            subprocess.run(
                ["git", "config", "--global", "user.email", email],
                check=True, capture_output=True,
                creationflags=_NO_WINDOW,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def _get(key: str) -> str:
        try:
            result = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True, text=True, check=True,
                creationflags=_NO_WINDOW,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
