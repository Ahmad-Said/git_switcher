import customtkinter as ctk
from typing import Optional

from core.config import Profile


class ProfileDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, profile: Optional[Profile] = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x310")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.result: Optional[Profile] = None
        self._original_name = profile.name if profile else None

        self._build(profile)
        self.after(150, self._name_entry.focus)
        self.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _build(self, profile: Optional[Profile]):
        self.grid_columnconfigure(0, weight=1)

        def field(row: int, label: str, placeholder: str) -> ctk.CTkEntry:
            ctk.CTkLabel(
                self, text=label, font=ctk.CTkFont(size=12), anchor="w"
            ).grid(row=row, column=0, sticky="w", padx=24, pady=(14, 2))
            entry = ctk.CTkEntry(self, placeholder_text=placeholder, height=34)
            entry.grid(row=row + 1, column=0, sticky="ew", padx=24)
            return entry

        self._name_entry = field(0, "Profile Name", "e.g. Work, Personal, GitHub")
        self._git_name_entry = field(2, "Git User Name", "e.g. John Doe")
        self._git_email_entry = field(4, "Git Email", "e.g. user@example.com")

        self._error_label = ctk.CTkLabel(
            self, text="", text_color=("#c0392b", "#e05555"), font=ctk.CTkFont(size=11)
        )
        self._error_label.grid(row=6, column=0, padx=24, pady=(8, 0))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, pady=(6, 18))

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

        if profile:
            self._name_entry.insert(0, profile.name)
            self._git_name_entry.insert(0, profile.git_name)
            self._git_email_entry.insert(0, profile.git_email)

    def _on_save(self):
        name = self._name_entry.get().strip()
        git_name = self._git_name_entry.get().strip()
        git_email = self._git_email_entry.get().strip()

        if not name:
            self._error_label.configure(text="Profile name is required")
            return
        if not git_name:
            self._error_label.configure(text="Git user name is required")
            return
        if not git_email or "@" not in git_email:
            self._error_label.configure(text="A valid git email is required")
            return

        self.result = Profile(name=name, git_name=git_name, git_email=git_email)
        self.destroy()
