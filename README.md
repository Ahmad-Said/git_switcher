# Git Profile Switcher

A Windows desktop application for switching between multiple git identities and GitHub Desktop workspaces with a single
click.

Inspired by a bash script that required Git Bash — this app replaces it with a native GUI that any user can run.

---

## Install (one command, no admin required)

Open **PowerShell** (Win + R → `powershell`) and run:

```powershell
irm https://raw.githubusercontent.com/Ahmad-Said/git_switcher/main/install.ps1 | iex
```

The script will:

1. Fetch the latest release from GitHub
2. Download the `.exe` to a temp file
3. Install it to `%LOCALAPPDATA%\GitSwitcher\GitSwitcher.exe`
4. Register it in the user App Paths registry key (no admin needed)
5. Create a **Start Menu** shortcut
6. Optionally create a **Desktop** shortcut (asked interactively)

Run the same command at any time to update to the latest version.

> **Tip:** If you see a script-execution error, run this first once:
> ```powershell
> Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## What it does

Each **profile** pairs a git identity (`user.name` + `user.email`) with a GitHub Desktop configuration folder. Switching
profiles:

1. Kills the running GitHub Desktop process
2. Backs up the current `%APPDATA%\GitHub Desktop` folder under the current profile's name
3. Updates `git config --global user.name` and `user.email`
4. Restores the target profile's previously backed-up folder
5. Relaunches GitHub Desktop

GitHub Desktop integration is optional — profiles without a backup still switch the git identity only.

---

## Screenshots

| Profile list                                                   | Add profile                     | Settings                            |
|----------------------------------------------------------------|---------------------------------|-------------------------------------|
| *(active profile highlighted in blue, backup status per card)* | *(name · git name · git email)* | *(appearance · GH Desktop toggles)* |

---

## Requirements

- Windows 10 / 11
- Python 3.10+ (only needed to run from source or build)
- GitHub Desktop installed at the default location (optional)

---

## Running from source

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
python main.py
```

---

## Building a standalone executable

```bash
pip install pyinstaller
```
pyinstaller build.spec

The output is a single file at `dist\GitSwitcher.exe` — no Python installation required on the target machine.

> **Tip:** Add an icon by placing `assets\icon.ico` in the project root and updating the `icon=` line in `build.spec`.

---

## First-time setup

### Option A — import your existing bash profiles

For each profile defined in the old bash script, add it via **+ Add Profile** and fill in the same name/email values.

Then create the GitHub Desktop backups by switching *to* each profile once while GitHub Desktop is closed. The app will
copy the current `GitHub Desktop` folder as the backup for that profile on first switch-away.

### Option B — fresh setup for a new profile

1. Open GitHub Desktop and sign in with the account for that profile.
2. Add the profile in the app (matching the git name and email for that account).
3. Close GitHub Desktop.
4. Switch to any other profile — the app will back up the current folder before switching.

---

## Project structure

```
git_switcher/
├── main.py                   # Entry point (also updater-mode dispatcher)
├── install.ps1               # One-command user installer (hosted on GitHub)
├── requirements.txt
├── build.spec                # PyInstaller spec (one-file, no console)
│
├── core/
│   ├── config.py             # Profile & AppSettings dataclasses, JSON persistence
│   ├── git_manager.py        # Read / write git global config
│   ├── github_desktop.py     # Kill, backup, restore, launch GitHub Desktop
│   ├── switcher.py           # Switch orchestration with progress callbacks
│   └── updater.py            # Self-update logic (download, apply, cleanup)
│
├── ui/
│   ├── app.py                # Main window (customtkinter)
│   ├── profile_card.py       # Per-profile card widget
│   ├── profile_dialog.py     # Add / edit profile dialog
│   ├── settings_dialog.py    # Appearance & integration settings
│   └── update_dialog.py      # Check-for-updates dialog
│
└── utils/
    └── paths.py              # Windows path resolution (%APPDATA%, %LOCALAPPDATA%)
```

---

## Self-update

The app checks for updates from **Help → Check for Updates**.  
When a new version is available it downloads the new `.exe` and applies it without needing a separate installer:

1. The new exe is launched in the background with a hidden `--apply-update` flag.
2. It waits (via Win32 `OpenProcess`) for the running app to exit.
3. It atomically replaces the installed exe (with retries for AV/file-lock tolerance).
4. It relaunches the freshly-installed exe.

A diagnostic log is written to `%TEMP%\GitSwitcher_update.log` if anything goes wrong.

---

## Configuration file

Profiles and settings are stored at:

```
%APPDATA%\GitSwitcher\profiles.json
```

GitHub Desktop backups are stored alongside the live folder:

```
%APPDATA%\GitHub Desktop          ← active config
%APPDATA%\GitHub Desktop-Work     ← backup for "Work" profile
%APPDATA%\GitHub Desktop-Personal ← backup for "Personal" profile
```

---

## Dependencies

| Package                                                         | Version  | Purpose                         |
|-----------------------------------------------------------------|----------|---------------------------------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | ≥ 5.2.0  | Modern Tk UI widgets            |
| [Pillow](https://python-pillow.org)                             | ≥ 10.0.0 | Image support for customtkinter |
| [pyinstaller](https://pyinstaller.org)                          | ≥ 6.0.0  | Build standalone `.exe`         |
