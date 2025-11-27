"""Platform Dialog Coordinator - SOLID polymorphic dialog handling."""

import os
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional

from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.models import Download
from src.interfaces.service_interfaces import ICookieHandler, IErrorHandler
from src.services.instagram.downloader import InstagramDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.ui.dialogs.login_dialog import LoginDialog
from src.utils.error_helpers import extract_error_context, format_user_friendly_error
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DialogHandler(ABC):
    """Base interface for platform-specific dialog handlers."""

    def __init__(self, error_handler: IErrorHandler):
        """Initialize dialog handler with error handler.

        Args:
            error_handler: Error handler for user notifications
        """
        self.error_handler = error_handler

    @abstractmethod
    def show_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show platform-specific download dialog.

        Args:
            url: URL to download
            on_download_callback: Callback to execute when download is confirmed
        """
        pass


class TwitterDialogHandler(DialogHandler):
    """Twitter dialog handler."""

    def show_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show Twitter download dialog."""
        try:
            download = Download(
                url=url,
                name=os.path.basename(url) or "twitter_download",
                service_type="twitter",
            )
            on_download_callback(download)
            logger.info(f"[TWITTER_DIALOG] Download added: {url}")
        except Exception as e:
            logger.error(f"[TWITTER_DIALOG] Error: {e}", exc_info=True)
            error_context = extract_error_context(e, "Twitter", "dialog", url)
            error_msg = format_user_friendly_error(error_context)
            self.error_handler.handle_exception(e, "Twitter dialog", "Twitter")


class InstagramDialogHandler(DialogHandler):
    """Instagram dialog handler."""

    def show_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show Instagram download dialog."""
        try:
            download = Download(
                url=url,
                name=os.path.basename(url) or "instagram_download",
                service_type="instagram",
            )
            on_download_callback(download)
            logger.info(f"[INSTAGRAM_DIALOG] Download added: {url}")
        except Exception as e:
            logger.error(f"[INSTAGRAM_DIALOG] Error: {e}", exc_info=True)
            error_context = extract_error_context(e, "Instagram", "dialog", url)
            error_msg = format_user_friendly_error(error_context)
            self.error_handler.handle_exception(e, "Instagram dialog", "Instagram")


class PinterestDialogHandler(DialogHandler):
    """Pinterest dialog handler."""

    def show_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show Pinterest download dialog."""
        try:
            download = Download(
                url=url,
                name=os.path.basename(url) or "pinterest_download",
                service_type="pinterest",
            )
            on_download_callback(download)
            logger.info(f"[PINTEREST_DIALOG] Download added: {url}")
        except Exception as e:
            logger.error(f"[PINTEREST_DIALOG] Error: {e}", exc_info=True)
            error_context = extract_error_context(e, "Pinterest", "dialog", url)
            error_msg = format_user_friendly_error(error_context)
            self.error_handler.handle_exception(e, "Pinterest dialog", "Pinterest")


