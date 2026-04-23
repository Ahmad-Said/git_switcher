"""
Small helpers for keeping the UI responsive while background work runs.

- ButtonBusy: disables a button and animates a spinner in its label.
- TextSpinner: animates a spinner prefix in any widget with a 'text' option
  (CTkLabel, CTkButton, ...).
- run_async: run a callable on a background thread and deliver the result
  back on the Tk main thread via widget.after().

All animation is driven by widget.after() so no extra threads are needed for
the spinner itself — only the work function is threaded.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Optional

# Braille spinner frames — render cleanly in most Tk fonts.
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_INTERVAL_MS = 80


class ButtonBusy:
    """Put a button into an animated 'busy' state and restore it on stop().

    Usage:
        busy = ButtonBusy(my_button, "Loading")
        busy.start()
        ...
        busy.stop()
    """

    def __init__(self, button, loading_text: str = ""):
        self._btn = button
        self._loading_text = loading_text
        try:
            self._orig_text = button.cget("text")
        except Exception:
            self._orig_text = ""
        try:
            self._orig_state = button.cget("state")
        except Exception:
            self._orig_state = "normal"
        self._running = False
        self._idx = 0
        self._after_id = None

    def start(self):
        if self._running:
            return
        self._running = True
        try:
            self._btn.configure(state="disabled")
        except Exception:
            pass
        self._tick()

    def _tick(self):
        if not self._running:
            return
        frame = SPINNER_FRAMES[self._idx % len(SPINNER_FRAMES)]
        self._idx += 1
        text = f"{frame}  {self._loading_text}" if self._loading_text else frame
        try:
            self._btn.configure(text=text)
        except Exception:
            return
        try:
            self._after_id = self._btn.after(SPINNER_INTERVAL_MS, self._tick)
        except Exception:
            self._after_id = None

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._after_id is not None:
            try:
                self._btn.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            self._btn.configure(text=self._orig_text, state=self._orig_state)
        except Exception:
            pass


class TextSpinner:
    """Animate a spinner prefix on any widget with a 'text' option."""

    def __init__(self, widget, base_text: str = ""):
        self._w = widget
        self._base = base_text
        self._running = False
        self._idx = 0
        self._after_id = None

    def start(self, base_text: Optional[str] = None):
        if base_text is not None:
            self._base = base_text
        if self._running:
            return
        self._running = True
        self._tick()

    def _tick(self):
        if not self._running:
            return
        frame = SPINNER_FRAMES[self._idx % len(SPINNER_FRAMES)]
        self._idx += 1
        try:
            self._w.configure(text=f"{frame}  {self._base}")
        except Exception:
            return
        try:
            self._after_id = self._w.after(SPINNER_INTERVAL_MS, self._tick)
        except Exception:
            self._after_id = None

    def stop(self, final_text: Optional[str] = None):
        self._running = False
        if self._after_id is not None:
            try:
                self._w.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if final_text is not None:
            try:
                self._w.configure(text=final_text)
            except Exception:
                pass


def run_async(
    widget,
    task: Callable[[], Any],
    on_done: Optional[Callable[[Any, Optional[BaseException]], None]] = None,
    *,
    busy: Optional[ButtonBusy] = None,
    text_spinner: Optional[TextSpinner] = None,
) -> threading.Thread:
    """Run `task()` in a background thread; deliver the result back on the
    Tk main loop.

    on_done is called as on_done(result, error). `error` is None on success.
    Any spinner passed via `busy` / `text_spinner` is stopped before on_done.
    """
    if busy is not None:
        busy.start()
    if text_spinner is not None:
        text_spinner.start()

    def worker():
        result: Any = None
        error: Optional[BaseException] = None
        try:
            result = task()
        except BaseException as exc:  # noqa: BLE001
            error = exc

        def deliver():
            if busy is not None:
                busy.stop()
            if text_spinner is not None:
                text_spinner.stop()
            if on_done is not None:
                try:
                    on_done(result, error)
                except Exception:
                    pass

        try:
            widget.after(0, deliver)
        except Exception:
            # widget destroyed — drop the result silently.
            pass

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread

