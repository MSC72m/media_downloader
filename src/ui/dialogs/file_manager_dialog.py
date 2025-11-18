import os
from collections.abc import Callable
from tkinter import messagebox

import customtkinter as ctk

from src.utils.logger import get_logger
from src.utils.window import WindowCenterMixin

from ..components.file_list import FileListBox
from ..components.file_manager_buttons import FileManagerButtonBar
from ..components.path_entry import PathEntryBar
from .input_dialog import CenteredInputDialog

logger = get_logger(__name__)


class FileManagerDialog(ctk.CTkToplevel, WindowCenterMixin):
    def __init__(
        self,
        parent,
        initial_path: str,
        on_directory_change: Callable[[str], None],
        show_status: Callable[[str], None],
    ):
        super().__init__(parent)

        self.title("File Browser")
        self.geometry("600x400")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)

        # Setup window - expand any tilde paths
        self.current_path = os.path.expanduser(initial_path)
        self.on_directory_change = on_directory_change
        self.show_status = show_status

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Create widgets before centering
        self.create_widgets()
        self.update_file_list()

        # Center the window
        self.center_window()

        # Update to ensure window is drawn
        self.update_idletasks()

        # Make visible and grab focus
        self.grab_set()
        self.focus_set()

    def create_widgets(self):
        """Create and arrange all widgets."""
        # Path entry bar
        self.path_entry = PathEntryBar(self, self.current_path, self.update_file_list)
        self.path_entry.grid(row=0, column=0, columnspan=2, sticky="ew")

        # File list
        self.file_list = FileListBox(self, self.on_item_double_click)
        self.file_list.grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew"
        )

        # Action buttons
        self.action_buttons = FileManagerButtonBar(
            self, self.change_directory, self.create_folder, self.destroy
        )
        self.action_buttons.grid(
            row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew"
        )

    def update_file_list(self):
        """Update the file list with current directory contents."""
        try:
            self.current_path = os.path.expanduser(self.path_entry.get_path())
            self.file_list.update_items(self.current_path)
        except OSError as oe:
            logger.error(f"Error accessing directory: {oe}")
            self.show_status("Error: Unable to access the specified directory.")

    def on_item_double_click(self, event):
        """Handle double-click on file/directory."""
        item = self.file_list.get_selected_item()
        if not item:
            return

        # Handle parent directory
        if item == "..":
            new_path = os.path.dirname(self.current_path)
        else:
            # Remove icon prefix if present
            if item.startswith("📁 ") or item.startswith("📄 "):
                item = item[2:]
            new_path = os.path.join(self.current_path, item)

        if os.path.isdir(new_path):
            self.current_path = new_path
            self.path_entry.set_path(new_path)
            self.update_file_list()

    def change_directory(self):
        """Change the download directory."""
        if os.path.exists(self.current_path) and os.path.isdir(self.current_path):
            self.on_directory_change(self.current_path)
            logger.info(f"Download directory changed to: {self.current_path}")
            self.show_status(f"Download directory changed to: {self.current_path}")
            self.destroy()
        else:
            messagebox.showerror("Error", "Please select a valid directory.")

    def create_folder(self):
        """Create a new folder."""
        dialog = CenteredInputDialog(title="Create Folder", text="Enter folder name:")
        folder_name = dialog.get_input()

        if folder_name:
            new_folder_path = os.path.join(self.current_path, folder_name)
            try:
                os.mkdir(new_folder_path)
                logger.info(f"Created new folder: {new_folder_path}")
                self.update_file_list()
            except OSError as oe:
                logger.error(f"Error creating folder: {oe}")
                self.show_status("Error: Unable to create the folder.")
                messagebox.showerror("Error", f"Unable to create folder: {str(oe)}")
