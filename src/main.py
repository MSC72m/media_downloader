import os
import sys
import logging
from typing import List, Dict, Callable, Optional
import queue
import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import UI components
from src.ui.components.url_entry import URLEntryFrame
from src.ui.components.options_bar import OptionsBar
from src.ui.components.download_list import DownloadListView
from src.ui.components.action_buttons import ActionButtonBar
from src.ui.components.status_bar import StatusBar
from src.ui.dialogs.file_manager_dialog import FileManagerDialog
from src.ui.components.main_action_buttons import ActionButtonBar

#utils
from src.utils.message_queue import MessageQueue, Message, MessageType

# Import managers/controllers
from src.controllers.download_manager import DownloadManager
from src.controllers.auth_manager import AuthenticationManager
from src.models.download_item import DownloadItem

# Configure logging
logging.basicConfig(
    filename='media_downloader.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set theme
ctk.set_appearance_mode("dark")
SUPPORTED_PLATFORMS = ['YouTube', 'Twitter', 'Instagram', 'Pinterest']
ctk.set_default_color_theme("blue")

class MediaDownloader(ctk.CTk):
    """Main application window for Media Downloader."""

    def __init__(self):
        super().__init__()

        # Initialize managers first
        self.auth_manager = AuthenticationManager()  # Create auth manager first
        self.download_manager = DownloadManager()    # Create download manager
        self.download_manager.set_auth_manager(self.auth_manager)  # Connect them
        # Initialize state
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.message_queue = MessageQueue(self)
        # Configure window
        self.title("Media Downloader")
        self.geometry("1000x700")

        # Create main frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Initialize UI components
        self.init_components()
        self.setup_grid()
        self.create_widgets()

        # Bind close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("MediaDownloader initialized")

    def init_components(self):
        """Initialize all UI components."""
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Media Downloader",
            font=("Roboto", 32, "bold")
        )

        # URL Entry
        self.url_entry = URLEntryFrame(
            self.main_frame,
            on_add=self.handle_add_url
        )

        # Options Bar
        self.options_bar = OptionsBar(
            self.main_frame,
            on_instagram_login=self.handle_instagram_login,
            on_quality_change=self.handle_quality_change,
            on_option_change=self.handle_option_change
        )

        # Download List
        self.download_list = DownloadListView(
            self.main_frame,
            on_selection_change=self.handle_selection_change
        )

        # Action Buttons
        self.action_buttons = ActionButtonBar(
            self.main_frame,
            on_remove=self.handle_remove,
            on_clear=self.handle_clear,
            on_download=self.handle_download,
            on_manage_files=self.handle_manage_files
        )

        # Status Bar
        self.status_bar = StatusBar(self.main_frame)

    def setup_grid(self):
        """Configure the main grid layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main container frame
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

    def create_widgets(self):
        """Create and arrange all UI widgets."""
        # Title
        self.title_label.grid(row=0, column=0, pady=(0, 20))

        # URL Entry
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Options Bar
        self.options_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # Download List
        self.download_list.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        # Action Buttons
        self.action_buttons.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        # Status Bar
        self.status_bar.grid(row=5, column=0, sticky="ew")


    # Inside the MediaDownloader class, update the handle_add_url method:
    def handle_add_url(self, url: str, name: str):  # Update signature to accept both arguments
        """Handle adding new download item."""
        try:
            item = DownloadItem(name=name, url=url)
            self.download_manager.add_item(item)
            self.download_list.refresh_items(self.download_manager.get_items())
            self.status_bar.show_message(f"Added: {name}")
            logger.info(f"Added download item: {name} - {url}")
        except Exception as e:
            logger.error(f"Error adding URL: {str(e)}")
            self.status_bar.show_error(f"Error adding URL: {str(e)}")

    def handle_instagram_login(self):
        """Handle Instagram login process."""
        try:
            def on_auth_complete(success: bool):
                if success:
                    self.options_bar.set_instagram_authenticated(True)
                    self.status_bar.show_message("Instagram login successful")
                else:
                    self.options_bar.set_instagram_authenticated(False)
                    self.status_bar.show_error("Instagram login failed")

            self.auth_manager.authenticate_instagram(
                parent_window=self,
                callback=on_auth_complete
            )
        except Exception as e:
            logger.error(f"Error during Instagram login: {str(e)}")
            self.status_bar.show_error("Instagram login error")
            self.options_bar.set_instagram_authenticated(False)

    def handle_quality_change(self, quality: str):
        """Handle video quality change."""
        self.download_manager.set_quality(quality)

    def handle_option_change(self, option: str, value: bool):
        """Handle download option changes."""
        self.download_manager.set_option(option, value)

    def handle_selection_change(self, selected_indices: List[int]):
        """Handle download item selection changes."""
        self.action_buttons.update_button_states(
            has_selection=bool(selected_indices),
            has_items=bool(self.download_manager.get_items())
        )

    def handle_remove(self):
        """Handle removing selected items."""
        try:
            selected_indices = self.download_list.get_selected_indices()
            if not selected_indices:
                self.status_bar.show_message("Please select items to remove")
                return

            self.download_manager.remove_items(selected_indices)
            self.download_list.refresh_items(self.download_manager.get_items())
            self.status_bar.show_message("Selected items removed")
        except Exception as e:
            logger.error(f"Error removing items: {str(e)}")
            self.status_bar.show_error("Error removing items")

    def handle_clear(self):
        """Handle clearing all items."""
        try:
            if not self.download_manager.get_items():
                self.status_bar.show_message("No items to clear")
                return

            self.download_manager.clear_items()
            self.download_list.refresh_items([])
            self.status_bar.show_message("All items cleared")
        except Exception as e:
            logger.error(f"Error clearing items: {str(e)}")
            self.status_bar.show_error("Error clearing items")

    def handle_download(self):
        """Handle starting downloads."""
        try:
            if not self.download_manager.get_items():
                self.status_bar.show_message("Please add items to download")
                return

            self.action_buttons.set_button_state("download", "disabled")

            def progress_callback(item: DownloadItem, progress: float):
                self.after(0, lambda: self._update_progress(item, progress))

            def completion_callback(success: bool, error: Optional[str] = None):
                self.after(0, lambda: self._handle_download_completion(success, error))

            self.download_manager.start_downloads(
                self.downloads_folder,
                progress_callback,
                completion_callback
            )
        except Exception as e:
            logger.error(f"Error starting downloads: {str(e)}")
            self.message_queue.add_message(Message(
                type=MessageType.ERROR,
                text=f"Error starting downloads: {str(e)}"
            ))
            self.action_buttons.set_button_state("download", "normal")

    def _update_progress(self, item: DownloadItem, progress: float):
        """Update UI with download progress."""
        self.download_list.update_item_progress(item, progress)
        self.status_bar.update_progress(progress)

    def _handle_download_completion(self, success: bool, error: Optional[str] = None):
        """Handle download completion."""
        self.action_buttons.set_button_state("download", "normal")
        if success:
            self.message_queue.add_message(Message(
                type=MessageType.SUCCESS,
                text="Downloads completed successfully"
            ))
        else:
            self.message_queue.add_message(Message(
                type=MessageType.ERROR,
                text=f"Download failed: {error}"
            ))
        self.download_list.refresh_items(self.download_manager.get_items())

    def handle_manage_files(self):
        """Handle opening file manager dialog."""
        try:
            def on_directory_change(new_path: str):
                self.downloads_folder = new_path
                self.status_bar.show_message(f"Download directory changed: {new_path}")

            FileManagerDialog(
                self,
                self.downloads_folder,
                on_directory_change,
                self.status_bar.show_message
            )
        except Exception as e:
            logger.error(f"Error managing files: {str(e)}")
            self.status_bar.show_error("Error opening file manager")

    def on_closing(self):
        """Handle application closing."""
        try:
            if self.download_manager.has_active_downloads():
                if not messagebox.askyesno(
                    "Active Downloads",
                    "There are active downloads. Are you sure you want to exit?"
                ):
                    return

            self.download_manager.cleanup()
            self.auth_manager.cleanup()
            self.quit()
            logger.info("Application closed cleanly")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            self.quit()

def main():
    """Application entry point."""
    try:
        app = MediaDownloader()
        logger.info("Application started")
        app.mainloop()
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}")
        messagebox.showerror(
            "Critical Error",
            "An unexpected error occurred. Please check the log file for details."
        )
    finally:
        logging.shutdown()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
