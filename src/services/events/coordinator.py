import os
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from src.core.models import Download, ServiceType
from src.interfaces.event_handlers import (
    AuthenticationHandler,
    ConfigurationHandler,
    DownloadManagementHandler,
    FileManagementHandler,
    NetworkStatusHandler,
    UIUpdateHandler,
    URLDetectionHandler,
    YouTubeSpecificHandler,
)
from src.ui.dialogs.file_manager_dialog import FileManagerDialog
from src.ui.dialogs.network_status_dialog import NetworkStatusDialog
from src.utils.logger import get_logger

from ..detection.link_detector import LinkDetector
from ..network.checker import check_all_services, check_internet_connection

logger = get_logger(__name__)


class EventCoordinator(
    URLDetectionHandler,
    DownloadManagementHandler,
    UIUpdateHandler,
    AuthenticationHandler,
    FileManagementHandler,
    ConfigurationHandler,
    NetworkStatusHandler,
    YouTubeSpecificHandler,
):
    """Coordinates events between UI and business logic."""

    def __init__(self, root_window: ctk.CTk, container):
        self.root = root_window
        self.container = container
        self.link_detector = LinkDetector()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup internal handlers and services."""
        logger.info("[EVENT_COORDINATOR] _setup_handlers called")
        # Get services from container
        self.download_list = self.container.get("download_list")
        logger.info(f"[EVENT_COORDINATOR] Got download_list: {self.download_list}")

        self.status_bar = self.container.get("status_bar")
        logger.info(f"[EVENT_COORDINATOR] Got status_bar: {self.status_bar}")

        self.action_buttons = self.container.get("action_buttons")
        logger.info(f"[EVENT_COORDINATOR] Got action_buttons: {self.action_buttons}")

        self.url_entry = self.container.get("url_entry")
        logger.info(f"[EVENT_COORDINATOR] Got url_entry: {self.url_entry}")

        self.cookie_handler = self.container.get("cookie_handler")
        logger.info(f"[EVENT_COORDINATOR] Got cookie_handler: {self.cookie_handler}")

        self.auth_handler = self.container.get("auth_handler")
        logger.info(f"[EVENT_COORDINATOR] Got auth_handler: {self.auth_handler}")

        self.service_controller = self.container.get("service_controller")
        logger.info(
            f"[EVENT_COORDINATOR] Got service_controller: {self.service_controller}"
        )

        logger.info("[EVENT_COORDINATOR] _setup_handlers completed")

    def refresh_handlers(self):
        """Refresh handlers after UI components are registered."""
        logger.info("[EVENT_COORDINATOR] refresh_handlers called")
        self._setup_handlers()
        logger.info("[EVENT_COORDINATOR] refresh_handlers completed")

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
        """Add a download to the system."""
        logger.info(f"[EVENT_COORDINATOR] add_download called with: {download}")
        logger.info(f"[EVENT_COORDINATOR] download type: {type(download)}")
        logger.info(f"[EVENT_COORDINATOR] download_list: {self.download_list}")
        logger.info(
            f"[EVENT_COORDINATOR] download_list type: {type(self.download_list)}"
        )

        if not self.download_list:
            logger.error("[EVENT_COORDINATOR] download_list is None or falsy")
            return False
        try:
            logger.info("[EVENT_COORDINATOR] Adding download to download_list")
            self.download_list.add_download(download)
            self.update_status(f"Download added: {download.name}")
            return True
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Failed to add download: {e}", exc_info=True
            )
            self.show_error("Add Error", f"Failed to add download: {str(e)}")
            return False

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
        logger.info("[EVENT_COORDINATOR] start_downloads called")
        logger.info(f"[EVENT_COORDINATOR] download_list: {self.download_list}")
        logger.info(f"[EVENT_COORDINATOR] action_buttons: {self.action_buttons}")
        logger.info(
            f"[EVENT_COORDINATOR] service_controller: {self.service_controller}"
        )

        try:
            if not self.download_list or not self.download_list.has_items():
                logger.warning("[EVENT_COORDINATOR] No downloads to start")
                self.update_status("Please add items to download")
                return False

            logger.info(
                "[EVENT_COORDINATOR] Downloads available, checking service_controller"
            )
            if self.service_controller:
                logger.info("[EVENT_COORDINATOR] Getting downloads from download_list")
                downloads = self.download_list.get_downloads()
                logger.info(
                    f"[EVENT_COORDINATOR] Got {len(downloads)} downloads: {downloads}"
                )

                # Update each download status to "Downloading" before starting
                from src.core.models import DownloadStatus

                for download in downloads:
                    download.status = DownloadStatus.DOWNLOADING
                    download.progress = 0.0

                # Refresh the UI to show updated status
                if self.download_list:
                    self.download_list.refresh_items(downloads)

                # Define callbacks for UI feedback (THREAD-SAFE)
                def on_progress(download, progress):
                    """Called from worker thread - must schedule UI updates on main thread."""
                    logger.debug(
                        f"[EVENT_COORDINATOR] Progress callback: {download.name} - {progress}%"
                    )
                    # Schedule UI update on main thread
                    self.root.after(
                        0, lambda: self._update_progress_ui(download, progress)
                    )

                def on_completion(success, message):
                    """Called from worker thread - must schedule UI updates on main thread."""
                    logger.info(
                        f"[EVENT_COORDINATOR] Completion callback: success={success}, message={message}"
                    )
                    # Schedule UI update on main thread
                    self.root.after(
                        0, lambda: self._handle_completion_ui(success, message)
                    )

                # Disable buttons during download
                if self.action_buttons:
                    logger.info(
                        "[EVENT_COORDINATOR] Disabling action buttons during download"
                    )
                    self.action_buttons.set_enabled(False)
                else:
                    logger.warning(
                        "[EVENT_COORDINATOR] action_buttons is None, cannot disable buttons"
                    )

                # Start downloads with callbacks using download handler directly
                logger.info(
                    "[EVENT_COORDINATOR] Calling download_handler.start_downloads"
                )
                download_handler = self.container.get("download_handler")
                if not download_handler:
                    logger.error("[EVENT_COORDINATOR] download_handler not found")
                    self.show_error("Download Error", "Download handler not available")
                    return False

                download_handler.start_downloads(
                    downloads, self.get_download_directory(), on_progress, on_completion
                )
                logger.info(
                    "[EVENT_COORDINATOR] download_handler.start_downloads called successfully"
                )
                return True
            else:
                logger.error("[EVENT_COORDINATOR] service_controller is None")

        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Failed to start downloads: {e}", exc_info=True
            )
            self.show_error("Download Error", f"Failed to start downloads: {str(e)}")
            if self.action_buttons:
                logger.info(
                    "[EVENT_COORDINATOR] Re-enabling action buttons after error"
                )
                self.action_buttons.set_enabled(True)

        logger.warning("[EVENT_COORDINATOR] start_downloads returning False")
        return False

    # UIUpdateHandler implementation
    def update_status(self, message: str, is_error: bool = False) -> None:
        """Update status bar message."""
        if not self.status_bar:
            return

        if is_error:
            self.status_bar.show_error(message)
        else:
            self.status_bar.show_message(message)

    def update_progress(self, download: Download, progress: float) -> None:
        """Update download progress (DEPRECATED - use _update_progress_ui for thread-safe updates)."""
        if self.status_bar:
            self.status_bar.show_message(
                f"Downloading {download.name}: {progress:.1f}%"
            )

    def _update_progress_ui(self, download: Download, progress: float) -> None:
        """Update download progress in UI (called on main thread)."""
        logger.info(
            f"[EVENT_COORDINATOR] _update_progress_ui called: {download.name} - {progress}%"
        )

        # Update the download object
        download.progress = progress
        logger.info(f"[EVENT_COORDINATOR] Updated download.progress to {progress}")

        # Update the download list item UI
        if self.download_list:
            logger.info(
                f"[EVENT_COORDINATOR] Calling download_list.update_item_progress"
            )
            self.download_list.update_item_progress(download, progress)
            logger.info(
                f"[EVENT_COORDINATOR] download_list.update_item_progress completed"
            )
        else:
            logger.warning(
                f"[EVENT_COORDINATOR] download_list is None, cannot update UI"
            )

        # Update status bar
        if self.status_bar:
            logger.info(f"[EVENT_COORDINATOR] Updating status bar")
            self.status_bar.show_message(
                f"Downloading {download.name}: {progress:.1f}%"
            )
        else:
            logger.warning(f"[EVENT_COORDINATOR] status_bar is None")

    def _handle_completion_ui(self, success: bool, message: str) -> None:
        """Handle download completion in UI (called on main thread)."""
        try:
            logger.info(
                f"[EVENT_COORDINATOR] _handle_completion_ui: success={success}, message={message}"
            )

            # Re-enable buttons
            if self.action_buttons:
                logger.info("[EVENT_COORDINATOR] Re-enabling action buttons")
                try:
                    self.action_buttons.set_enabled(True)
                except Exception as e:
                    logger.error(f"[EVENT_COORDINATOR] Error re-enabling buttons: {e}")

            # Don't clear downloads - just update status
            # Users might want to retry failed downloads

            # Show completion message
            if success:
                self.update_status("Download completed successfully!")
            else:
                self.update_status(f"Download failed: {message}", is_error=True)

        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error in completion handler: {e}", exc_info=True
            )

    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        """Update button enabled/disabled states."""
        logger.debug(
            f"[EVENT_COORDINATOR] update_button_states called: has_selection={has_selection}, has_items={has_items}"
        )
        logger.debug(f"[EVENT_COORDINATOR] action_buttons: {self.action_buttons}")
        if self.action_buttons:
            try:
                self.action_buttons.update_button_states(has_selection, has_items)
                logger.debug(
                    "[EVENT_COORDINATOR] action_buttons.update_button_states called successfully"
                )
            except Exception as e:
                logger.error(
                    f"[EVENT_COORDINATOR] Error calling action_buttons.update_button_states: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                "[EVENT_COORDINATOR] action_buttons is None, cannot update button states"
            )

    def show_error(self, title: str, message: str) -> None:
        """Show error dialog."""
        messagebox.showerror(title, message)

    # AuthenticationHandler implementation
    def authenticate_instagram(
        self,
        parent_window: Any = None,
        callback: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """Handle Instagram authentication."""
        if self.auth_handler:
            self.auth_handler.authenticate_instagram(
                parent_window or self.root, callback or (lambda success: None)
            )

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
        initial_path = (
            self.get_download_directory()
        )  # Already expanded by get_download_directory()
        FileManagerDialog(
            self.root, initial_path, self.set_download_directory, self.update_status
        )

    def browse_files(self, file_types: List[str]) -> Optional[str]:
        """Browse for files."""
        from tkinter import filedialog

        file_types_formatted = [(ft, f"*.{ft}") for ft in file_types]
        file_types_formatted.append(("All files", "*.*"))
        return filedialog.askopenfilename(filetypes=file_types_formatted)

    # ConfigurationHandler implementation
    def get_download_directory(self) -> str:
        """Get download directory."""
        ui_state = self.container.get("ui_state")
        directory = (
            getattr(ui_state, "download_directory", "~/Downloads")
            if ui_state
            else "~/Downloads"
        )
        return os.path.expanduser(directory)

    def set_download_directory(self, directory: str) -> bool:
        """Set download directory."""
        try:
            ui_state = self.container.get("ui_state")
            if ui_state:
                ui_state.download_directory = directory

                # Refresh button states after directory change
                if hasattr(self, "download_list") and self.download_list:
                    has_items = self.download_list.has_items()
                    selected_indices = self.download_list.get_selected_indices()
                    has_selection = bool(selected_indices)
                    self.update_button_states(has_selection, has_items)

                return True
        except Exception as e:
            self.show_error(
                "Configuration Error", f"Failed to set download directory: {str(e)}"
            )
        return False

    def save_configuration(self) -> bool:
        """Save current configuration."""
        # Implementation would save to config file
        return True

    # NetworkStatusHandler implementation
    def check_connectivity(self) -> bool:
        """Check internet connectivity."""
        return check_internet_connection()

    def check_service_status(self, services: List[str]) -> Dict[str, bool]:
        """Check status of specific services."""
        results = check_all_services()
        return {service: results.get(service, (False, ""))[0] for service in services}

    def show_network_status(self) -> None:
        """Show network status dialog."""
        NetworkStatusDialog(self.root)

    # YouTubeSpecificHandler implementation
    def handle_youtube_download(self, url: str, name: str, options: dict) -> None:
        """Handle YouTube download completion."""
        logger.info("[EVENT_COORDINATOR] handle_youtube_download called")
        logger.info(f"[EVENT_COORDINATOR] URL: {url}")
        logger.info(f"[EVENT_COORDINATOR] Name: {name}")
        logger.info(f"[EVENT_COORDINATOR] Options: {options}")

        try:
            # Create download with YouTube-specific options
            logger.info("[EVENT_COORDINATOR] Creating Download object")
            download = Download(
                name=name,
                url=url,
                service_type=ServiceType.YOUTUBE,
                quality=options.get("quality", "720p"),
                format=options.get("format", "video"),
                audio_only=options.get("audio_only", False),
                video_only=options.get("video_only", False),
                download_playlist=options.get("download_playlist", False),
                download_subtitles=options.get("download_subtitles", False),
                selected_subtitles=options.get("selected_subtitles"),
                download_thumbnail=options.get("download_thumbnail", True),
                embed_metadata=options.get("embed_metadata", True),
                cookie_path=options.get("cookie_path"),
                selected_browser=options.get("selected_browser"),
                speed_limit=options.get("speed_limit"),
                retries=options.get("retries", 3),
                concurrent_downloads=options.get("concurrent_downloads", 1),
            )
            logger.info(f"[EVENT_COORDINATOR] Download object created: {download}")

            # Add to download list
            logger.info("[EVENT_COORDINATOR] Calling add_download")
            if self.add_download(download):
                logger.info("[EVENT_COORDINATOR] Download added successfully")
                # Reset URL entry field
                if self.url_entry:
                    logger.info("[EVENT_COORDINATOR] Resetting URL entry field")
                    try:
                        if hasattr(self.url_entry, "url_entry"):
                            self.url_entry.url_entry.delete(0, "end")
                            self.url_entry.url_entry.insert(0, "")
                        else:
                            self.url_entry.delete(0, "end")
                            self.url_entry.insert(0, "")
                        logger.info(
                            "[EVENT_COORDINATOR] URL entry field reset successfully"
                        )
                    except Exception as e:
                        logger.error(
                            f"[EVENT_COORDINATOR] Error resetting URL entry: {e}",
                            exc_info=True,
                        )
                else:
                    logger.warning(
                        "[EVENT_COORDINATOR] url_entry is None, cannot reset"
                    )

                # Create descriptive message
                config_desc = []
                if options.get("format") == "audio":
                    config_desc.append("Audio")
                elif options.get("format") == "video_only":
                    config_desc.append("Video Only")
                if options.get("download_playlist"):
                    config_desc.append("Playlist")
                if options.get("quality") and options.get("quality") != "720p":
                    config_desc.append(f"{options.get('quality')}")
                if options.get("selected_browser"):
                    config_desc.append(f"{options.get('selected_browser')} cookies")

                desc = f"YouTube {config_desc[0]}" if config_desc else "YouTube video"
                status_message = f"{desc} added: {name}"
                logger.info(f"[EVENT_COORDINATOR] Updating status: {status_message}")
                self.update_status(status_message)
            else:
                logger.error(
                    "[EVENT_COORDINATOR] Failed to add download (add_download returned False)"
                )

        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Failed to process YouTube download: {e}",
                exc_info=True,
            )
            self.show_error(
                "YouTube Download Error",
                f"Failed to process YouTube download: {str(e)}",
            )

    def show_youtube_dialog(
        self, url: str, cookie_path: Optional[str] = None, browser: Optional[str] = None
    ) -> None:
        """Show YouTube download dialog - delegated to handler system."""
        # This is handled by the new link detection system
        self.update_status("YouTube dialog handled by link detection system")
