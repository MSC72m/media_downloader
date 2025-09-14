import os
import sys
import logging
from typing import List, Optional
from pathlib import Path
import threading
import customtkinter as ctk
from tkinter import messagebox

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import existing UI components (reusing them)
from src.ui.components.url_entry import URLEntryFrame
from src.ui.components.options_bar import OptionsBar
from src.ui.components.download_list import DownloadListView
from src.ui.components.status_bar import StatusBar
from src.ui.dialogs.file_manager_dialog import FileManagerDialog
from src.ui.components.main_action_buttons import ActionButtonBar
from src.ui.dialogs.network_status_dialog import NetworkStatusDialog

# Import existing models
from src.models import (
    DownloadItem, UIState, MessageLevel, InstagramAuthStatus, ServiceType
)

# Import existing controllers (reusing them)
from src.controllers.download_manager import DownloadManager
from src.controllers.auth_manager import AuthenticationManager

# Import existing utils (reusing them)
from src.utils import (
    MessageQueue, Message,
    check_internet_connection,
    check_site_connection,
    check_all_services,
    get_problem_services
)

# Import new architecture
from src.abstractions import IApplicationController
from src.handlers import (
    ApplicationController, DefaultUIEventHandler,
    DownloadHandler, AuthenticationHandler,
    ServiceDetector, NetworkChecker
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MediaDownloaderRefactored(ctk.CTk):
    """Refactored main application using clean architecture."""

    def __init__(self):
        super().__init__()

        # Initialize state
        self.ui_state = UIState()
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.message_queue = MessageQueue(self)
        self.instagram_auth_status = InstagramAuthStatus.FAILED

        # Configure window
        self.title("Media Downloader")
        self.geometry("1000x700")

        # Initialize new architecture (reusing existing controllers)
        self._initialize_architecture()

        # Create UI (reusing existing components)
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.init_components()
        self.setup_grid()
        self.create_widgets()
        self.setup_menu()

        # Bind close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("MediaDownloader (Refactored) initialized")

        # Check internet connectivity
        self.check_internet_connectivity()

    def _initialize_architecture(self):
        """Initialize the new architecture with existing controllers."""
        # Reuse existing controllers
        download_manager = DownloadManager()
        auth_manager = AuthenticationManager()

        # Set up auth manager reference
        download_manager.auth_manager = auth_manager

        # Create new handlers that delegate to existing controllers
        download_handler = DownloadHandler(download_manager)
        auth_handler = AuthenticationHandler(auth_manager)
        service_detector = ServiceDetector()
        network_checker = NetworkChecker()

        # Create UI event handler
        ui_event_handler = DefaultUIEventHandler(
            download_handler=download_handler,
            auth_handler=auth_handler,
            service_detector=service_detector,
            network_checker=network_checker,
            app_controller=None,  # Will set after creating app controller
            message_callback=self._show_message,
            error_callback=self._show_error
        )

        # Create main application controller
        self.app_controller = ApplicationController(
            download_handler=download_handler,
            auth_handler=auth_handler,
            service_detector=service_detector,
            network_checker=network_checker,
            ui_event_handler=ui_event_handler
        )

        # Update the UI event handler with the app controller reference
        ui_event_handler._app_controller = self.app_controller

        # Initialize the architecture
        self.app_controller.initialize()

        # Store references for direct use
        self.download_handler = download_handler
        self.auth_handler = auth_handler
        self.service_detector = service_detector
        self.network_checker = network_checker

    def init_components(self):
        """Initialize all UI components (reusing existing components)."""
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Media Downloader",
            font=("Roboto", 32, "bold")
        )

        # URL Entry - route to new architecture
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

        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

    def create_widgets(self):
        """Create and arrange all UI widgets."""
        self.title_label.grid(row=0, column=0, pady=(0, 20))
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.options_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.download_list.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        self.action_buttons.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.status_bar.grid(row=5, column=0, sticky="ew")

    def setup_menu(self):
        """Set up application menu."""
        from tkinter import Menu

        menubar = Menu(self)
        self.configure(menu=menubar)

        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Network Status", command=self.show_network_status)
        menubar.add_cascade(label="Tools", menu=tools_menu)

    def show_network_status(self):
        """Show network status dialog."""
        NetworkStatusDialog(self)

    def check_internet_connectivity(self):
        """Check internet connectivity at startup."""
        self.status_bar.show_message("Checking network connectivity...")

        def check_worker():
            internet_connected, error_msg = self.network_checker.check_internet_connection()
            service_results = check_all_services()
            problem_services = [
                service for service, (connected, _) in service_results.items()
                if not connected
            ]

            self.after(0, lambda: self.handle_connectivity_check(
                internet_connected, error_msg, problem_services
            ))

        threading.Thread(target=check_worker, daemon=True).start()

    def handle_connectivity_check(self, internet_connected: bool, error_msg: str, problem_services: List[str]):
        """Handle the results of the connectivity check."""
        if not internet_connected:
            messagebox.showwarning(
                "Network Connectivity Issue",
                f"There are network connectivity issues:\n\n{error_msg}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            self.status_bar.show_warning("Network connectivity issues detected")
        elif problem_services:
            problem_list = ", ".join(problem_services)
            messagebox.showwarning(
                "Service Connection Issues",
                f"Cannot connect to the following services: {problem_list}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            self.status_bar.show_warning(f"Connection issues with: {problem_list}")
        else:
            self.status_bar.show_message("Ready - All services connected")

    # Event handlers - route to new architecture
    def handle_add_url(self, url: str, name: str):
        """Handle adding new download item."""
        self.app_controller.get_ui_event_handler().handle_url_add(url, name)
        # Update UI after adding
        self._refresh_download_list()
        self._update_button_states()

    def handle_remove(self):
        """Handle removing selected items."""
        self.app_controller.get_ui_event_handler().handle_remove_selected()
        # Update UI after removal
        self._refresh_download_list()

    def handle_clear(self):
        """Handle clearing all items."""
        self.app_controller.get_ui_event_handler().handle_clear_all()
        # Update UI after clearing
        self._refresh_download_list()

    def handle_download(self):
        """Handle starting downloads."""
        self.app_controller.get_ui_event_handler().handle_download_start()

    def handle_selection_change(self, selected_indices: List[int]):
        """Handle download item selection changes."""
        self.app_controller.get_ui_event_handler().handle_selection_change(selected_indices)
        self._update_button_states()

    def handle_instagram_login(self):
        """Handle Instagram login process."""
        try:
            self.instagram_auth_status = InstagramAuthStatus.LOGGING_IN
            self.options_bar.set_instagram_status(self.instagram_auth_status)

            # Check connectivity first
            connected, error_msg = self.network_checker.check_service_connection(ServiceType.INSTAGRAM)
            if not connected:
                self.instagram_auth_status = InstagramAuthStatus.FAILED
                self.options_bar.set_instagram_status(self.instagram_auth_status)
                self.status_bar.show_error(f"Cannot connect to Instagram: {error_msg}")
                return

            def on_auth_complete(success: bool):
                if success:
                    self.instagram_auth_status = InstagramAuthStatus.AUTHENTICATED
                    self.status_bar.show_message("Instagram login successful")
                else:
                    self.instagram_auth_status = InstagramAuthStatus.FAILED
                    self.status_bar.show_error("Instagram login failed")

                self.options_bar.set_instagram_status(self.instagram_auth_status)

            self.app_controller.get_auth_handler().authenticate_instagram(
                parent_window=self,
                callback=on_auth_complete
            )
        except Exception as e:
            logger.error(f"Error during Instagram login: {str(e)}")
            self.instagram_auth_status = InstagramAuthStatus.FAILED
            self.options_bar.set_instagram_status(self.instagram_auth_status)
            self.status_bar.show_error("Instagram login error")

    def handle_quality_change(self, quality: str):
        """Handle video quality change."""
        self.app_controller.get_ui_event_handler().handle_option_change('quality', quality)

    def handle_option_change(self, option: str, value: bool):
        """Handle download option changes."""
        self.app_controller.get_ui_event_handler().handle_option_change(option, value)

    def handle_manage_files(self):
        """Handle opening file manager dialog."""
        try:
            dialog = FileManagerDialog(
                self,
                self.downloads_folder,
                self.on_directory_change,
                self.status_bar.show_message
            )
            self.wait_window(dialog)
        except Exception as e:
            logger.error(f"Error opening file manager: {str(e)}")
            self.status_bar.show_error("Error opening file manager")

    def on_directory_change(self, new_directory: str):
        """Handle directory change from file manager."""
        self.downloads_folder = new_directory
        self.app_controller.ui_state.download_directory = new_directory
        logger.info(f"Download directory changed to: {new_directory}")

    # Helper methods for UI updates
    def _refresh_download_list(self):
        """Refresh the download list UI."""
        items = self.download_handler.get_items()
        self.download_list.refresh_items(items)

    def _update_button_states(self):
        """Update button states based on current application state."""
        has_selection = bool(self.app_controller.ui_state.selected_indices)
        has_items = self.download_handler.has_items()
        is_downloading = self.download_handler.has_active_downloads()

        self.app_controller.update_button_states(has_selection, has_items, is_downloading)
        self.action_buttons.update_states(self.app_controller.ui_state.button_states)

    def _show_message(self, message: str, level: str = "info"):
        """Show a message using the existing message queue."""
        level_map = {
            "info": MessageLevel.INFO,
            "success": MessageLevel.SUCCESS,
            "warning": MessageLevel.WARNING,
            "error": MessageLevel.ERROR
        }

        self.message_queue.add_message(Message(
            level=level_map.get(level, MessageLevel.INFO),
            text=message
        ))

    def _show_error(self, message: str):
        """Show an error message."""
        self._show_message(message, "error")

    def on_closing(self):
        """Handle application closing."""
        try:
            self.app_controller.cleanup()
            self.destroy()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            self.destroy()


if __name__ == "__main__":
    app = MediaDownloaderRefactored()
    app.mainloop()
