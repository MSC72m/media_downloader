"""Compact URL input bar for the queue-first desktop layout."""

from __future__ import annotations

import contextlib
import re
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GlassButton, GlassFrame, GradientButton, resolve_palette

_YOUTUBE_DOMAIN_PATTERN = re.compile(r"(?:youtube\.com|youtu\.be)", re.IGNORECASE)
_SERVICE_DOMAIN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:youtube\.com|youtu\.be|music\.youtube\.com)", re.IGNORECASE), "YT"),
    (re.compile(r"open\.spotify\.com|spotify\.link", re.IGNORECASE), "SP"),
    (re.compile(r"soundcloud\.com", re.IGNORECASE), "SC"),
    (re.compile(r"tiktok\.com", re.IGNORECASE), "TK"),
    (re.compile(r"instagram\.com|instagr\.am", re.IGNORECASE), "IG"),
    (re.compile(r"twitter\.com|x\.com", re.IGNORECASE), "X"),
    (re.compile(r"pinterest\.com|pin\.it", re.IGNORECASE), "PI"),
    (re.compile(r"radiojavan\.com|rj\.app", re.IGNORECASE), "RJ"),
]


class URLEntryFrame(GlassFrame):
    """One-row link input with integrated platform, paste, clear, and add actions."""

    def __init__(
        self,
        master,
        on_add: Callable[[str, str], None],
        on_youtube_detected: Callable[[str], None] | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        super().__init__(
            master,
            theme_manager=self._theme_manager,
            elevation="raised",
            corner_radius=14,
        )
        self.on_add = on_add
        self.on_youtube_detected = on_youtube_detected
        self._detected_badge: str | None = None

        self.grid_columnconfigure(1, weight=1)

        self._platform_badge = ctk.CTkLabel(
            self,
            text="LINK",
            width=42,
            height=30,
            corner_radius=8,
            font=("Roboto", 9, "bold"),
        )
        self._platform_badge.grid(row=0, column=0, padx=(10, 7), pady=9)

        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="Paste a media URL…",
            height=38,
            corner_radius=10,
            border_width=0,
            font=("Roboto", 13, "normal"),
        )
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=7)
        self.url_entry.bind("<KeyRelease>", self._on_key_release, add=True)
        self.url_entry.bind("<Return>", lambda _event: self.handle_add(), add=True)
        self.url_entry.bind("<FocusIn>", self._on_focus_in, add=True)
        self.url_entry.bind("<FocusOut>", self._on_focus_out, add=True)

        self.paste_button = GlassButton(
            self,
            text="Paste",
            width=58,
            height=32,
            variant="ghost",
            command=self._paste,
            theme_manager=self._theme_manager,
        )
        self.paste_button.grid(row=0, column=2, padx=(7, 2), pady=9)

        self.clear_button = GlassButton(
            self,
            text="×",
            width=32,
            height=32,
            variant="ghost",
            command=self.clear,
            theme_manager=self._theme_manager,
        )
        self.clear_button.grid(row=0, column=3, padx=2, pady=9)
        self.clear_button.grid_remove()

        self.add_button = GradientButton(
            self,
            text="Add download",
            command=self.handle_add,
            width=126,
            height=38,
            corner_radius=10,
            theme_manager=self._theme_manager,
        )
        self.add_button.grid(row=0, column=4, padx=(6, 9), pady=7, sticky="e")

        self._install_clipboard_support()
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self._apply_palette()

    def _install_clipboard_support(self) -> None:
        for sequence in ("<Control-v>", "<Control-V>", "<Command-v>"):
            self.url_entry.bind(sequence, self._paste, add=True)
        for sequence in ("<Control-c>", "<Control-C>", "<Command-c>"):
            self.url_entry.bind(sequence, self._copy, add=True)
        for sequence in ("<Control-x>", "<Control-X>", "<Command-x>"):
            self.url_entry.bind(sequence, self._cut, add=True)

        self._context_menu = tk.Menu(self.url_entry, tearoff=0)
        self._context_menu.add_command(label="Paste", command=self._paste)
        self._context_menu.add_command(label="Copy", command=self._copy)
        self._context_menu.add_command(label="Cut", command=self._cut)
        for sequence in ("<Button-2>", "<Button-3>"):
            self.url_entry.bind(sequence, self._show_context_menu, add=True)

    def _show_context_menu(self, event: tk.Event) -> str:
        with contextlib.suppress(tk.TclError):
            self._context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _paste(self, _event: tk.Event | None = None) -> str:
        try:
            text = self.url_entry.clipboard_get()
        except tk.TclError:
            return "break"
        with contextlib.suppress(tk.TclError):
            if self.url_entry.select_present():
                self.url_entry.delete("sel.first", "sel.last")
        self.url_entry.insert(tk.INSERT, text.strip())
        self._on_key_release()
        return "break"

    def _copy(self, _event: tk.Event | None = None) -> str:
        with contextlib.suppress(tk.TclError):
            if self.url_entry.select_present():
                self.clipboard_clear()
                self.clipboard_append(self.url_entry.selection_get())
        return "break"

    def _cut(self, _event: tk.Event | None = None) -> str:
        self._copy()
        with contextlib.suppress(tk.TclError):
            if self.url_entry.select_present():
                self.url_entry.delete("sel.first", "sel.last")
        self._on_key_release()
        return "break"

    def _on_key_release(self, _event: tk.Event | None = None) -> None:
        value = self.url_entry.get().strip()
        badge = next(
            (label for pattern, label in _SERVICE_DOMAIN_PATTERNS if pattern.search(value)), None
        )
        if badge != self._detected_badge:
            self._detected_badge = badge
            self._platform_badge.configure(text=badge or "LINK")
        if value:
            self.clear_button.grid()
        else:
            self.clear_button.grid_remove()

    def _on_focus_in(self, _event: tk.Event | None = None) -> None:
        palette = resolve_palette(self._theme_manager)
        self.url_entry.configure(border_width=1, border_color=palette.accent)

    def _on_focus_out(self, _event: tk.Event | None = None) -> None:
        palette = resolve_palette(self._theme_manager)
        self.url_entry.configure(border_width=0, border_color=palette.border)

    def _apply_palette(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self.url_entry.configure(
            fg_color=palette.surface,
            text_color=palette.text,
            placeholder_text_color=palette.text_muted,
            border_color=palette.border,
        )
        self._platform_badge.configure(
            fg_color=palette.surface_hover,
            text_color=palette.accent if self._detected_badge else palette.text_muted,
        )

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_palette()

    def handle_add(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            self.url_entry.focus_set()
            return
        if self.on_youtube_detected and _YOUTUBE_DOMAIN_PATTERN.search(url):
            self.on_youtube_detected(url)
            self.clear()
            return
        tail = url.rstrip("/").split("/")[-1]
        name = tail.replace("-", " ").replace("_", " ").title() or url
        self.on_add(url, name[:80])
        self.clear()

    def clear(self) -> None:
        self.url_entry.delete(0, tk.END)
        self._detected_badge = None
        self._platform_badge.configure(text="LINK")
        self.clear_button.grid_remove()
        self._apply_palette()

    def get_url(self) -> str:
        return self.url_entry.get().strip()

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
