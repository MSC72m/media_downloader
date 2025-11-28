from collections.abc import Callable

import customtkinter as ctk


class PathEntryBar(ctk.CTkFrame):
    """Frame for path entry and navigation."""

    def __init__(self, master, initial_path: str, on_path_change: Callable):
        super().__init__(master, fg_color="transparent")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Path variable
        self.path_var = ctk.StringVar(value=initial_path)

        # Path entry
        self.entry = ctk.CTkEntry(self, textvariable=self.path_var, height=40, font=("Roboto", 14))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(20, 10), pady=20)

        # Go button
        self.go_button = ctk.CTkButton(
            self,
            text="Go",
            width=60,
            command=on_path_change,
            height=40,
            font=("Roboto", 14),
        )
        self.go_button.grid(row=0, column=1, padx=(0, 20), pady=20)

    def get_path(self) -> str:
        """Get current path."""
        return self.path_var.get()

    def set_path(self, path: str):
        """Set new path."""
        self.path_var.set(path)
