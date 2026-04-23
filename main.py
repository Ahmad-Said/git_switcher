import sys
from pathlib import Path

# Make sure the project root is on sys.path when running as a PyInstaller bundle
if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from ui.app import GitSwitcherApp


def main():
    app = GitSwitcherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
