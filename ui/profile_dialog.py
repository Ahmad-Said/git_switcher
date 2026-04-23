import customtkinter as ctk
from typing import Optional

from core.config import Profile
from core.git_manager import GitManager


class ProfileDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, profile: Optional[Profile] = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x360")
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

        # Row 0-1: profile name
        self._name_entry = field(0, "Profile Name", "e.g. Work, Personal, GitHub")

        # Row 2: autofill hint row
        hint_row = ctk.CTkFrame(self, fg_color="transparent")
        hint_row.grid(row=2, column=0, sticky="ew", padx=24, pady=(10, 0))
        hint_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hint_row,
            text="Git Identity",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self._autofill_btn = ctk.CTkButton(
            hint_row,
            text="Fill from current git config",
            width=190,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            command=self._autofill,
        )
        self._autofill_btn.grid(row=0, column=1, sticky="e")

        # Row 3: thin separator
        ctk.CTkFrame(
            self, height=1, fg_color=("gray80", "gray30")
        ).grid(row=3, column=0, sticky="ew", padx=24, pady=(4, 0))

        # Row 4-5: git name, Row 6-7: git email
        self._git_name_entry = field(4, "Git User Name", "e.g. John Doe")
        self._git_email_entry = field(6, "Git Email", "e.g. user@example.com")

        # Row 8: error
        self._error_label = ctk.CTkLabel(
            self, text="", text_color=("#c0392b", "#e05555"), font=ctk.CTkFont(size=11)
        )
        self._error_label.grid(row=8, column=0, padx=24, pady=(8, 0))

        # Row 9: action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=9, column=0, pady=(6, 18))

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

    def _autofill(self):
        git_name, git_email = GitManager.get_current_user()
        if not git_name and not git_email:
            self._error_label.configure(text="No git config found — run: git config --global user.name / user.email")
            return

        self._error_label.configure(text="")
        self._git_name_entry.delete(0, "end")
        self._git_email_entry.delete(0, "end")
        if git_name:
            self._git_name_entry.insert(0, git_name)
        if git_email:
            self._git_email_entry.insert(0, git_email)

        # Brief visual confirmation on the button
        self._autofill_btn.configure(text="Filled!")
        self.after(1500, lambda: self._autofill_btn.configure(text="Fill from current git config"))

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
