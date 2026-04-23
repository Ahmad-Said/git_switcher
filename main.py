import sys
from pathlib import Path

# Make sure the project root is on sys.path when running as a PyInstaller bundle
if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, str(Path(__file__).parent))

from core.updater import APPLY_UPDATE_FLAG, cleanup_stale_update_files, run_updater_mode


def main():
    # Hidden updater-mode entry point. When an update has been downloaded,
    # the NEW exe is started with: --apply-update <target_exe> <old_pid>
    # It waits for the old process to exit, replaces the target exe with
    # itself, relaunches the target, and exits. No GUI is created.
    if APPLY_UPDATE_FLAG in sys.argv:
        try:
            idx = sys.argv.index(APPLY_UPDATE_FLAG)
            target_exe = sys.argv[idx + 1]
            old_pid = sys.argv[idx + 2]
        except (IndexError, ValueError):
            sys.exit(2)
        sys.exit(run_updater_mode(target_exe, old_pid))

    # Normal startup — opportunistically wipe any leftover update installers.
    cleanup_stale_update_files()

    import customtkinter as ctk  # noqa: F401  (kept for side-effect parity)
    from ui.app import GitSwitcherApp

    app = GitSwitcherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
