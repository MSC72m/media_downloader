from __future__ import annotations

import customtkinter as ctk

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeSwitcher(ctk.CTkFrame):
    def __init__(self, master, theme_manager: ThemeManager | None = None) -> None:
        super().__init__(master, fg_color="transparent")

        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, sticky="e")

        current_mode = self._theme_manager.get_appearance()
        is_dark = current_mode == AppearanceMode.DARK

        self.appearance_switch = ctk.CTkSwitch(
            container,
            text="🌙 Dark" if is_dark else "☀️ Light",
            command=self._on_appearance_toggle,
            font=("Roboto", 11),
            width=90,
        )
        if is_dark:
            self.appearance_switch.select()
        self.appearance_switch.grid(row=0, column=0, padx=(0, 15))

        self.color_label = ctk.CTkLabel(container, text="Theme:", font=("Roboto", 11))
        self.color_label.grid(row=0, column=1, padx=(0, 5), sticky="w")

        theme_emoji_map = {
            ColorTheme.BLUE: "🔵",
            ColorTheme.GREEN: "🟢",
            ColorTheme.PURPLE: "🟣",
            ColorTheme.ORANGE: "🟠",
            ColorTheme.TEAL: "🔷",
            ColorTheme.PINK: "🌸",
            ColorTheme.INDIGO: "💙",
            ColorTheme.AMBER: "🟡",
            ColorTheme.RED: "🔴",
            ColorTheme.CYAN: "🔵",
            ColorTheme.EMERALD: "💚",
            ColorTheme.ROSE: "🌹",
            ColorTheme.VIOLET: "🟣",
            ColorTheme.SLATE: "⚫",
        }

        color_values = [
            f"{theme_emoji_map.get(theme, '🔵')} {theme.value.capitalize()}" for theme in ColorTheme
        ]
        current_color = self._theme_manager.get_color_theme()
        current_emoji = theme_emoji_map.get(current_color, "🔵")
        current_display = f"{current_emoji} {current_color.value.capitalize()}"

        self.color_dropdown = ctk.CTkComboBox(
            container,
            values=color_values,
            command=self._on_color_change,
            font=("Roboto", 11),
            width=130,
            height=30,
            dropdown_font=("Roboto", 11),
        )
        self.color_dropdown.set(current_display)
        self.color_dropdown.grid(row=0, column=2, padx=(0, 0))

        self._make_combobox_readonly()

        self._apply_theme_colors()

    def _make_combobox_readonly(self) -> None:
        def prevent_edit(event) -> str | None:
            if event.keysym not in ("Return", "Escape", "Up", "Down"):
                return "break"
            return None

        def prevent_selection(_event) -> str:
            return "break"

        try:
            entry = self.color_dropdown._entry
            entry.bind("<Key>", prevent_edit)
            entry.bind("<Button-1>", lambda _e: self.color_dropdown._open_dropdown_menu())
            entry.bind("<Control-a>", prevent_selection)
            entry.bind("<Button-3>", prevent_selection)
        except Exception:
            pass

    @staticmethod
    def _normalize_color(color):
        """Extract a single color string from a theme color value (may be list/tuple)."""
        if isinstance(color, list | tuple) and len(color) > 0:
            return color[0] if isinstance(color[0], str) else str(color[0])
        if not isinstance(color, str):
            return str(color)
        return color

    def _apply_theme_colors(self) -> None:
        theme_json = self._theme_manager.get_theme_json()

        if button_config := theme_json.get("CTkButton", {}):
            button_color = self._normalize_color(button_config.get("fg_color"))
            hover_color = self._normalize_color(button_config.get("hover_color"))

            self.appearance_switch.configure(
                progress_color=button_color,
                button_color=button_color,
                button_hover_color=hover_color,
            )

        if (entry_config := theme_json.get("CTkEntry", {})) and button_config:
            fg_color = self._normalize_color(entry_config.get("fg_color"))
            border_color = self._normalize_color(entry_config.get("border_color"))
            button_color = self._normalize_color(button_config.get("fg_color"))
            hover_color = self._normalize_color(button_config.get("hover_color"))

            self.color_dropdown.configure(
                fg_color=fg_color,
                border_color=border_color,
                button_color=button_color,
                button_hover_color=hover_color,
            )

        if label_config := theme_json.get("CTkLabel", {}):
            text_color = self._normalize_color(label_config.get("text_color"))
            self.color_label.configure(text_color=text_color)

    def _on_appearance_toggle(self) -> None:
        is_dark = self.appearance_switch.get()
        appearance = AppearanceMode.DARK if is_dark else AppearanceMode.LIGHT
        current_color = self._theme_manager.get_color_theme()

        logger.info(f"[THEME_SWITCHER] Changing appearance to {appearance.value}")
        self._theme_manager.set_theme(appearance, current_color)

        self.appearance_switch.configure(text="🌙 Dark" if is_dark else "☀️ Light")

    def _on_color_change(self, value: str) -> None:
        color_name = value.rsplit(maxsplit=1)[-1].lower()
        try:
            color = ColorTheme(color_name)
            current_appearance = self._theme_manager.get_appearance()

            logger.info(f"[THEME_SWITCHER] Changing color to {color.value}")
            self._theme_manager.set_theme(current_appearance, color)
        except ValueError:
            logger.error(f"[THEME_SWITCHER] Invalid color theme: {color_name}")

    def _on_theme_changed(self, appearance, color) -> None:
        self._apply_theme_colors()

        theme_emoji_map = {
            ColorTheme.BLUE: "🔵",
            ColorTheme.GREEN: "🟢",
            ColorTheme.PURPLE: "🟣",
            ColorTheme.ORANGE: "🟠",
            ColorTheme.TEAL: "🔷",
            ColorTheme.PINK: "🌸",
            ColorTheme.INDIGO: "💙",
            ColorTheme.AMBER: "🟡",
            ColorTheme.RED: "🔴",
            ColorTheme.CYAN: "🔵",
            ColorTheme.EMERALD: "💚",
            ColorTheme.ROSE: "🌹",
            ColorTheme.VIOLET: "🟣",
            ColorTheme.SLATE: "⚫",
        }
        emoji = theme_emoji_map.get(color, "🔵")
        current_display = f"{emoji} {color.value.capitalize()}"
        self.color_dropdown.set(current_display)
