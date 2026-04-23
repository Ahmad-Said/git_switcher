import os
import sys
import threading

import customtkinter as ctk

from core.updater import (
    ReleaseInfo,
    apply_update,
    download_release,
    fetch_latest_release,
    is_frozen,
    is_newer,
)
from version import __version__


class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Check for Updates")
        self.geometry("460x340")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._release: ReleaseInfo | None = None

        self.grid_columnconfigure(0, weight=1)
        self._build()
        self.bind("<Escape>", lambda _e: self._safe_close())

        # Auto-check as soon as the dialog is visible
        self.after(100, self._do_check)

    # ── Layout ────────────────────────────────────────────────────

    def _build(self):
        # Version row
        ver_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray17"), corner_radius=0)
        ver_frame.grid(row=0, column=0, sticky="ew")
        ver_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            ver_frame,
            text=f"Current version:  v{__version__}",
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).grid(row=0, column=0, padx=20, pady=14, sticky="w")

        # Status area
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(16, 6))
        status_frame.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            status_frame,
            text="Checking for updates...",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color=("gray40", "gray60"),
        )
        self._status_label.grid(row=0, column=0, sticky="w")

        self._check_btn = ctk.CTkButton(
            status_frame,
            text="Re-check",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            command=self._do_check,
            state="disabled",
        )
        self._check_btn.grid(row=0, column=1, sticky="e")

        # Release notes box (shown only when update is available)
        self._notes_box = ctk.CTkTextbox(
            self,
            height=100,
            font=ctk.CTkFont(size=11),
            state="disabled",
            wrap="word",
        )
        self._notes_box.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))
        self._notes_box.grid_remove()   # hidden initially

        # Progress bar (shown during download)
        self._progress = ctk.CTkProgressBar(self, mode="determinate")
        self._progress.set(0)
        self._progress.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 2))
        self._progress.grid_remove()

        self._progress_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        )
        self._progress_label.grid(row=4, column=0, pady=(0, 4))
        self._progress_label.grid_remove()

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=(8, 16))

        self._close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            width=110,
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color=("gray55", "gray45"),
            text_color=("gray15", "gray85"),
            hover_color=("gray82", "gray28"),
            command=self._safe_close,
        )
        self._close_btn.pack(side="left", padx=6)

        self._download_btn = ctk.CTkButton(
            btn_frame,
            text="Download & Apply",
            width=150,
            height=34,
            command=self._do_download,
            state="disabled",
        )
        self._download_btn.pack(side="left", padx=6)

    # ── Update check ─────────────────────────────────────────────

    def _do_check(self):
        self._check_btn.configure(state="disabled")
        self._download_btn.configure(state="disabled")
        self._notes_box.grid_remove()
        self._status_label.configure(
            text="Checking for updates...",
            text_color=("gray40", "gray60"),
        )

        def worker():
            release, error = fetch_latest_release()
            self.after(0, lambda: self._on_check_done(release, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_done(self, release: ReleaseInfo | None, error: str | None):
        self._check_btn.configure(state="normal")

        if error:
            self._status_label.configure(
                text=f"Could not check: {error}",
                text_color=("#c0392b", "#e05555"),
            )
            return

        self._release = release
        if not is_newer(release):
            self._status_label.configure(
                text=f"You are up to date  (latest: {release.tag})",
                text_color=("#2d7a4a", "#4caf7d"),
            )
            return

        # Update available
        self._status_label.configure(
            text=f"Update available:  {release.tag}  —  {release.name}",
            text_color=("#1a5fa8", "#4a9eff"),
        )

        if release.release_notes:
            self._notes_box.configure(state="normal")
            self._notes_box.delete("1.0", "end")
            self._notes_box.insert("1.0", release.release_notes)
            self._notes_box.configure(state="disabled")
            self._notes_box.grid()
            self.geometry("460x420")

        if is_frozen():
            self._download_btn.configure(state="normal")
        else:
            self._download_btn.configure(
                text="Dev mode — no update",
                state="disabled",
            )

    # ── Download & apply ─────────────────────────────────────────

    def _do_download(self):
        if not self._release:
            return

        self._download_btn.configure(state="disabled")
        self._check_btn.configure(state="disabled")
        self._close_btn.configure(state="disabled")
        self._progress.set(0)
        self._progress.grid()
        self._progress_label.configure(text="Starting download...")
        self._progress_label.grid()

        release = self._release

        def on_progress(downloaded: int, total: int):
            if total > 0:
                ratio = downloaded / total
                mb_done = downloaded / 1_048_576
                mb_total = total / 1_048_576
                self.after(0, lambda r=ratio, d=mb_done, t=mb_total: (
                    self._progress.set(r),
                    self._progress_label.configure(
                        text=f"Downloading...  {d:.1f} / {t:.1f} MB"
                    ),
                ))
            else:
                mb = downloaded / 1_048_576
                self.after(0, lambda m=mb: (
                    self._progress.configure(mode="indeterminate"),
                    self._progress.start(),
                    self._progress_label.configure(text=f"Downloading...  {m:.1f} MB"),
                ))

        def worker():
            path, error = download_release(release, on_progress)
            self.after(0, lambda: self._on_download_done(path, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_done(self, path, error):
        self._progress.stop()
        self._progress.configure(mode="determinate")

        if error:
            self._progress.grid_remove()
            self._progress_label.configure(
                text=f"Download failed: {error}",
                text_color=("#c0392b", "#e05555"),
            )
            self._close_btn.configure(state="normal")
            self._download_btn.configure(state="normal")
            return

        self._progress.set(1)
        self._progress_label.configure(text="Download complete. Applying update...")

        try:
            apply_update(path)
        except Exception as exc:
            self._progress_label.configure(
                text=f"Apply failed: {exc}",
                text_color=("#c0392b", "#e05555"),
            )
            self._close_btn.configure(state="normal")
            return

        # Update applied — exit so the batch script can replace the exe
        self._progress_label.configure(
            text="Update ready. Restarting...",
            text_color=("#2d7a4a", "#4caf7d"),
        )
        # os._exit() is required here — sys.exit() raises SystemExit which
        # tkinter's event loop swallows, leaving the process alive and the
        # waiting batch script stuck. os._exit() kills the process immediately.
        self.after(1200, lambda: os._exit(0))

    # ── Close ─────────────────────────────────────────────────────

    def _safe_close(self):
        if self._close_btn.cget("state") != "disabled":
            self.destroy()
