import customtkinter as ctk
from PIL import Image

from utils.paths import get_asset, get_app_config_file, get_appdata_roaming


# ── Reusable section primitives ───────────────────────────────────────────────

def _section_header(parent, text: str, row: int):
    """Bold section title with a coloured accent bar underneath."""
    ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=("#1a5fa8", "#4a9eff"),
        anchor="w",
    ).grid(row=row, column=0, sticky="ew", padx=20, pady=(20, 2))

    ctk.CTkFrame(
        parent, height=2, fg_color=("#1a5fa8", "#4a9eff"), corner_radius=1
    ).grid(row=row + 1, column=0, sticky="ew", padx=20, pady=(0, 10))


def _paragraph(parent, text: str, row: int):
    ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=12),
        anchor="w",
        justify="left",
        wraplength=460,
    ).grid(row=row, column=0, sticky="w", padx=20, pady=(0, 6))


def _step(parent, number: int, title: str, body: str, row: int):
    """Numbered step: circle badge + title + body text."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 10))
    frame.grid_columnconfigure(1, weight=1)

    # Number badge
    badge = ctk.CTkFrame(
        frame,
        width=28, height=28,
        corner_radius=14,
        fg_color=("#1a5fa8", "#4a9eff"),
    )
    badge.grid(row=0, column=0, rowspan=2, padx=(0, 12), pady=2, sticky="n")
    badge.grid_propagate(False)
    ctk.CTkLabel(
        badge,
        text=str(number),
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color="white",
    ).place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        frame,
        text=title,
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
    ).grid(row=0, column=1, sticky="w")

    ctk.CTkLabel(
        frame,
        text=body,
        font=ctk.CTkFont(size=11),
        text_color=("gray40", "gray65"),
        anchor="w",
        justify="left",
        wraplength=410,
    ).grid(row=1, column=1, sticky="w")


def _flow_step(parent, label: str, detail: str, row: int, last: bool = False):
    """Arrow-flow step for the 'what happens during a switch' list."""
    frame = ctk.CTkFrame(parent, fg_color=("gray93", "gray20"), corner_radius=6)
    frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 2))
    frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        frame,
        text=label,
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
        width=28,
        text_color=("#1a5fa8", "#4a9eff"),
    ).grid(row=0, column=0, padx=(12, 6), pady=8, sticky="w")

    ctk.CTkLabel(
        frame,
        text=detail,
        font=ctk.CTkFont(size=12),
        anchor="w",
        justify="left",
        wraplength=380,
    ).grid(row=0, column=1, padx=(0, 12), pady=8, sticky="w")

    if not last:
        ctk.CTkLabel(
            parent,
            text="  |",
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray45"),
        ).grid(row=row + 1, column=0, sticky="w", padx=32, pady=0)


def _tip(parent, text: str, row: int):
    frame = ctk.CTkFrame(
        parent, fg_color=("#e8f4fd", "#1a2d40"), corner_radius=6
    )
    frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 6))
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        frame,
        text=text,
        font=ctk.CTkFont(size=11),
        text_color=("#1a5fa8", "#7ab8f5"),
        anchor="w",
        justify="left",
        wraplength=440,
    ).grid(row=0, column=0, padx=12, pady=8, sticky="w")


def _mono(parent, text: str, row: int):
    """Monospaced path/command label."""
    frame = ctk.CTkFrame(
        parent, fg_color=("gray88", "gray22"), corner_radius=4
    )
    frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 6))
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        frame,
        text=text,
        font=ctk.CTkFont(size=11, family="Consolas"),
        text_color=("gray20", "gray80"),
        anchor="w",
        justify="left",
        wraplength=440,
    ).grid(row=0, column=0, padx=10, pady=6, sticky="w")


def _copyable_mono(parent, text: str, row: int):
    """Monospaced path label with a Copy button that writes to the clipboard."""
    frame = ctk.CTkFrame(
        parent, fg_color=("gray88", "gray22"), corner_radius=4
    )
    frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 6))
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        frame,
        text=text,
        font=ctk.CTkFont(size=11, family="Consolas"),
        text_color=("gray20", "gray80"),
        anchor="w",
        justify="left",
        wraplength=360,
    ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

    copy_btn = ctk.CTkButton(
        frame,
        text="Copy",
        width=58,
        height=26,
        font=ctk.CTkFont(size=11),
        fg_color="transparent",
        border_width=1,
        border_color=("gray55", "gray45"),
        text_color=("gray15", "gray85"),
        hover_color=("gray82", "gray28"),
    )
    copy_btn.configure(command=lambda: _do_copy(parent, text, copy_btn))
    copy_btn.grid(row=0, column=1, padx=(4, 8), pady=8, sticky="e")


def _do_copy(widget, text: str, btn: ctk.CTkButton):
    widget.clipboard_clear()
    widget.clipboard_append(text)
    btn.configure(text="Copied!")
    widget.after(1500, lambda: btn.configure(text="Copy"))


# ── Main dialog ───────────────────────────────────────────────────────────────

class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About / Getting Started")
        self.geometry("520x640")
        self.minsize(480, 500)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()
        self._build_footer()
        self.bind("<Escape>", lambda _e: self.destroy())

    # ── Header (logo + app name) ──────────────────────────────────

    def _build_header(self):
        frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray17"))
        frame.grid(row=0, column=0, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        logo_path = get_asset("logo_96.png")
        if logo_path.exists():
            img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(52, 52),
            )
            ctk.CTkLabel(frame, image=img, text="").grid(
                row=0, column=0, rowspan=2, padx=(18, 12), pady=14, sticky="w"
            )

        ctk.CTkLabel(
            frame,
            text="Git Profile Switcher",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", padx=(0, 20), pady=(14, 1))

        ctk.CTkLabel(
            frame,
            text="Getting Started Guide",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray60"),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", padx=(0, 20), pady=(0, 14))

    # ── Scrollable content ────────────────────────────────────────

    def _build_content(self):
        scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        r = 0  # running row counter inside the scroll frame

        # ── What is this app? ─────────────────────────────────────
        _section_header(scroll, "What is Git Profile Switcher?", r); r += 2
        _paragraph(scroll,
            "Git Profile Switcher lets you maintain multiple git identities on "
            "one machine and swap between them instantly. Each Profile stores a "
            "git user name and email. When you switch, the app updates your "
            "global git config so that every repository on your machine uses "
            "the new identity — no more manually running git config commands.",
            r); r += 1
        _paragraph(scroll,
            "If you also use GitHub Desktop, the app can back up and restore "
            "its entire configuration folder per profile, keeping each account's "
            "repositories, preferences, and session completely separate.",
            r); r += 1

        # ── Quick start ───────────────────────────────────────────
        _section_header(scroll, "Quick Start", r); r += 2
        _step(scroll, 1,
            "Add your first profile",
            'Click the blue "+ Add Profile" button at the top of the main window.',
            r); r += 1
        _step(scroll, 2,
            "Fill in the three fields",
            "Profile Name is just a label (e.g. Work, Personal, GitHub). "
            "Git User Name and Git Email must match the identity you want git to use.",
            r); r += 1
        _step(scroll, 3,
            "Save and add more profiles",
            "Repeat for every identity you switch between. The active profile "
            "(matching your current git config) is highlighted in blue.",
            r); r += 1
        _step(scroll, 4,
            "Switch with one click",
            'Click "Switch" on any inactive profile card. The status bar at '
            "the bottom shows progress in real time.",
            r); r += 1

        # ── What happens during a switch ──────────────────────────
        _section_header(scroll, "What Happens During a Switch", r); r += 2
        _paragraph(scroll,
            "When GitHub Desktop integration is enabled, switching runs these "
            "five steps automatically:",
            r); r += 1

        steps = [
            ("1", "GitHub Desktop is closed so its config files are not locked."),
            ("2", "The current GitHub Desktop config folder is copied as a backup "
                  "named after the active profile."),
            ("3", "git config --global user.name and user.email are updated."),
            ("4", "The target profile's previously saved backup is restored as the "
                  "active GitHub Desktop config."),
            ("5", "GitHub Desktop relaunches — already signed in as the new account."),
        ]
        for i, (label, detail) in enumerate(steps):
            _flow_step(scroll, label, detail, r, last=(i == len(steps) - 1))
            r += 2 if i < len(steps) - 1 else 1

        _tip(scroll,
            "Tip: If a profile has no GitHub Desktop backup yet, "
            "the app skips steps 2 and 4 and only updates the git identity. "
            "A backup is created automatically the next time you switch away from it.",
            r); r += 1

        # ── GitHub Desktop integration ────────────────────────────
        _section_header(scroll, "GitHub Desktop Integration", r); r += 2
        _paragraph(scroll,
            "Open Settings to control the integration. You can disable it if "
            "you only need to switch git identities without touching GitHub Desktop, "
            "or turn off auto-launch if you prefer to open it manually.",
            r); r += 1
        _tip(scroll,
            "The 'No GH Desktop backup' badge on a card means that profile has "
            "never been made active while the integration was on. Switch to it once "
            "and then switch away — that creates the first backup.",
            r); r += 1

        # ── Data locations ────────────────────────────────────────
        _section_header(scroll, "Where Is My Data?", r); r += 2
        _paragraph(scroll, "Profile list and settings:", r); r += 1
        _copyable_mono(scroll, str(get_app_config_file()), r); r += 1
        _paragraph(scroll, "GitHub Desktop config backups:", r); r += 1
        _mono(scroll, str(get_appdata_roaming() / "GitHub Desktop-<ProfileName>"), r); r += 1
        _tip(scroll,
            "Tip: Back up the profiles.json file if you want to move your profile "
            "list to another machine. The GitHub Desktop backup folders must be "
            "copied separately.",
            r); r += 1

        # ── Keyboard / tips ───────────────────────────────────────
        _section_header(scroll, "Tips", r); r += 2
        _paragraph(scroll,
            "Press Escape to close any dialog without saving.",
            r); r += 1
        _paragraph(scroll,
            'Use "Refresh" if you changed git config outside the app and want '
            "the active profile indicator to update.",
            r); r += 1
        _paragraph(scroll,
            "Profile names are case-sensitive. 'Work' and 'work' are two different profiles.",
            r); r += 1

        # bottom padding
        ctk.CTkLabel(scroll, text="").grid(row=r, column=0, pady=6)

    # ── Footer ────────────────────────────────────────────────────

    def _build_footer(self):
        frame = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color=("gray88", "gray18"))
        frame.grid(row=2, column=0, sticky="ew")
        frame.grid_propagate(False)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            frame,
            text="Close",
            width=120,
            height=34,
            command=self.destroy,
        ).grid(row=0, column=0, pady=10)
