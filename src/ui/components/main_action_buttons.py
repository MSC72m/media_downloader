from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Disabled buttons must read as disabled by graying the BUTTON, not just the
# text (accessibility feedback: gray text on a still-coloured fill fails
# contrast). Tuples are (light, dark) so CTk picks per appearance mode.
_DISABLED_FILL = ("#C7CBD1", "#3A3F44")
_DISABLED_TEXT = ("#6B7280", "#9AA0A6")
_ENABLED_TEXT = "#FFFFFF"  # high contrast on the saturated accent fills


class ActionButtonBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_remove: Callable[[], None],
        on_clear: Callable[[], None],
        on_download: Callable[[], None],
        on_manage_files: Callable[[], None],
        theme_manager: ThemeManager | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")

        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._download_in_progress = False
        logger.info(
            f"[ACTION_BUTTONS] Initialized with _download_in_progress={self._download_in_progress}"
        )

        root_window = master.winfo_toplevel()
        self._theme_manager = theme_manager or get_theme_manager(root_window)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.button_style = {
            "height": 45,
            "font": ("Roboto", 13),
            "corner_radius": 8,
            "border_width": 0,
            "text_color": _ENABLED_TEXT,
            "text_color_disabled": _DISABLED_TEXT,
        }

        # Enabled fill/hover are populated from the theme in _apply_theme_colors.
        self._enabled_fill: str | None = None
        self._enabled_hover: str | None = None

        def on_download_with_logging() -> None:
            logger.info("[ACTION_BUTTONS] Download All button clicked")
            logger.info(f"[ACTION_BUTTONS] on_download callback: {on_download}")
            try:
                on_download()
                logger.info("[ACTION_BUTTONS] on_download callback executed successfully")
            except Exception as e:
                logger.error(
                    f"[ACTION_BUTTONS] Error in on_download callback: {e}",
                    exc_info=True,
                )

        self.remove_button = ctk.CTkButton(
            self, text="Remove Selected", command=on_remove, **self.button_style
        )
        self.remove_button.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="ew")

        self.clear_button = ctk.CTkButton(
            self, text="Clear All", command=on_clear, **self.button_style
        )
        self.clear_button.grid(row=0, column=1, padx=(0, 8), pady=0, sticky="ew")

        self.download_button = ctk.CTkButton(
            self,
            text="Download All",
            command=on_download_with_logging,
            height=45,
            font=("Roboto", 13),
            corner_radius=8,
            border_width=0,
            text_color=_ENABLED_TEXT,
            text_color_disabled=_DISABLED_TEXT,
        )
        self.download_button.grid(row=0, column=2, padx=(0, 8), pady=0, sticky="ew")

        self.manage_files_button = ctk.CTkButton(
            self, text="Manage Files", command=on_manage_files, **self.button_style
        )
        self.manage_files_button.grid(row=0, column=3, padx=0, pady=0, sticky="ew")

        logger.info("[ACTION_BUTTONS] Setting initial button states to enabled")
        self._apply_theme_colors()
        self.set_enabled(True)

    def _all_buttons(self) -> list[ctk.CTkButton]:
        return [
            self.remove_button,
            self.clear_button,
            self.download_button,
            self.manage_files_button,
        ]

    def _set_state(self, button: ctk.CTkButton, enabled: bool) -> None:
        """Enable/disable a button AND its fill, so disabled buttons look
        disabled (neutral gray) instead of a vivid fill with gray text."""
        if enabled and self._enabled_fill:
            button.configure(
                state="normal",
                fg_color=self._enabled_fill,
                hover_color=self._enabled_hover,
            )
        elif enabled:
            button.configure(state="normal")
        else:
            button.configure(
                state="disabled",
                fg_color=_DISABLED_FILL,
                hover_color=_DISABLED_FILL,
            )

    def set_button_state(self, button_name: str, state: str) -> None:
        button_map = {
            "remove": self.remove_button,
            "clear": self.clear_button,
            "download": self.download_button,
            "manage": self.manage_files_button,
        }
        if button_name in button_map:
            self._set_state(button_map[button_name], state == "normal")

    def set_enabled(self, enabled: bool) -> None:
        logger.debug(f"[ACTION_BUTTONS] set_enabled called with: {enabled}")
        self._download_in_progress = not enabled
        for button in self._all_buttons():
            self._set_state(button, enabled)

    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        logger.debug(
            f"[ACTION_BUTTONS] update_button_states called: has_selection={has_selection}, has_items={has_items}"
        )
        logger.debug(f"[ACTION_BUTTONS] Download in progress: {self._download_in_progress}")

        if self._download_in_progress:
            logger.debug("[ACTION_BUTTONS] Download in progress, keeping current button states")
            return

        self._set_state(self.remove_button, has_selection)
        self._set_state(self.clear_button, has_items)
        self._set_state(self.download_button, has_items)
        self._set_state(self.manage_files_button, has_items)

    def _apply_theme_colors(self) -> None:
        theme_json = self._theme_manager.get_theme_json()

        if button_config := theme_json.get("CTkButton", {}):
            button_color = button_config.get("fg_color")
            hover_color = button_config.get("hover_color")

            # Handle button_color - extract first element if it's a list or tuple
            if isinstance(button_color, list | tuple) and len(button_color) > 0:
                button_color = (
                    button_color[0] if isinstance(button_color[0], str) else str(button_color[0])
                )
            elif not isinstance(button_color, str):
                button_color = str(button_color)

            # Handle hover_color - extract first element if it's a list or tuple
            if isinstance(hover_color, list | tuple) and len(hover_color) > 0:
                hover_color = (
                    hover_color[0] if isinstance(hover_color[0], str) else str(hover_color[0])
                )
            elif not isinstance(hover_color, str):
                hover_color = str(hover_color)

            if button_color:
                self._enabled_fill = button_color
                self._enabled_hover = hover_color
                for button in self._all_buttons():
                    button.configure(text_color=_ENABLED_TEXT)
                    # Preserve each button's current enabled/disabled visual.
                    self._set_state(button, str(button.cget("state")) == "normal")

    def _on_theme_changed(self, appearance, color) -> None:
        self._apply_theme_colors()

    def destroy(self) -> None:
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
