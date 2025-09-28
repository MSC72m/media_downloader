import customtkinter as ctk
from tkinter import messagebox
from typing import List, Optional, Any, Callable, Dict
from .interfaces.event_handlers import (
    URLDetectionHandler, DownloadManagementHandler, UIUpdateHandler,
    AuthenticationHandler, FileManagementHandler, ConfigurationHandler,
    NetworkStatusHandler, YouTubeSpecificHandler
)
from .models import Download, DownloadStatus
from ..services.youtube.metadata_service import YouTubeMetadataService
from ..ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog
from ..ui.dialogs.browser_cookie_dialog import BrowserCookieDialog
from ..ui.dialogs.file_manager_dialog import FileManagerDialog
from ..ui.dialogs.network_status_dialog import NetworkStatusDialog
from .link_detection import LinkDetector


class EventCoordinator(
    URLDetectionHandler,
    DownloadManagementHandler,
    UIUpdateHandler,
    AuthenticationHandler,
    FileManagementHandler,
    ConfigurationHandler,
    NetworkStatusHandler,
    YouTubeSpecificHandler
):
    """Coordinates events between UI and business logic."""

    def __init__(self, root_window: ctk.CTk, container):
        self.root = root_window
        self.container = container
        self.link_detector = LinkDetector()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup internal handlers and services."""
        # Get services from container
        self.download_list = self.container.get('download_list')
        self.status_bar = self.container.get('status_bar')
        self.action_buttons = self.container.get('action_buttons')
        self.url_entry = self.container.get('url_entry')
        self.cookie_handler = self.container.get('cookie_handler')
        self.auth_handler = self.container.get('auth_handler')
        self.service_controller = self.container.get('service_controller')

    
    # URLDetectionHandler implementation
    def detect_url_type(self, url: str) -> Optional[str]:
        """Detect the type of URL - delegated to link detection system."""
        # This is handled by the new link detection system
        return None

    def handle_detected_url(self, url: str, context: Any) -> bool:
        """Handle a detected URL - delegated to link detection system."""
        # This is handled by the new link detection system
        return False

    # DownloadManagementHandler implementation
    def add_download(self, download: Download) -> bool:
        """Add a download to the system - delegated to dialog system."""
        # Downloads are added through the dialog system
        self.update_status(f"Download added: {download.name}")
        return True

    def remove_downloads(self, indices: List[int]) -> bool:
        """Remove downloads by indices."""
        try:
            if self.download_list:
                self.download_list.remove_downloads(indices)
                self.update_status("Selected items removed")
                return True
        except Exception as e:
            self.show_error("Remove Error", f"Failed to remove downloads: {str(e)}")
        return False

    def clear_downloads(self) -> bool:
        """Clear all downloads."""
        try:
            if self.download_list:
                self.download_list.clear_downloads()
                self.update_status("All items cleared")
                return True
        except Exception as e:
            self.show_error("Clear Error", f"Failed to clear downloads: {str(e)}")
        return False

    def start_downloads(self) -> bool:
        """Start all pending downloads."""
        try:
            if not self.download_list or not self.download_list.has_items():
                self.update_status("Please add items to download")
                return False

            if self.service_controller:
                downloads = self.download_list.get_downloads()

                # Define callbacks for UI feedback
                def on_progress(download, progress):
                    self.update_progress(download, progress)

                def on_completion(success, message):
                    # Re-enable buttons
                    if self.action_buttons:
                        self.action_buttons.set_enabled(True)

                    # Show completion message
                    if success:
                        self.update_status("Downloads completed successfully!")
                    else:
                        self.update_status(f"Downloads failed: {message}", is_error=True)

                # Disable buttons during download
                if self.action_buttons:
                    self.action_buttons.set_enabled(False)

                # Start downloads with callbacks
                self.service_controller.start_downloads(downloads, on_progress, on_completion)
                return True

        except Exception as e:
            self.show_error("Download Error", f"Failed to start downloads: {str(e)}")
            if self.action_buttons:
                self.action_buttons.set_enabled(True)
        return False

    # UIUpdateHandler implementation
    def update_status(self, message: str, is_error: bool = False) -> None:
        """Update status bar message."""
        if self.status_bar:
            if is_error:
                self.status_bar.show_error(message)
            else:
                self.status_bar.show_message(message)

    def update_progress(self, download: Download, progress: float) -> None:
        """Update download progress."""
        if self.status_bar:
            self.status_bar.show_message(f"Downloading {download.name}: {progress:.1f}%")

    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        """Update button enabled/disabled states."""
        if self.action_buttons:
            self.action_buttons.update_button_states(has_selection, has_items)

    def show_error(self, title: str, message: str) -> None:
        """Show error dialog."""
        messagebox.showerror(title, message)

    # AuthenticationHandler implementation
    def authenticate_instagram(self, parent_window: Any = None, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Handle Instagram authentication."""
        if self.auth_handler:
            self.auth_handler.authenticate_instagram(parent_window or self.root, callback or (lambda success: None))

    def handle_cookie_detection(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection."""
        if self.cookie_handler:
            success = self.cookie_handler.set_cookie_file(cookie_path)
            if success:
                self.update_status(f"Cookies loaded from {browser_type}")
            else:
                self.update_status("Failed to load cookies", is_error=True)

    # FileManagementHandler implementation
    def show_file_manager(self) -> None:
        """Show file manager dialog."""
        FileManagerDialog(self.root)

    def browse_files(self, file_types: List[str]) -> Optional[str]:
        """Browse for files."""
        from tkinter import filedialog
        file_types_formatted = [(ft, f"*.{ft}") for ft in file_types]
        file_types_formatted.append(("All files", "*.*"))
        return filedialog.askopenfilename(filetypes=file_types_formatted)

    # ConfigurationHandler implementation
    def get_download_directory(self) -> str:
        """Get download directory."""
        ui_state = self.container.get('ui_state')
        return getattr(ui_state, 'download_directory', '~/Downloads') if ui_state else '~/Downloads'

    def set_download_directory(self, directory: str) -> bool:
        """Set download directory."""
        try:
            ui_state = self.container.get('ui_state')
            if ui_state:
                ui_state.download_directory = directory
                return True
        except Exception as e:
            self.show_error("Configuration Error", f"Failed to set download directory: {str(e)}")
        return False

    def save_configuration(self) -> bool:
        """Save current configuration."""
        # Implementation would save to config file
        return True

    # NetworkStatusHandler implementation
    def check_connectivity(self) -> bool:
        """Check internet connectivity."""
        from .network import check_internet_connection
        return check_internet_connection()

    def check_service_status(self, services: List[str]) -> Dict[str, bool]:
        """Check status of specific services."""
        from .network import check_all_services
        results = check_all_services()
        return {service: results.get(service, (False, ""))[0] for service in services}

    def show_network_status(self) -> None:
        """Show network status dialog."""
        NetworkStatusDialog(self.root)

    # YouTubeSpecificHandler implementation
    def handle_youtube_download(self, url: str, name: str, options: dict) -> None:
        """Handle YouTube download completion."""
        try:
            # Create download with YouTube-specific options
            from .models import ServiceType
            download = Download(
                name=name,
                url=url,
                service_type=ServiceType.YOUTUBE,
                quality=options.get('quality', '720p'),
                format=options.get('format', 'video'),
                audio_only=options.get('audio_only', False),
                video_only=options.get('video_only', False),
                download_playlist=options.get('download_playlist', False),
                download_subtitles=options.get('download_subtitles', False),
                selected_subtitles=options.get('selected_subtitles'),
                download_thumbnail=options.get('download_thumbnail', True),
                embed_metadata=options.get('embed_metadata', True),
                cookie_path=options.get('cookie_path'),
                selected_browser=options.get('selected_browser'),
                speed_limit=options.get('speed_limit'),
                retries=options.get('retries', 3),
                concurrent_downloads=options.get('concurrent_downloads', 1)
            )

            # Add to download list
            if self.add_download(download):
                # Reset URL entry field
                if self.url_entry:
                    try:
                        if hasattr(self.url_entry, 'url_entry'):
                            self.url_entry.url_entry.delete(0, 'end')
                            self.url_entry.url_entry.insert(0, '')
                        else:
                            self.url_entry.delete(0, 'end')
                            self.url_entry.insert(0, '')
                    except Exception as e:
                        print(f"Error resetting URL entry: {e}")

                # Create descriptive message
                config_desc = []
                if options.get('format') == 'audio':
                    config_desc.append("Audio")
                elif options.get('format') == 'video_only':
                    config_desc.append("Video Only")
                if options.get('download_playlist'):
                    config_desc.append("Playlist")
                if options.get('quality') and options.get('quality') != '720p':
                    config_desc.append(f"{options.get('quality')}")
                if options.get('selected_browser'):
                    config_desc.append(f"{options.get('selected_browser')} cookies")

                desc = f"YouTube {config_desc[0]}" if config_desc else "YouTube video"
                self.update_status(f"{desc} added: {name}")

        except Exception as e:
            self.show_error("YouTube Download Error", f"Failed to process YouTube download: {str(e)}")

    def show_youtube_dialog(self, url: str, cookie_path: Optional[str] = None, browser: Optional[str] = None) -> None:
        """Show YouTube download dialog - delegated to handler system."""
        # This is handled by the new link detection system
        self.update_status("YouTube dialog handled by link detection system")