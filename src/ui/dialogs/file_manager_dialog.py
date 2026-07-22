import os
from collections.abc import Callable
from typing import Any

from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.events.queue import Message
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassFrame
from src.utils.logger import get_logger

from ..components.file_list import FileListBox
from ..components.file_manager_buttons import FileManagerButtonBar
from ..components.path_entry import PathEntryBar
from .base_dialog import BaseDialog
from .input_dialog import CenteredInputDialog

logger = get_logger(__name__)


class FileManagerDialog(BaseDialog):
    def __init__(
        self,
        parent: Any,
        initial_path: str,
        on_directory_change: Callable[[str], None],
        show_status: Callable[[str], None],
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        super().__init__(parent, title="File Browser", theme_manager=theme_manager)

        self.current_path = os.path.expanduser(initial_path)
        self.on_directory_change = on_directory_change
        self.show_status = show_status
        self.error_handler = error_handler
        self.message_queue = message_queue

        self.create_widgets()
        self.update_file_list()
        self._finalize_init(
            preferred_width=680,
            preferred_height=400,
            min_width=560,
            min_height=320,
            modal=True,
        )

    def create_widgets(self) -> None:
        """Create and arrange all widgets under the shared content parent."""
        self.main_frame = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
        )
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.path_entry = PathEntryBar(
            self.main_frame,
            self.current_path,
            self.update_file_list,
            theme_manager=self._theme_manager,
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        self.file_list = FileListBox(
            self.main_frame,
            self.on_item_double_click,
            theme_manager=self._theme_manager,
        )
        self.file_list.grid(row=1, column=0, padx=12, pady=8, sticky="nsew")

        self.action_buttons = FileManagerButtonBar(
            self.main_frame,
            self.change_directory,
            self.create_folder,
            self.destroy,
            theme_manager=self._theme_manager,
        )
        self.action_buttons.grid(row=2, column=0, padx=12, pady=(8, 12), sticky="ew")

    def update_file_list(self) -> None:
        """Update the file list with current directory contents."""
        try:
            self.current_path = os.path.expanduser(self.path_entry.get_path())
            self.file_list.update_items(self.current_path)
        except OSError as error:
            logger.error(f"Error accessing directory: {error}")
            if self.show_status:
                self.show_status("Error: Unable to access the specified directory.")

    def on_item_double_click(self, _event: Any) -> None:
        """Handle double-click on file/directory."""
        if not (item := self.file_list.get_selected_item()):
            return

        if item == "..":
            new_path = os.path.dirname(self.current_path)
        else:
            if item.startswith(("📁 ", "📄 ")):
                item = item[2:]
            new_path = os.path.join(self.current_path, item)

        if os.path.isdir(new_path):
            self.current_path = new_path
            self.path_entry.set_path(new_path)
            self.update_file_list()

    def change_directory(self) -> None:
        """Change the download directory."""
        if os.path.exists(self.current_path) and os.path.isdir(self.current_path):
            self.on_directory_change(self.current_path)
            logger.info(f"Download directory changed to: {self.current_path}")
            if self.show_status:
                self.show_status(f"Download directory changed to: {self.current_path}")
            self.destroy()
            return

        error_msg = "Please select a valid directory."
        if self.error_handler:
            self.error_handler.show_error("File Manager Error", error_msg)
        elif self.message_queue:
            self.message_queue.add_message(
                Message(
                    text=error_msg,
                    level=MessageLevel.ERROR,
                    title="File Manager Error",
                )
            )
        elif self.show_status:
            self.show_status(error_msg)

    def create_folder(self) -> None:
        """Create a new folder."""
        dialog = CenteredInputDialog(
            self,
            title="Create Folder",
            text="Enter folder name:",
        )
        if folder_name := dialog.get_input():
            new_folder_path = os.path.join(self.current_path, folder_name)
            try:
                os.mkdir(new_folder_path)
                logger.info(f"Created new folder: {new_folder_path}")
                self.update_file_list()
            except OSError as error:
                logger.error(f"Error creating folder: {error}")
                error_msg = f"Unable to create folder: {error!s}"
                if self.error_handler:
                    self.error_handler.show_error("File Manager Error", error_msg)
                elif self.message_queue:
                    self.message_queue.add_message(
                        Message(
                            text=error_msg,
                            level=MessageLevel.ERROR,
                            title="File Manager Error",
                        )
                    )
                elif self.show_status:
                    self.show_status(f"Error: {error_msg}")
