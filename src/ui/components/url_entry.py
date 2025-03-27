import customtkinter as ctk
import tkinter as tk
from typing import Callable
from ..dialogs.input_dialog import CenteredInputDialog


class URLEntryFrame(ctk.CTkFrame):
    """Frame for URL input and add button."""

    def __init__(
            self,
            master,
            on_add: Callable[[str, str], None]  # Callback signature: (url: str, name: str) -> None
    ):
        super().__init__(master, fg_color="transparent")

        self.on_add = on_add

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # URL Entry
        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="Enter a URL",
            height=40,
            font=("Roboto", 14)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.handle_add())

        # Add Button
        self.add_button = ctk.CTkButton(
            self,
            text="Add",
            command=self.handle_add,
            width=100,
            height=40,
            font=("Roboto", 14)
        )
        self.add_button.grid(row=0, column=1)

    def handle_add(self):
        """Handle add button click."""
        url = self.url_entry.get().strip()
        if url:
            dialog = CenteredInputDialog(
                text="Enter a name for this link:",
                title="Link Name"
            )
            name = dialog.get_input()

            if name:
                self.on_add(url, name)  # Call with two arguments
                self.url_entry.delete(0, tk.END)