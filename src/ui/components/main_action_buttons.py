from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ActionButtonBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_remove: Callable[[], None],
        on_clear: Callable[[], None],
        on_download: Callable[[], None],
        on_manage_files: Callable[[], None],
        theme_manager: ThemeManager | None = None,
    ):
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
        }

        def on_download_with_logging():
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
        )
        self.download_button.grid(row=0, column=2, padx=(0, 8), pady=0, sticky="ew")

        self.manage_files_button = ctk.CTkButton(
            self, text="Manage Files", command=on_manage_files, **self.button_style
        )
        self.manage_files_button.grid(row=0, column=3, padx=0, pady=0, sticky="ew")

        logger.info("[ACTION_BUTTONS] Setting initial button states to enabled")
        self.set_enabled(True)

        self._apply_theme_colors()

    def set_button_state(self, button_name: str, state: str):
        button_map = {
            "remove": self.remove_button,
            "clear": self.clear_button,
            "download": self.download_button,
            "manage": self.manage_files_button,
        }
        if button_name in button_map:
            button_map[button_name].configure(state=state)

    def set_enabled(self, enabled: bool):
        logger.debug(f"[ACTION_BUTTONS] set_enabled called with: {enabled}")
        state = "normal" if enabled else "disabled"
        logger.debug(f"[ACTION_BUTTONS] Setting button state to: {state}")

        self._download_in_progress = not enabled

        for button in [
            self.remove_button,
            self.clear_button,
            self.download_button,
            self.manage_files_button,
        ]:
            button.configure(state=state)
        logger.debug(f"[ACTION_BUTTONS] All buttons configured with state: {state}")

    def update_button_states(self, has_selection: bool, has_items: bool):
        logger.debug(
            f"[ACTION_BUTTONS] update_button_states called: has_selection={has_selection}, has_items={has_items}"
        )
        logger.debug(f"[ACTION_BUTTONS] Download in progress: {self._download_in_progress}")

        if self._download_in_progress:
            logger.debug("[ACTION_BUTTONS] Download in progress, keeping current button states")
            return

        remove_state = "normal" if has_selection else "disabled"
        clear_state = "normal" if has_items else "disabled"
        download_state = "normal" if has_items else "disabled"

        logger.debug(f"[ACTION_BUTTONS] Setting remove_button to: {remove_state}")
        self.remove_button.configure(state=remove_state)

        logger.debug(f"[ACTION_BUTTONS] Setting clear_button to: {clear_state}")
        self.clear_button.configure(state=clear_state)

        logger.debug(f"[ACTION_BUTTONS] Setting download_button to: {download_state}")
        self.download_button.configure(state=download_state)

        manage_state = "normal" if has_items else "disabled"
        logger.debug(f"[ACTION_BUTTONS] Setting manage_files_button to: {manage_state}")
        self.manage_files_button.configure(state=manage_state)

    def _apply_theme_colors(self):
        theme_json = self._theme_manager.get_theme_json()

        button_config = theme_json.get("CTkButton", {})
        if button_config:
            button_color = button_config.get("fg_color")
            hover_color = button_config.get("hover_color")
            text_color = button_config.get("text_color")

            if isinstance(button_color, tuple):
                button_color = (
                    button_color[0] if isinstance(button_color[0], str) else str(button_color[0])
                )
            elif not isinstance(button_color, str):
                button_color = str(button_color)

            if isinstance(hover_color, tuple):
                hover_color = (
                    hover_color[0] if isinstance(hover_color[0], str) else str(hover_color[0])
                )
            elif not isinstance(hover_color, str):
                hover_color = str(hover_color)

            if button_color:
                for button in [
                    self.remove_button,
                    self.clear_button,
                    self.download_button,
                    self.manage_files_button,
                ]:
                    button.configure(
                        fg_color=button_color,
                        hover_color=hover_color,
                        text_color=text_color,
                    )

    def _on_theme_changed(self, appearance, color):
        self._apply_theme_colors()
