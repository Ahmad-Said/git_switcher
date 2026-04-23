import customtkinter as ctk
from typing import Callable

from core.config import Profile


class ProfileCard(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        profile: Profile,
        is_active: bool,
        has_backup: bool,
        on_switch: Callable,
        on_edit: Callable,
        on_delete: Callable,
        **kwargs,
    ):
        border_color = "#1f6aa5" if is_active else ("gray70", "gray30")
        super().__init__(
            parent,
            border_color=border_color,
            border_width=2 if is_active else 1,
            corner_radius=8,
            **kwargs,
        )
        self._switch_btn: ctk.CTkButton | None = None
        self._edit_btn: ctk.CTkButton | None = None
        self._delete_btn: ctk.CTkButton | None = None

        self.grid_columnconfigure(0, weight=1)
        self._build(profile, is_active, has_backup, on_switch, on_edit, on_delete)

    def _build(
        self,
        profile: Profile,
        is_active: bool,
        has_backup: bool,
        on_switch: Callable,
        on_edit: Callable,
        on_delete: Callable,
    ):
        # ── Name row ──────────────────────────────────────────────
        name_row = ctk.CTkFrame(self, fg_color="transparent")
        name_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
        name_row.grid_columnconfigure(1, weight=1)

        indicator_color = "#1f6aa5" if is_active else ("gray60", "gray50")
        ctk.CTkLabel(
            name_row,
            text="●",
            text_color=indicator_color,
            font=ctk.CTkFont(size=10),
            width=16,
        ).grid(row=0, column=0, padx=(0, 6))

        ctk.CTkLabel(
            name_row,
            text=profile.name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        if is_active:
            ctk.CTkLabel(
                name_row,
                text="ACTIVE",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#1f6aa5",
            ).grid(row=0, column=2, padx=(0, 2))

        # ── Git identity ──────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=f"  {profile.git_name}",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color=("gray40", "gray70"),
        ).grid(row=1, column=0, sticky="ew", padx=14)

        ctk.CTkLabel(
            self,
            text=f"  {profile.git_email}",
            font=ctk.CTkFont(size=11),
            anchor="w",
            text_color=("gray50", "gray55"),
        ).grid(row=2, column=0, sticky="ew", padx=14)

        # ── GH Desktop backup indicator ───────────────────────────
        backup_text = "  ✓ GitHub Desktop backup exists" if has_backup else "  ○ No GitHub Desktop backup"
        backup_color = ("green", "#4caf7d") if has_backup else ("gray55", "gray50")
        ctk.CTkLabel(
            self,
            text=backup_text,
            font=ctk.CTkFont(size=11),
            anchor="w",
            text_color=backup_color,
        ).grid(row=3, column=0, sticky="ew", padx=14, pady=(3, 10))

        # ── Action buttons ────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))

        self._edit_btn = ctk.CTkButton(
            btn_row,
            text="Edit",
            width=72,
            height=28,
            fg_color="transparent",
            border_width=1,
            command=on_edit,
            font=ctk.CTkFont(size=11),
        )
        self._edit_btn.pack(side="left", padx=(0, 6))

        self._delete_btn = ctk.CTkButton(
            btn_row,
            text="Delete",
            width=72,
            height=28,
            fg_color="transparent",
            border_width=1,
            text_color=("#c0392b", "#e05555"),
            border_color=("#c0392b", "#e05555"),
            hover_color=("#fce4e4", "#4a1a1a"),
            command=on_delete,
            font=ctk.CTkFont(size=11),
        )
        self._delete_btn.pack(side="left")

        if not is_active:
            self._switch_btn = ctk.CTkButton(
                btn_row,
                text="Switch  →",
                width=100,
                height=28,
                command=on_switch,
                font=ctk.CTkFont(size=11),
            )
            self._switch_btn.pack(side="right")

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        if self._switch_btn:
            self._switch_btn.configure(state=state)
        if self._edit_btn:
            self._edit_btn.configure(state=state)
        if self._delete_btn:
            self._delete_btn.configure(state=state)
