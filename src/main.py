import os
import sys
import logging
from typing import List, Optional, Dict
from pathlib import Path
from urllib.parse import urlparse
import threading
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
from src.ui.dialogs.network_status_dialog import NetworkStatusDialog

# Import models
from src.models.pydantic_models import DownloadItem, UIState, UIMessage
from src.models.enums import MessageLevel
from src.models.enums.status import NetworkStatus, InstagramAuthStatus
from src.models.pydantic_models.options import DownloadOptions, VideoQuality

# Import managers/controllers
from src.controllers.download_manager import DownloadManager
from src.controllers.auth_manager import AuthenticationManager

# Import utils
from src.utils.message_queue import MessageQueue, Message
from src.utils.common import (
    check_internet_connection, 
    check_site_connection, 
    check_all_services,
    get_problem_services,
    is_service_connected
)

# Configure logging
logging.basicConfig(
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
        
        # Instagram auth status
        self.instagram_auth_status = InstagramAuthStatus.FAILED

        # Initialize state
        self.ui_state = UIState()
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.message_queue = MessageQueue(self)

        # Initialize controllers
        self.auth_manager = AuthenticationManager()
        self.download_manager = DownloadManager()
        self.download_manager.auth_manager = self.auth_manager

        # Configure window
        self.title("Media Downloader")
        self.geometry("1000x700")

        # Create main frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")

        # Initialize UI components
        self.init_components()
        self.setup_grid()
        self.create_widgets()
        self.setup_menu()

        # Bind close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("MediaDownloader initialized")
        
        # Check internet connectivity immediately during initialization
        self.check_internet_connectivity()

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
    
    def setup_menu(self):
        """Set up application menu."""
        from tkinter import Menu
        
        menubar = Menu(self)
        self.configure(menu=menubar)
        
        # Tools menu
        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Network Status", command=self.show_network_status)
        menubar.add_cascade(label="Tools", menu=tools_menu)
    
    def show_network_status(self):
        """Show network status dialog."""
        NetworkStatusDialog(self)
        
    def check_internet_connectivity(self):
        """Check internet connectivity at startup."""
        # Show checking message in status bar
        self.status_bar.show_message("Checking network connectivity...")
        
        # Run check in background thread
        def check_worker():
            # First check if internet is connected
            internet_connected, error_msg = check_internet_connection()
            
            # Check individual services
            service_results = check_all_services()
            
            # Get services with problems
            problem_services = [
                service for service, (connected, _) in service_results.items() 
                if not connected
            ]
            
            # Update UI from main thread
            self.after(0, lambda: self.handle_connectivity_check(
                internet_connected, error_msg, problem_services
            ))
        
        threading.Thread(target=check_worker, daemon=True).start()
    
    def handle_connectivity_check(self, internet_connected: bool, error_msg: str, problem_services: List[str]):
        """Handle the results of the connectivity check."""
        if not internet_connected:
            # Show a warning message box immediately at startup if connectivity issues
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

    def handle_add_url(self, url: str, name: str):
        """Handle adding new download item."""
        try:
            # Validate URL
            if not url.startswith('http'):
                raise ValueError("Invalid URL format. URL must start with http:// or https://")

            # Check if URL is from supported platform
            domain = urlparse(url).netloc.lower()
            supported = False
            site_name = None
            
            for platform in ['youtube.com', 'youtu.be']:
                if platform in domain:
                    supported = True
                    site_name = "YouTube"
                    break
                    
            for platform in ['twitter.com', 'x.com']:
                if platform in domain:
                    supported = True
                    site_name = "Twitter"
                    break
                    
            for platform in ['instagram.com']:
                if platform in domain:
                    supported = True
                    site_name = "Instagram"
                    break
                    
            for platform in ['pinterest.com', 'pin.it']:
                if platform in domain:
                    supported = True
                    site_name = "Pinterest"
                    break

            if not supported:
                raise ValueError(
                    "Unsupported platform. Currently supported: YouTube, Twitter, Instagram, and Pinterest")
            
            # Check connectivity to the site
            if site_name:
                connected, error_msg = check_site_connection(site_name)
                if not connected:
                    raise ValueError(f"Cannot connect to {site_name}: {error_msg}")

            # Create and add item
            item = DownloadItem(name=name, url=url)
            self.download_manager.add_item(item)
            self.download_list.refresh_items(self.download_manager.items)
            self.message_queue.add_message(Message(
                level=MessageLevel.SUCCESS,
                text=f"Added: {name}"
            ))
            logger.info(f"Added download item: {name} - {url}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error adding URL: {error_msg}")
            self.message_queue.add_message(Message(
                level=MessageLevel.ERROR,
                text=f"Error adding URL: {error_msg}"
            ))

    def handle_instagram_login(self):
        """Handle Instagram login process."""
        try:
            # Update status immediately to indicate we're trying to log in
            self.instagram_auth_status = InstagramAuthStatus.LOGGING_IN
            self.options_bar.set_instagram_status(self.instagram_auth_status)
            
            # Check connectivity to Instagram first
            connected, error_msg = check_site_connection("Instagram")
            if not connected:
                self.instagram_auth_status = InstagramAuthStatus.FAILED
                self.options_bar.set_instagram_status(self.instagram_auth_status)
                self.status_bar.show_error(f"Cannot connect to Instagram: {error_msg}")
                messagebox.showerror(
                    "Instagram Connection Error",
                    f"Cannot connect to Instagram: {error_msg}\n\n"
                    "Please check your internet connection and try again."
                )
                return
                
            def on_auth_complete(success: bool):
                if success:
                    self.instagram_auth_status = InstagramAuthStatus.AUTHENTICATED
                    self.options_bar.set_instagram_status(self.instagram_auth_status)
                    self.status_bar.show_message("Instagram login successful")
                else:
                    self.instagram_auth_status = InstagramAuthStatus.FAILED
                    self.options_bar.set_instagram_status(self.instagram_auth_status)
                    self.status_bar.show_error("Instagram login failed")
                    messagebox.showerror(
                        "Instagram Login Failed",
                        "Login to Instagram failed. Please check your username and password.\n\n"
                        "If you're sure your credentials are correct, Instagram might be temporarily "
                        "limiting login attempts from your IP address."
                    )

            self.auth_manager.authenticate_instagram(
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
        self.download_manager.quality = quality

    def handle_option_change(self, option: str, value: bool):
        """Handle download option changes."""
        self.download_manager.set_option(option, value)

    def handle_selection_change(self, selected_indices: List[int]):
        """Handle download item selection changes."""
        self.ui_state.selected_indices = selected_indices
        self.ui_state.update_button_states(
            has_selection=bool(selected_indices),
            has_items=self.download_manager.has_items(),
            is_downloading=self.download_manager.has_active_downloads()
        )
        self.action_buttons.update_states(self.ui_state.button_states)

    def handle_remove(self):
        """Handle removing selected items."""
        try:
            if not self.ui_state.selected_indices:
                self.status_bar.show_message("Please select items to remove")
                return

            self.download_manager.remove_items(self.ui_state.selected_indices)
            self.download_list.refresh_items(self.download_manager.items)
            self.status_bar.show_message("Selected items removed")
        except Exception as e:
            logger.error(f"Error removing items: {str(e)}")
            self.status_bar.show_error("Error removing items")

    def handle_clear(self):
        """Handle clearing all items."""
        try:
            if not self.download_manager.has_items():
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
            if not self.download_manager.has_items():
                self.message_queue.add_message(Message(
                    level=MessageLevel.INFO,
                    text="Please add items to download"
                ))
                return

            # Check if Instagram items exist and we're authenticated
            has_instagram = any('instagram.com' in item.url for item in self.download_manager.items)
            if has_instagram and self.instagram_auth_status != InstagramAuthStatus.AUTHENTICATED:
                self.message_queue.add_message(Message(
                    level=MessageLevel.ERROR,
                    text="Please log in to Instagram first to download Instagram content"
                ))
                return
            
            # Check internet connectivity before starting downloads
            problem_services = get_problem_services()
            if problem_services:
                problem_list = ", ".join(problem_services)
                self.message_queue.add_message(Message(
                    level=MessageLevel.ERROR,
                    text=f"Network connectivity issue with: {problem_list}"
                ))
                messagebox.showerror(
                    "Network Error",
                    f"Cannot start downloads due to connection issues with: {problem_list}\n\n"
                    "Please check your internet connection and try again."
                )
                return

            def progress_callback(item: DownloadItem, progress: float):
                self.download_list.update_item_progress(item, progress)
                self.ui_state.update_button_states(
                    has_selection=bool(self.ui_state.selected_indices),
                    has_items=self.download_manager.has_items(),
                    is_downloading=True
                )
                self.action_buttons.update_states(self.ui_state.button_states)

            def completion_callback(success: bool, error: Optional[str] = None):
                if success:
                    self.status_bar.show_message("Downloads completed")
                else:
                    self.status_bar.show_error(f"Download error: {error}")
                
                # Make sure to update button states on completion
                self.ui_state.update_button_states(
                    has_selection=bool(self.ui_state.selected_indices),
                    has_items=self.download_manager.has_items(),
                    is_downloading=self.download_manager.has_active_downloads()
                )
                self.action_buttons.update_states(self.ui_state.button_states)

            self.download_manager.start_downloads(
                self.downloads_folder,
                progress_callback,
                completion_callback
            )
        except Exception as e:
            logger.error(f"Error starting downloads: {str(e)}")
            self.status_bar.show_error("Error starting downloads")

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
        logger.info(f"Download directory changed to: {new_directory}")

    def on_closing(self):
        """Handle application closing."""
        try:
            # Clean up resources
            self.download_manager.cleanup()
            self.auth_manager.cleanup()
            self.destroy()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            self.destroy()


if __name__ == "__main__":
    app = MediaDownloader()
    app.mainloop()
