import subprocess
from typing import Tuple


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
            )
            subprocess.run(
                ["git", "config", "--global", "user.email", email],
                check=True, capture_output=True,
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
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
