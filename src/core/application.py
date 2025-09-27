"""Application orchestrator that coordinates all services and UI."""

import os
import logging
from typing import Optional, Any
import customtkinter as ctk
from tkinter import messagebox

from .models import UIState
from .message_queue import MessageQueue
from .network import check_internet_connection, check_all_services
from .container import ServiceContainer
from ..handlers.cookie_handler import CookieHandler
from ..handlers.auth_handler import AuthenticationHandler
from ..handlers.download_handler import DownloadHandler
from ..services.youtube.cookie_detector import CookieManager
from ..services.factory import ServiceFactory
from ..services.download import DownloadService

logger = logging.getLogger(__name__)


class ApplicationOrchestrator:
    """Orchestrates all application services and coordinates UI interactions."""

    def __init__(self, root_window: ctk.CTk):
        self.root = root_window
        self.ui_state = UIState()
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.message_queue = MessageQueue(root_window)

        # Initialize service container
        self.container = ServiceContainer()
        self._initialize_services()

        # Initialize event handling directly
        self._setup_event_handlers()

        # UI components (will be set by the main entrypoint)
        self.ui_components = {}

        logger.info("Application orchestrator initialized")

    def _initialize_services(self):
        """Initialize all application services using the container."""
        # Register singletons first
        self.container.register('ui_state', self.ui_state, singleton=True)
        self.container.register('message_queue', self.message_queue, singleton=True)
        self.container.register('downloads_folder', self.downloads_folder, singleton=True)

        # Register service factories
        from ..services.youtube.cookie_detector import CookieManager, CookieDetector
        from ..handlers.network_checker import NetworkChecker
        from ..handlers.service_detector import ServiceDetector

        self.container.register_factory('cookie_detector', lambda: self._create_simple_cookie_detector())
        self.container.register_factory('auth_manager', lambda: self._create_auth_manager())
        self.container.register_factory('network_checker', lambda: NetworkChecker())
        self.container.register_factory('service_detector', lambda: ServiceDetector())

        # Initialize core services
        cookie_detector = self.container.get('cookie_detector')
        cookie_manager = CookieManager()
        cookie_manager.initialize()

        service_factory = ServiceFactory(cookie_manager)
        download_service = DownloadService(service_factory)

        # Register core services
        self.container.register('cookie_manager', cookie_manager, singleton=True)
        self.container.register('service_factory', service_factory, singleton=True)
        self.container.register('download_service', download_service, singleton=True)

        # Initialize and register handlers using dependency injection
        auth_manager = self.container.get('auth_manager')
        self.container.register('auth_manager', auth_manager, singleton=True)

        cookie_handler = CookieHandler(cookie_manager)
        auth_handler = AuthenticationHandler(auth_manager)
        download_handler = DownloadHandler(self.container)
        network_checker = self.container.get('network_checker')
        service_detector = self.container.get('service_detector')

        # Initialize handlers
        auth_handler.initialize()
        network_checker.initialize()
        service_detector.initialize()
        download_handler.initialize()

        # Register handlers
        self.container.register('cookie_handler', cookie_handler, singleton=True)
        self.container.register('auth_handler', auth_handler, singleton=True)
        self.container.register('download_handler', download_handler, singleton=True)
        self.container.register('network_checker', network_checker, singleton=True)
        self.container.register('service_detector', service_detector, singleton=True)

        # Create a simple service controller for now
        class SimpleServiceController:
            def __init__(self, download_service, service_factory, cookie_manager):
                self.download_service = download_service
                self.service_factory = service_factory
                self.cookie_manager = cookie_manager

            def start_downloads(self, downloads, progress_callback=None, completion_callback=None):
                # Simple implementation for now
                if completion_callback:
                    completion_callback(True, "Downloads completed")

            def has_active_downloads(self):
                return False

        self.container.register('service_controller', SimpleServiceController(
            download_service=download_service,
            service_factory=service_factory,
            cookie_manager=cookie_manager
        ), singleton=True)

        # Register orchestrator as event handler
        self.container.register('event_handler', self, singleton=True)

        logger.info("All services registered in container")

    def _create_auth_manager(self):
        """Create a simple auth manager for now."""
        class SimpleAuthManager:
            def authenticate_instagram(self, parent_window, callback):
                # Simple implementation for now
                callback(False)

            def cleanup(self):
                pass

        return SimpleAuthManager()

    def _create_simple_cookie_detector(self):
        """Create a simple cookie detector for now."""
        from ..interfaces.cookie_detection import ICookieDetector, BrowserType, PlatformType

        class SimpleCookieDetector(ICookieDetector):
            def __init__(self):
                self._platform = self._detect_platform()

            def _detect_platform(self):
                import platform
                system = platform.system().lower()
                if system == "windows":
                    return PlatformType.WINDOWS
                elif system == "darwin":
                    return PlatformType.MACOS
                else:
                    return PlatformType.LINUX

            def get_supported_browsers(self):
                return [BrowserType.CHROME, BrowserType.FIREFOX]

            def detect_cookies_for_browser(self, browser: BrowserType):
                return None

            def get_current_cookie_path(self):
                return None

        return SimpleCookieDetector()

    def set_ui_components(self, **components):
        """Set UI component references."""
        self.ui_components.update(components)
        logger.debug("UI components registered")

    def handle(self, event_name: str, *args, **kwargs):
        """Handle an event through the application controller."""
        return self.app_controller.handle_event(event_name, *args, **kwargs)

    def get_service(self, service_name: str):
        """Get a service from the container."""
        return self.container.get(service_name)

    def check_connectivity(self):
        """Check internet connectivity at startup."""
        status_bar = self.ui_components.get('status_bar')
        if status_bar:
            status_bar.show_message("Checking network connectivity...")

        def check_worker():
            internet_connected, error_msg = check_internet_connection()
            service_results = check_all_services()
            problem_services = [
                service for service, (connected, _) in service_results.items()
                if not connected
            ]

            self.root.after(0, lambda: self._handle_connectivity_check(
                internet_connected, error_msg, problem_services
            ))

        import threading
        threading.Thread(target=check_worker, daemon=True).start()

    def _handle_connectivity_check(self, internet_connected: bool, error_msg: str, problem_services: list):
        """Handle the results of the connectivity check."""
        status_bar = self.ui_components.get('status_bar')

        if not internet_connected:
            messagebox.showwarning(
                "Network Connectivity Issue",
                f"There are network connectivity issues:\n\n{error_msg}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            if status_bar:
                status_bar.show_warning("Network connectivity issues detected")
        elif problem_services:
            problem_list = ", ".join(problem_services)
            messagebox.showwarning(
                "Service Connection Issues",
                f"Cannot connect to the following services: {problem_list}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            if status_bar:
                status_bar.show_warning(f"Connection issues with: {problem_list}")
        else:
            if status_bar:
                status_bar.show_message("Ready - All services connected")

    def show_network_status(self):
        """Show network status dialog."""
        from ..ui.dialogs.network_status_dialog import NetworkStatusDialog
        NetworkStatusDialog(self.root)

    def cleanup(self):
        """Clean up all services."""
        try:
            # Clean up services that need cleanup
            cookie_handler = self.container.get('cookie_handler')
            auth_handler = self.container.get('auth_handler')
            download_handler = self.container.get('download_handler')
            network_checker = self.container.get('network_checker')

            if cookie_handler:
                cookie_handler.cleanup()
            if auth_handler:
                auth_handler.cleanup()
            if download_handler:
                download_handler.cleanup()
            if network_checker:
                network_checker.cleanup()

            self.container.clear()
            logger.info("Application cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def _setup_event_handlers(self):
        """Set up direct event handling methods."""
        logger.info("Event handlers initialized")

    def handle_add_url(self, url: str, name: str = None):
        """Handle adding a new URL."""
        from ..core.models import Download

        # Validate URL
        if not url.startswith('http'):
            raise ValueError("Invalid URL format. URL must start with http:// or https://")

        # Detect service type
        service_detector = self.container.get('service_detector')
        service_type = service_detector.detect_service(url)
        if not service_type:
            raise ValueError("Unsupported platform")

        # Check service accessibility
        if not service_detector.is_service_accessible(service_type):
            raise ValueError(f"Cannot connect to {service_type.value}")

        # Create download item
        if not name:
            name = f"Media from {service_type.value}"

        download = Download(name=name, url=url, service_type=service_type)

        # Add to download list
        download_list = self.download_list
        if download_list:
            download_list.add_download(download)

        status_bar = self.status_bar
        if status_bar:
            status_bar.show_message(f"Added: {name}")

    def handle_remove(self):
        """Handle removing selected items."""
        download_list = self.download_list
        if not download_list:
            return

        selected_indices = download_list.get_selected_indices()
        if not selected_indices:
            status_bar = self.status_bar
            if status_bar:
                status_bar.show_message("Please select items to remove")
            return

        download_list.remove_downloads(selected_indices)

        status_bar = self.status_bar
        if status_bar:
            status_bar.show_message("Selected items removed")

    def handle_clear(self):
        """Handle clearing all items."""
        download_list = self.download_list
        if not download_list:
            return

        download_list.clear_downloads()

        status_bar = self.status_bar
        if status_bar:
            status_bar.show_message("All items cleared")

    def handle_download(self):
        """Handle starting downloads."""
        download_list = self.download_list
        if not download_list or not download_list.has_items():
            status_bar = self.status_bar
            if status_bar:
                status_bar.show_message("Please add items to download")
            return

        # Get service controller and start downloads
        service_controller = self.container.get('service_controller')
        if service_controller:
            downloads = download_list.get_downloads()
            service_controller.start_downloads(downloads)

    def handle_selection_change(self, selected_indices: list):
        """Handle selection changes."""
        action_buttons = self.action_buttons
        if action_buttons:
            has_selection = bool(selected_indices)
            action_buttons.update_button_states(has_selection)

    def handle_quality_change(self, quality: str):
        """Handle quality changes."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            ui_state.quality = quality

    def handle_option_change(self, option_name: str, value: Any):
        """Handle option changes."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            if option_name == 'audio_only':
                ui_state.audio_only = value
            elif option_name == 'download_playlist':
                ui_state.download_playlist = value

    def handle_instagram_login(self, parent_window=None):
        """Handle Instagram login."""
        auth_handler = self.container.get('auth_handler')
        if auth_handler:
            auth_handler.authenticate_instagram(parent_window, lambda success: None)

    def handle_youtube_detected(self, url: str):
        """Handle YouTube URL detection by opening new dialog."""
        from ..ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog
        cookie_handler = self.container.get('cookie_handler')

        dialog = YouTubeDownloaderDialog(
            self.root,
            url=url,
            cookie_handler=cookie_handler,
            on_download=self._handle_youtube_download
        )

    def handle_cookie_detected(self, browser_type: str, cookie_path: str):
        """Handle cookie detection."""
        cookie_handler = self.container.get('cookie_handler')
        if cookie_handler:
            success = cookie_handler.set_cookie_file(cookie_path)
            status_bar = self.status_bar
            if status_bar:
                if success:
                    status_bar.show_message(f"Cookies loaded from {browser_type}")
                else:
                    status_bar.show_error("Failed to load cookies")

    def handle_cookie_manual_select(self):
        """Handle manual cookie selection."""
        from ..ui.dialogs.file_manager_dialog import FileManagerDialog
        file_dialog = FileManagerDialog(self.root)
        cookie_path = file_dialog.select_file()

        if cookie_path:
            cookie_handler = self.container.get('cookie_handler')
            if cookie_handler:
                success = cookie_handler.set_cookie_file(cookie_path)
                status_bar = self.status_bar
                if status_bar:
                    if success:
                        status_bar.show_message("Cookie file loaded successfully")
                    else:
                        status_bar.show_error("Failed to load cookie file")

    def handle_manage_files(self):
        """Handle file management."""
        from ..ui.dialogs.file_manager_dialog import FileManagerDialog
        FileManagerDialog(self.root)

    def _handle_youtube_download(self, url: str, name: str, options: dict):
        """Handle YouTube download from the dialog with comprehensive options."""
        from ..core.models import Download, ServiceType

        # Create download item with all individual options
        download = Download(
            name=name,
            url=url,
            service_type=ServiceType.YOUTUBE,
            quality=options.get('quality', '720p'),
            format=options.get('format', 'video'),
            audio_only=options.get('audio_only', False),
            download_playlist=options.get('download_playlist', False),
            download_subtitles=options.get('download_subtitles', False),
            download_thumbnail=options.get('download_thumbnail', True),
            embed_metadata=options.get('embed_metadata', True),
            cookie_path=options.get('cookie_path'),
            selected_browser=options.get('selected_browser'),
            speed_limit=options.get('speed_limit'),
            retries=options.get('retries', 3),
            concurrent_downloads=options.get('concurrent_downloads', 1)
        )

        # Add to download list
        download_list = self.download_list
        if download_list:
            download_list.add_download(download)

        status_bar = self.status_bar
        if status_bar:
            # Create a descriptive message
            config_desc = []
            if options.get('audio_only'):
                config_desc.append("Audio Only")
            if options.get('download_playlist'):
                config_desc.append("Playlist")
            if options.get('quality') and options.get('quality') != '720p':
                config_desc.append(f"{options.get('quality')}")
            if options.get('selected_browser'):
                config_desc.append(f"{options.get('selected_browser')} cookies")

            desc = f"YouTube {config_desc[0]}" if config_desc else "YouTube video"
            status_bar.show_message(f"{desc} added: {name}")

    # Convenience properties for common services
    @property
    def service_controller(self):
        """Get the service controller."""
        return self.container.get('service_controller')

    @property
    def cookie_handler(self):
        """Get the cookie handler."""
        return self.container.get('cookie_handler')

    @property
    def auth_handler(self):
        """Get the auth handler."""
        return self.container.get('auth_handler')

    @property
    def network_checker(self):
        """Get the network checker."""
        return self.container.get('network_checker')

    @property
    def service_detector(self):
        """Get the service detector."""
        return self.container.get('service_detector')

    # Convenience properties for UI components
    @property
    def url_entry(self):
        """Get the URL entry component."""
        return self.ui_components.get('url_entry')

    @property
    def options_bar(self):
        """Get the options bar component."""
        return self.ui_components.get('options_bar')

    @property
    def download_list(self):
        """Get the download list component."""
        return self.ui_components.get('download_list')

    @property
    def action_buttons(self):
        """Get the action buttons component."""
        return self.ui_components.get('action_buttons')

    @property
    def status_bar(self):
        """Get the status bar component."""
        return self.ui_components.get('status_bar')

    @property
    def cookie_selector(self):
        """Get the cookie selector component."""
        return self.ui_components.get('cookie_selector')