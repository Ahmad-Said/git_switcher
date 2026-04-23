import customtkinter as ctk

from core.config import AppSettings, ConfigManager
from utils.paths import is_github_desktop_installed
from version import __version__


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: ConfigManager):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x420")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._config = config
        self._build(config.settings)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _build(self, s: AppSettings):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Settings", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 14))

        # ── Appearance ────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Appearance Mode", font=ctk.CTkFont(size=12), anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 4))

        self._appearance_var = ctk.StringVar(value=s.appearance_mode)
        ctk.CTkOptionMenu(
            self,
            values=["System", "Light", "Dark"],
            variable=self._appearance_var,
            command=self._on_appearance_change,
            width=200,
        ).grid(row=2, column=0, sticky="w", padx=24)

        # ── GitHub Desktop ────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).grid(
            row=3, column=0, sticky="ew", padx=24, pady=(18, 14)
        )

        ghd_label = "GitHub Desktop Integration"
        if not is_github_desktop_installed():
            ghd_label += "  (not detected)"

        self._use_ghd_var = ctk.BooleanVar(value=s.use_github_desktop)
        ctk.CTkCheckBox(
            self,
            text=ghd_label,
            variable=self._use_ghd_var,
            font=ctk.CTkFont(size=12),
            command=self._on_toggle_ghd,
        ).grid(row=4, column=0, sticky="w", padx=24, pady=(0, 10))

        self._launch_var = ctk.BooleanVar(value=s.launch_after_switch)
        self._launch_cb = ctk.CTkCheckBox(
            self,
            text="Launch GitHub Desktop after switching",
            variable=self._launch_var,
            font=ctk.CTkFont(size=12),
        )
        self._launch_cb.grid(row=5, column=0, sticky="w", padx=40, pady=(0, 10))
        if not s.use_github_desktop:
            self._launch_cb.configure(state="disabled")

        # ── Updates ───────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).grid(
            row=6, column=0, sticky="ew", padx=24, pady=(8, 14)
        )

        update_row = ctk.CTkFrame(self, fg_color="transparent")
        update_row.grid(row=7, column=0, sticky="ew", padx=24, pady=(0, 4))
        update_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            update_row,
            text=f"Version  v{__version__}",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            update_row,
            text="Check for Updates",
            width=150,
            height=30,
            font=ctk.CTkFont(size=11),
            command=self._on_check_updates,
        ).grid(row=0, column=1, sticky="e")

        # ── Save / Cancel ─────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=8, column=0, pady=(14, 18))

        ctk.CTkButton(
            btn_frame, text="Cancel", width=110, height=34,
            fg_color="transparent", border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            command=self.destroy,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame, text="Save", width=110, height=34, command=self._on_save,
        ).pack(side="left", padx=6)

    def _on_appearance_change(self, value: str):
        ctk.set_appearance_mode(value)

    def _on_toggle_ghd(self):
        state = "normal" if self._use_ghd_var.get() else "disabled"
        self._launch_cb.configure(state=state)

    def _on_check_updates(self):
        # Import here to avoid circular imports at module load time
        from ui.update_dialog import UpdateDialog
        # Release grab so the update dialog can take focus properly
        self.grab_release()
        self.destroy()
        UpdateDialog(self.master)

    def _on_save(self):
        new_settings = AppSettings(
            use_github_desktop=self._use_ghd_var.get(),
            launch_after_switch=self._launch_var.get(),
            appearance_mode=self._appearance_var.get(),
        )
        self._config.update_settings(new_settings)
        self.destroy()
