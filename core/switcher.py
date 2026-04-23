from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from core.config import ConfigManager
from core.git_manager import GitManager
from core.github_desktop import GitHubDesktopManager


class SwitchStep(Enum):
    KILLING_DESKTOP = "Closing GitHub Desktop..."
    BACKING_UP = "Backing up current profile..."
    UPDATING_GIT = "Updating git configuration..."
    RESTORING = "Restoring target profile..."
    LAUNCHING = "Launching GitHub Desktop..."
    COMPLETE = "Switch complete!"
    ERROR = "Error"


ProgressCallback = Callable[[SwitchStep, str], None]


@dataclass
class SwitchResult:
    success: bool
    message: str


class ProfileSwitcher:
    def __init__(
        self,
        config: ConfigManager,
        git: GitManager,
        desktop: GitHubDesktopManager,
    ):
        self.config = config
        self.git = git
        self.desktop = desktop

    def switch(
        self,
        target_name: str,
        current_name: Optional[str],
        on_progress: Optional[ProgressCallback] = None,
    ) -> SwitchResult:
        def notify(step: SwitchStep, detail: str = ""):
            if on_progress:
                on_progress(step, detail)

        target = self.config.get_profile(target_name)
        if not target:
            return SwitchResult(False, f"Profile '{target_name}' not found")

        settings = self.config.settings
        use_desktop = settings.use_github_desktop and GitHubDesktopManager.is_installed()

        if use_desktop:
            notify(SwitchStep.KILLING_DESKTOP)
            self.desktop.kill()

            if current_name:
                notify(SwitchStep.BACKING_UP, current_name)
                ok, msg = self.desktop.backup_config(current_name)
                if not ok:
                    return SwitchResult(False, f"Backup failed: {msg}")
                self.desktop.backup_credentials(current_name)

        notify(SwitchStep.UPDATING_GIT, f"{target.git_name} <{target.git_email}>")
        if not self.git.set_user(target.git_name, target.git_email):
            return SwitchResult(False, "Failed to update git global config")

        if use_desktop:
            if self.desktop.has_backup(target_name):
                notify(SwitchStep.RESTORING, target_name)
                ok, msg = self.desktop.restore_config(target_name)
                if not ok:
                    return SwitchResult(False, f"Restore failed: {msg}")
                self.desktop.restore_credentials(target_name)
            else:
                notify(SwitchStep.RESTORING, f"No backup for '{target_name}', skipping")

            if settings.launch_after_switch:
                notify(SwitchStep.LAUNCHING)
                self.desktop.launch()

        notify(SwitchStep.COMPLETE)
        return SwitchResult(True, f"Switched to '{target_name}'")
