import customtkinter as ctk
from src.utils.logger import get_logger
from typing import Callable, Dict
from src.core.downloads.models import ButtonState

logger = get_logger(__name__)


class ActionButtonBar(ctk.CTkFrame):
    """Frame containing action buttons for main window."""

    def __init__(
            self,
            master,
            on_remove: Callable[[], None],
            on_clear: Callable[[], None],
            on_download: Callable[[], None],
            on_manage_files: Callable[[], None]
    ):
        super().__init__(master, fg_color="transparent")

        # Configure grid
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Track download state
        self._download_in_progress = False

        # Common button style
        self.button_style = {
            "height": 40,
            "font": ("Roboto", 14),
            "corner_radius": 10
        }

        # Remove Button
        self.remove_button = ctk.CTkButton(
            self,
            text="Remove Selected",
            command=on_remove,
            **self.button_style
        )
        self.remove_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Clear Button
        self.clear_button = ctk.CTkButton(
            self,
            text="Clear All",
            command=on_clear,
            **self.button_style
        )
        self.clear_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Download Button
        def on_download_with_logging():
            logger.info("[ACTION_BUTTONS] Download All button clicked")
            logger.info(f"[ACTION_BUTTONS] on_download callback: {on_download}")
            try:
                on_download()
                logger.info("[ACTION_BUTTONS] on_download callback executed successfully")
            except Exception as e:
                logger.error(f"[ACTION_BUTTONS] Error in on_download callback: {e}", exc_info=True)

        self.download_button = ctk.CTkButton(
            self,
            text="Download All",
            command=on_download_with_logging,
            **self.button_style
        )
        self.download_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Manage Files Button
        self.manage_files_button = ctk.CTkButton(
            self,
            text="Manage Files",
            command=on_manage_files,
            **self.button_style
        )
        self.manage_files_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    def set_button_state(self, button_name: str, state: str):
        """Set state for a specific button."""
        button_map = {
            "remove": self.remove_button,
            "clear": self.clear_button,
            "download": self.download_button,
            "manage": self.manage_files_button
        }
        if button_name in button_map:
            button_map[button_name].configure(state=state)

    def set_enabled(self, enabled: bool):
        """Enable or disable all buttons."""
        logger.info(f"[ACTION_BUTTONS] set_enabled called with: {enabled}")
        state = "normal" if enabled else "disabled"
        logger.info(f"[ACTION_BUTTONS] Setting button state to: {state}")

        # Track download state
        self._download_in_progress = not enabled

        for button in [self.remove_button, self.clear_button,
                       self.download_button, self.manage_files_button]:
            button.configure(state=state)
        logger.info(f"[ACTION_BUTTONS] All buttons configured with state: {state}")

    def update_button_states(self, has_selection: bool, has_items: bool):
        """Update button states based on selection and items."""
        logger.info(f"[ACTION_BUTTONS] update_button_states called: has_selection={has_selection}, has_items={has_items}")
        logger.info(f"[ACTION_BUTTONS] Download in progress: {self._download_in_progress}")

        # If download is in progress, don't change button states
        if self._download_in_progress:
            logger.info("[ACTION_BUTTONS] Download in progress, keeping current button states")
            return

        remove_state = "normal" if has_selection else "disabled"
        clear_state = "normal" if has_items else "disabled"
        download_state = "normal" if has_items else "disabled"

        logger.info(f"[ACTION_BUTTONS] Setting remove_button to: {remove_state}")
        self.remove_button.configure(state=remove_state)

        logger.info(f"[ACTION_BUTTONS] Setting clear_button to: {clear_state}")
        self.clear_button.configure(state=clear_state)

        logger.info(f"[ACTION_BUTTONS] Setting download_button to: {download_state}")
        self.download_button.configure(state=download_state)

    def update_states(self, button_states: Dict[ButtonState, bool]):
        """Update button states using the new enum-based system."""
        # Map ButtonState to actual buttons - only handle buttons that exist in this UI
        button_mapping = {
            ButtonState.REMOVE: self.remove_button,
            ButtonState.CLEAR: self.clear_button,
            ButtonState.DOWNLOAD: self.download_button,
            ButtonState.SETTINGS: self.manage_files_button  # Map settings to manage files
        }

        # Only update states for buttons that exist in this component
        for button_state, button in button_mapping.items():
            if button_state in button_states:
                state = "normal" if button_states[button_state] else "disabled"
                button.configure(state=state)