class SoundCloudDialogHandler(DialogHandler):
    """SoundCloud dialog handler with premium check."""

    def show_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show SoundCloud download dialog with track info."""
        try:

            downloader = SoundCloudDownloader(error_handler=self.error_handler)
            info = downloader.get_info(url)

            if not info:
                download = Download(
                    url=url,
                    name=os.path.basename(url) or "soundcloud_download",
                    service_type="soundcloud",
                )
                on_download_callback(download)
                return

            if downloader._is_premium_track(info):
                error_msg = "This SoundCloud track requires a Go+ subscription. Premium tracks cannot be downloaded."
                self.error_handler.handle_service_failure("SoundCloud", "download", error_msg, url)
                return

            track_name = f"{info.get('artist', 'Unknown')} - {info.get('title', 'Unknown')}"
            download = Download(
                url=url,
                name=track_name,
                service_type="soundcloud",
            )
            on_download_callback(download)
            logger.info(f"[SOUNDCLOUD_DIALOG] Download added: {track_name}")

        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["premium", "go+", "subscription", "not available"]):
                error_msg = "This SoundCloud track requires a Go+ subscription. Premium tracks cannot be downloaded."
                self.error_handler.handle_service_failure("SoundCloud", "download", error_msg, url)
                return

            logger.error(f"[SOUNDCLOUD_DIALOG] Error: {e}", exc_info=True)
            error_context = extract_error_context(e, "SoundCloud", "dialog", url)
            self.error_handler.handle_exception(e, "SoundCloud dialog", "SoundCloud")


class GenericDialogHandler(DialogHandler):
    """Generic dialog handler for unknown platforms."""

    def show_dialog(self, url: str, on_download_callback: Callable, name: Optional[str] = None) -> None:
        """Show generic download dialog."""
        try:
            download = Download(
                url=url,
                name=name or os.path.basename(url) or "download",
                service_type="generic",
            )
            on_download_callback(download)
            logger.info(f"[GENERIC_DIALOG] Download added: {url}")
        except Exception as e:
            logger.error(f"[GENERIC_DIALOG] Error: {e}", exc_info=True)
            error_context = extract_error_context(e, "Generic", "download", url)
            self.error_handler.handle_exception(e, "Generic download", "Download")


class PlatformDialogCoordinator:
    """Coordinates platform-specific UI dialogs using polymorphic handlers."""

    def __init__(
        self,
        root_window,
        error_handler: IErrorHandler,
        cookie_handler: Optional[ICookieHandler] = None,
        orchestrator=None,
    ):
        """Initialize with proper dependency injection.

        Args:
            root_window: Root window for dialogs
            error_handler: Error handler for user notifications
            cookie_handler: Optional cookie handler
            orchestrator: Optional orchestrator reference
        """
        self.root = root_window
        self.error_handler = error_handler
        self.cookie_handler = cookie_handler
        self.orchestrator = orchestrator

        self._dialog_handlers = {
            "twitter": TwitterDialogHandler(error_handler),
            "instagram": InstagramDialogHandler(error_handler),
            "pinterest": PinterestDialogHandler(error_handler),
            "soundcloud": SoundCloudDialogHandler(error_handler),
            "generic": GenericDialogHandler(error_handler),
        }

    def show_youtube_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show YouTube download dialog.

        Note: YouTube handler manages its own dialog flow.
        This is a compatibility stub.
        """
        logger.warning("[PLATFORM_DIALOG_COORDINATOR] YouTube dialog should be handled by YouTubeHandler")

    def show_twitter_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show Twitter download dialog."""
        handler = self._dialog_handlers["twitter"]
        handler.show_dialog(url, on_download_callback)

    def show_instagram_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show Instagram download dialog."""
        handler = self._dialog_handlers["instagram"]
        handler.show_dialog(url, on_download_callback)

    def show_pinterest_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show Pinterest download dialog."""
        handler = self._dialog_handlers["pinterest"]
        handler.show_dialog(url, on_download_callback)

    def show_soundcloud_dialog(self, url: str, on_download_callback: Callable) -> None:
        """Show SoundCloud download dialog."""
        handler = self._dialog_handlers["soundcloud"]
        handler.show_dialog(url, on_download_callback)

    def generic_download(self, url: str, name: Optional[str], on_download_callback: Callable) -> None:
        """Generic download handler."""
        handler = self._dialog_handlers["generic"]
        handler.show_dialog(url, on_download_callback, name)

    def authenticate_instagram(self, parent_window, callback: Optional[Callable] = None) -> None:
        """Show Instagram authentication dialog with full login flow.
        
        Args:
            parent_window: Parent window for dialogs
            callback: Optional callback to update button state (receives InstagramAuthStatus)
        """
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Starting Instagram authentication")

        options_bar = self._get_options_bar(parent_window)
        
        if options_bar:
            options_bar.set_instagram_status(InstagramAuthStatus.LOGGING_IN)
        elif callback:
            callback(InstagramAuthStatus.LOGGING_IN)

        try:

            dialog = LoginDialog(
                parent_window,
                error_handler=self.error_handler,
                message_queue=None,  # LoginDialog doesn't need message_queue as it's modal
            )
            dialog.wait_window()

            if not dialog.username or not dialog.password:
                logger.info("[PLATFORM_DIALOG_COORDINATOR] Instagram login cancelled")
                if options_bar:
                    options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
                elif callback:
                    callback(InstagramAuthStatus.FAILED)
                    self.error_handler.show_info("Instagram Login", "Login cancelled")
                return

            username = dialog.username
            password = dialog.password

            def auth_worker():
                """Background thread worker for authentication."""
                try:
                    downloader = InstagramDownloader(error_handler=self.error_handler)
                    success = downloader.authenticate(username, password)
                    error_msg = "" if success else "Authentication failed"

                    def update_ui():
                            self._handle_auth_result(success, username, options_bar, callback, error_msg)

                    self.root.after(0, update_ui)
                except Exception as e:
                    logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Authentication error: {e}", exc_info=True)
                    error_context = extract_error_context(e, "Instagram", "authentication", "")
                    self.error_handler.handle_exception(e, "Instagram authentication", "Instagram")

                    def update_ui_error():
                        self._handle_auth_result(False, username, options_bar, callback, str(e))

                    self.root.after(0, update_ui_error)

            thread = threading.Thread(target=auth_worker, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error showing login dialog: {e}", exc_info=True)
            error_context = extract_error_context(e, "Instagram", "login dialog", "")
            self.error_handler.handle_exception(e, "Showing Instagram login dialog", "Instagram")

            if options_bar:
                options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
            elif callback:
                callback(InstagramAuthStatus.FAILED)

    def _get_options_bar(self, parent_window):
        """Get options bar from parent window or orchestrator."""
        try:
            if hasattr(parent_window, 'options_bar'):
                return parent_window.options_bar
            if self.orchestrator:
                ui_components = getattr(self.orchestrator, 'ui_components', {})
                return ui_components.get('options_bar')
            if hasattr(parent_window, 'orchestrator'):
                ui_components = getattr(parent_window.orchestrator, 'ui_components', {})
                return ui_components.get('options_bar')
        except Exception as e:
            logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] Could not get options bar: {e}")
        return None

    def _handle_auth_result(
        self,
        success: bool,
        username: str,
        options_bar,
        callback: Optional[Callable] = None,
        error_message: str = "",
    ) -> None:
        """Handle authentication result on main thread."""
        if success:
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication successful for {username[:3]}***")
            if options_bar:
                options_bar.set_instagram_status(InstagramAuthStatus.AUTHENTICATED)
            elif callback:
                callback(InstagramAuthStatus.AUTHENTICATED)
                self.error_handler.show_info("Instagram Login", f"Successfully authenticated as {username}")
        else:
            logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication failed for {username[:3]}***")
            if options_bar:
                options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
            elif callback:
                callback(InstagramAuthStatus.FAILED)
            error_msg = error_message or "Invalid credentials or authentication failed"
            self.error_handler.handle_service_failure("Instagram", "authentication", error_msg, "")
    