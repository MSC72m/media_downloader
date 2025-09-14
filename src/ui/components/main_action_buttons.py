import customtkinter as ctk
from typing import Callable, Dict
from src.models import ButtonState


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
        self.download_button = ctk.CTkButton(
            self,
            text="Download All",
            command=on_download,
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
        state = "normal" if enabled else "disabled"
        for button in [self.remove_button, self.clear_button,
                       self.download_button, self.manage_files_button]:
            button.configure(state=state)

    def update_button_states(self, has_selection: bool, has_items: bool):
        """Update button states based on selection and items."""
        self.remove_button.configure(state="normal" if has_selection else "disabled")
        self.clear_button.configure(state="normal" if has_items else "disabled")
        self.download_button.configure(state="normal" if has_items else "disabled")

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