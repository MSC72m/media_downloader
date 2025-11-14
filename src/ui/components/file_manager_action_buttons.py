from collections.abc import Callable

import customtkinter as ctk


class FileManagerActionButtonBar(ctk.CTkFrame):
    """Frame containing action buttons for file manager."""

    def __init__(
        self,
        master,
        on_change_dir: Callable[[], None],
        on_create_folder: Callable[[], None],
        on_cancel: Callable[[], None],
    ):
        super().__init__(master, fg_color="transparent")

        # Configure grid
        self.grid_columnconfigure((0, 1, 2), weight=1)

        # Button style
        button_style = {"height": 40, "font": ("Roboto", 14), "corner_radius": 10}

        # Set as Download Directory button
        self.change_dir_button = ctk.CTkButton(
            self,
            text="Set as Download Directory",
            command=on_change_dir,
            **button_style,
        )
        self.change_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Create Folder button
        self.create_folder_button = ctk.CTkButton(
            self, text="Create Folder", command=on_create_folder, **button_style
        )
        self.create_folder_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Cancel button
        self.cancel_button = ctk.CTkButton(
            self, text="Cancel", command=on_cancel, **button_style
        )
        self.cancel_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

    def set_enabled(self, enabled: bool):
        """Enable or disable all buttons."""
        state = "normal" if enabled else "disabled"
        self.change_dir_button.configure(state=state)
        self.create_folder_button.configure(state=state)
        self.cancel_button.configure(state=state)
