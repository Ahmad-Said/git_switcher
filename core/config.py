import json
from dataclasses import dataclass, asdict, field
from typing import Optional

from utils.paths import get_app_config_dir, get_app_config_file


@dataclass
class Profile:
    name: str
    git_name: str
    git_email: str


@dataclass
class AppSettings:
    use_github_desktop: bool = True
    launch_after_switch: bool = True
    appearance_mode: str = "System"


class ConfigManager:
    def __init__(self):
        self._config_file = get_app_config_file()
        self._profiles: dict[str, Profile] = {}
        self._settings = AppSettings()
        self._load()

    def _load(self):
        if not self._config_file.exists():
            return
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, pd in data.get("profiles", {}).items():
                self._profiles[name] = Profile(**pd)
            if "settings" in data:
                self._settings = AppSettings(**data["settings"])
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    def _save(self):
        get_app_config_dir().mkdir(parents=True, exist_ok=True)
        data = {
            "profiles": {n: asdict(p) for n, p in self._profiles.items()},
            "settings": asdict(self._settings),
        }
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_profiles(self) -> dict[str, Profile]:
        return dict(self._profiles)

    def get_profile(self, name: str) -> Optional[Profile]:
        return self._profiles.get(name)

    def add_profile(self, profile: Profile) -> bool:
        if profile.name in self._profiles:
            return False
        self._profiles[profile.name] = profile
        self._save()
        return True

    def update_profile(self, old_name: str, profile: Profile) -> bool:
        if old_name not in self._profiles:
            return False
        if old_name != profile.name:
            del self._profiles[old_name]
        self._profiles[profile.name] = profile
        self._save()
        return True

    def delete_profile(self, name: str) -> bool:
        if name not in self._profiles:
            return False
        del self._profiles[name]
        self._save()
        return True

    def find_profile_by_git(self, git_name: str, git_email: str) -> Optional[str]:
        for name, p in self._profiles.items():
            if p.git_name == git_name and p.git_email == git_email:
                return name
        return None

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update_settings(self, settings: AppSettings):
        self._settings = settings
        self._save()
