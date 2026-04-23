import threading
from typing import Optional

import customtkinter as ctk
from PIL import Image

from core.config import ConfigManager
from core.git_manager import GitManager
from core.github_desktop import GitHubDesktopManager
from core.switcher import ProfileSwitcher, SwitchStep
from ui.about_dialog import AboutDialog
from ui.profile_card import ProfileCard
from ui.profile_dialog import ProfileDialog
from ui.settings_dialog import SettingsDialog
from ui.update_dialog import UpdateDialog
from utils.paths import get_asset
from version import __version__


class GitSwitcherApp(ctk.CTk):
    _WIDTH = 520
    _HEIGHT = 630

    def __init__(self):
        super().__init__()
        self._config = ConfigManager()
        self._git = GitManager()
        self._desktop = GitHubDesktopManager()
        self._switcher = ProfileSwitcher(self._config, self._git, self._desktop)
        self._current_profile: Optional[str] = None
        self._cards: dict[str, ProfileCard] = {}

        ctk.set_appearance_mode(self._config.settings.appearance_mode)
        self._setup_window()
        self._build_ui()
        self._refresh()
        self.after(2000, self._background_update_check)

    # ── Window setup ──────────────────────────────────────────────

    def _setup_window(self):
        self.title(f"Git Profile Switcher  v{__version__}")
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}")
        self.minsize(420, 500)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)   # row 3 = profile list

        ico = get_asset("icon.ico")
        if ico.exists():
            self.after(201, lambda: self.iconbitmap(str(ico)))

    # ── UI construction ───────────────────────────────────────────

    def _build_ui(self):
        self._build_header()         # row 0
        self._build_update_banner()  # row 1 — hidden until an update is found
        self._build_toolbar()        # row 2
        self._build_profile_list()   # row 3
        self._build_statusbar()      # row 4

    def _build_header(self):
        frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray17"))
        frame.grid(row=0, column=0, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        logo_path = get_asset("logo_96.png")
        if logo_path.exists():
            img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(56, 56),
            )
            ctk.CTkLabel(frame, image=img, text="").grid(
                row=0, column=0, rowspan=3, padx=(16, 10), pady=12, sticky="w"
            )
            text_col = 1
        else:
            text_col = 0

        ctk.CTkLabel(
            frame,
            text="Git Profile Switcher",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=text_col, padx=(0, 20), pady=(14, 2), sticky="w")

        self._user_label = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray65"),
            anchor="w",
        )
        self._user_label.grid(row=1, column=text_col, padx=(0, 20), pady=(0, 2), sticky="w")

        self._profile_label = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray55", "gray55"),
            anchor="w",
        )
        self._profile_label.grid(row=2, column=text_col, padx=(0, 20), pady=(0, 14), sticky="w")

    def _build_update_banner(self):
        self._banner = ctk.CTkFrame(
            self,
            height=38,
            corner_radius=0,
            fg_color=("#1a5fa8", "#1a4a8a"),
        )
        self._banner.grid(row=1, column=0, sticky="ew")
        self._banner.grid_propagate(False)
        self._banner.grid_columnconfigure(0, weight=1)
        self._banner.grid_remove()   # hidden until an update is detected

        self._banner_label = ctk.CTkLabel(
            self._banner,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="white",
            anchor="w",
        )
        self._banner_label.grid(row=0, column=0, padx=14, sticky="w")

        install_btn = ctk.CTkButton(
            self._banner,
            text="Install Now",
            width=90,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="white",
            text_color=("#1a5fa8", "#1a4a8a"),
            hover_color=("#e0ecff", "#c0d8ff"),
            command=self._on_updates,
        )
        install_btn.grid(row=0, column=1, padx=(0, 6))

        ctk.CTkButton(
            self._banner,
            text="✕",
            width=26,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color="white",
            hover_color=("#2272c3", "#2560a8"),
            command=self._dismiss_banner,
        ).grid(row=0, column=2, padx=(0, 8))

    def _build_toolbar(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(10, 4))
        frame.grid_columnconfigure(1, weight=1)

        self._add_btn = ctk.CTkButton(
            frame,
            text="+ Add Profile",
            width=130,
            height=32,
            command=self._on_add,
        )
        self._add_btn.grid(row=0, column=0, sticky="w")

        btn_right = ctk.CTkFrame(frame, fg_color="transparent")
        btn_right.grid(row=0, column=2, sticky="e")

        self._refresh_btn = ctk.CTkButton(
            btn_right,
            text="⟳ Refresh",
            width=90,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            command=self._refresh,
            font=ctk.CTkFont(size=12),
        )
        self._refresh_btn.pack(side="left", padx=(0, 6))

        self._settings_btn = ctk.CTkButton(
            btn_right,
            text="⚙ Settings",
            width=100,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            command=self._on_settings,
        )
        self._settings_btn.pack(side="left", padx=(0, 6))

        self._about_btn = ctk.CTkButton(
            btn_right,
            text="?",
            width=32,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_about,
        )
        self._about_btn.pack(side="left")

    def _build_profile_list(self):
        self._scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self._scroll.grid(row=3, column=0, sticky="nsew", padx=15, pady=6)
        self._scroll.grid_columnconfigure(0, weight=1)

    def _build_statusbar(self):
        frame = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=("gray88", "gray18"))
        frame.grid(row=4, column=0, sticky="ew")
        frame.grid_propagate(False)
        frame.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            frame,
            text="Ready",
            font=ctk.CTkFont(size=11),
            anchor="w",
            text_color=("gray40", "gray60"),
        )
        self._status_label.grid(row=0, column=0, padx=14, sticky="w")

    # ── Refresh ───────────────────────────────────────────────────

    def _refresh(self):
        git_name, git_email = self._git.get_current_user()
        self._current_profile = self._config.find_profile_by_git(git_name, git_email)

        if git_name or git_email:
            self._user_label.configure(text=f"{git_name}  •  {git_email}")
        else:
            self._user_label.configure(text="No git user configured")

        if self._current_profile:
            self._profile_label.configure(text=f"Active profile: {self._current_profile}")
        else:
            self._profile_label.configure(text="Active profile: (unknown)")

        for w in self._scroll.winfo_children():
            w.destroy()
        self._cards.clear()

        profiles = self._config.get_profiles()
        if not profiles:
            ctk.CTkLabel(
                self._scroll,
                text='No profiles yet.\nClick "+ Add Profile" to get started.',
                font=ctk.CTkFont(size=13),
                text_color=("gray55", "gray55"),
                justify="center",
            ).grid(row=0, column=0, pady=40)
            return

        for i, (name, profile) in enumerate(profiles.items()):
            card = ProfileCard(
                self._scroll,
                profile=profile,
                is_active=(name == self._current_profile),
                has_backup=self._desktop.has_backup(name),
                on_switch=lambda n=name: self._on_switch(n),
                on_edit=lambda n=name: self._on_edit(n),
                on_delete=lambda n=name: self._on_delete(n),
            )
            card.grid(row=i, column=0, sticky="ew", pady=(0, 8))
            self._cards[name] = card

    # ── Actions ───────────────────────────────────────────────────

    def _on_switch(self, profile_name: str):
        self._set_status(f"Switching to '{profile_name}'...", "gray")
        self._set_controls_enabled(False)

        def worker():
            def on_progress(step: SwitchStep, detail: str):
                msg = f"{step.value} {detail}".strip()
                self.after(0, lambda: self._set_status(msg, "gray"))

            result = self._switcher.switch(
                profile_name, self._current_profile, on_progress
            )

            def on_done():
                color = ("#2d7a4a", "#4caf7d") if result.success else ("#c0392b", "#e05555")
                self._set_status(result.message, color)
                self._set_controls_enabled(True)
                self._refresh()

            self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_add(self):
        dialog = ProfileDialog(self, title="Add Profile")
        self.wait_window(dialog)
        if dialog.result:
            if not self._config.add_profile(dialog.result):
                self._set_status(f"Profile '{dialog.result.name}' already exists", "orange")
            else:
                self._set_status(f"Profile '{dialog.result.name}' added", "gray")
            self._refresh()

    def _on_edit(self, profile_name: str):
        profile = self._config.get_profile(profile_name)
        if not profile:
            return
        dialog = ProfileDialog(self, title="Edit Profile", profile=profile)
        self.wait_window(dialog)
        if dialog.result:
            self._config.update_profile(profile_name, dialog.result)
            self._set_status(f"Profile '{dialog.result.name}' updated", "gray")
            self._refresh()

    def _on_delete(self, profile_name: str):
        dialog = ctk.CTkInputDialog(
            text=f"Type  '{profile_name}'  to confirm deletion:",
            title="Delete Profile",
        )
        value = dialog.get_input()
        if value and value.strip() == profile_name:
            self._config.delete_profile(profile_name)
            self._set_status(f"Deleted profile '{profile_name}'", ("gray40", "gray60"))
            self._refresh()

    def _on_settings(self):
        dialog = SettingsDialog(self, self._config)
        self.wait_window(dialog)
        self._refresh()

    def _on_about(self):
        dialog = AboutDialog(self)
        self.wait_window(dialog)

    def _on_updates(self):
        dialog = UpdateDialog(self)
        self.wait_window(dialog)

    # ── Update check ──────────────────────────────────────────────

    def _background_update_check(self):
        from core.updater import fetch_latest_release, is_newer

        def worker():
            release, error = fetch_latest_release()
            if release and is_newer(release) and not error:
                self.after(0, lambda: self._show_update_banner(release.tag))

        threading.Thread(target=worker, daemon=True).start()

    def _show_update_banner(self, tag: str):
        self._banner_label.configure(text=f"  Update {tag} is available")
        self._banner.grid()

    def _dismiss_banner(self):
        self._banner.grid_remove()

    # ── Helpers ───────────────────────────────────────────────────

    def _set_status(self, message: str, color="gray"):
        self._status_label.configure(text=message, text_color=color)

    def _set_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._add_btn.configure(state=state)
        self._refresh_btn.configure(state=state)
        self._settings_btn.configure(state=state)
        self._about_btn.configure(state=state)
        for card in self._cards.values():
            card.set_enabled(enabled)
