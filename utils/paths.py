import os
from pathlib import Path


def get_appdata_roaming() -> Path:
    return Path(os.environ.get("APPDATA", Path.home()))


def get_appdata_local() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))


def get_github_desktop_config_dir() -> Path:
    return get_appdata_roaming() / "GitHub Desktop"


def get_profile_backup_dir(profile_name: str) -> Path:
    return get_appdata_roaming() / f"GitHub Desktop-{profile_name}"


def get_app_config_dir() -> Path:
    return get_appdata_roaming() / "GitSwitcher"


def get_app_config_file() -> Path:
    return get_app_config_dir() / "profiles.json"


def get_github_desktop_exe() -> Path:
    return get_appdata_local() / "GitHubDesktop" / "GitHubDesktop.exe"


def is_github_desktop_installed() -> bool:
    return get_github_desktop_exe().exists()
