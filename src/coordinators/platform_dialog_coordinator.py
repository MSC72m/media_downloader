"""Platform Dialog Coordinator - SOLID polymorphic dialog handling."""

import os
import re
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional

from src.core.config import AppConfig, get_config
from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.models import Download
from src.core.interfaces import ICookieHandler, IErrorNotifier
from src.services.instagram.auth_manager import InstagramAuthManager
from src.services.instagram.downloader import InstagramDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.ui.components.loading_dialog import LoadingDialog
from src.ui.dialogs.login_dialog import LoginDialog
from src.utils.error_helpers import extract_error_context
from src.utils.logger import get_logger
from src.utils.window import close_loading_dialog

logger = get_logger(__name__)


class DialogHandler(ABC):
    """Base interface for platform-specific dialog handlers."""

    def __init__(self, error_handler: IErrorNotifier):
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
            self.error_handler.handle_exception(e, "Pinterest dialog", "Pinterest")


class SoundCloudDialogHandler(DialogHandler):
    """SoundCloud dialog handler with premium check."""

    # Compiled regex pattern for premium keywords (more efficient than string 'in' check)
    _PREMIUM_KEYWORD_PATTERN = re.compile(
        r"(premium|go\+|subscription|not available)", re.IGNORECASE
    )

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
                self.error_handler.handle_service_failure(
                    "SoundCloud", "download", error_msg, url
                )
                return

            track_name = (
                f"{info.get('artist', 'Unknown')} - {info.get('title', 'Unknown')}"
            )
            download = Download(
                url=url,
                name=track_name,
                service_type="soundcloud",
            )
            on_download_callback(download)
            logger.info(f"[SOUNDCLOUD_DIALOG] Download added: {track_name}")

        except Exception as e:
            error_str = str(e)
            # Use compiled regex pattern for efficient matching
            if self._PREMIUM_KEYWORD_PATTERN.search(error_str):
                error_msg = "This SoundCloud track requires a Go+ subscription. Premium tracks cannot be downloaded."
                self.error_handler.handle_service_failure(
                    "SoundCloud", "download", error_msg, url
                )
                return

            logger.error(f"[SOUNDCLOUD_DIALOG] Error: {e}", exc_info=True)
            self.error_handler.handle_exception(e, "SoundCloud dialog", "SoundCloud")


class GenericDialogHandler(DialogHandler):
    """Generic dialog handler for unknown platforms."""

    def show_dialog(
        self, url: str, on_download_callback: Callable, name: Optional[str] = None
    ) -> None:
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
            self.error_handler.handle_exception(e, "Generic download", "Download")


class PlatformDialogCoordinator:
    """Coordinates platform-specific UI dialogs using polymorphic handlers."""

    def __init__(
        self,
        root_window,
        error_handler: IErrorNotifier,
        cookie_handler: Optional[ICookieHandler] = None,
        instagram_auth_manager: Optional[InstagramAuthManager] = None,
        orchestrator=None,
        config: AppConfig = get_config(),
    ):
        """Initialize with proper dependency injection.

        Args:
            root_window: Root window for dialogs
            error_handler: Error handler for user notifications
            cookie_handler: Optional cookie handler
            instagram_auth_manager: Optional Instagram authentication manager
            orchestrator: Optional orchestrator reference
        """
        self.root = root_window
        self.error_handler = error_handler
        self.cookie_handler = cookie_handler
        self.instagram_auth_manager = instagram_auth_manager
        self.orchestrator = orchestrator
        self.config = config

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
        logger.warning(
            "[PLATFORM_DIALOG_COORDINATOR] YouTube dialog should be handled by YouTubeHandler"
        )

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

    def generic_download(
        self, url: str, name: Optional[str], on_download_callback: Callable
    ) -> None:
        """Generic download handler."""
        handler = self._dialog_handlers["generic"]
        handler.show_dialog(url, on_download_callback, name)

    def authenticate_instagram(
        self, parent_window, callback: Optional[Callable] = None
    ) -> None:
        """Start Instagram authentication flow.

        Args:
            parent_window: Parent window for dialogs
            callback: Optional callback for auth status updates (receives InstagramAuthStatus)
        """
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Starting Instagram authentication")

        if not self.instagram_auth_manager:
            logger.error(
                "[PLATFORM_DIALOG_COORDINATOR] Instagram auth manager not available"
            )
            if callback:
                callback(InstagramAuthStatus.FAILED)
            return

        self.instagram_auth_manager.set_authenticating(True)

        try:
            credentials = self._get_instagram_credentials(parent_window)
            if not credentials:
                self._handle_auth_cancellation(callback)
                return

            username, password = credentials
            loading_dialog = self._show_loading_dialog(
                parent_window, "Authenticating with Instagram..."
            )

            thread = threading.Thread(
                target=self._authenticate_in_background,
                args=(username, password, loading_dialog, callback, parent_window),
                daemon=True,
            )
            thread.start()

        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error showing login dialog: {e}",
                exc_info=True,
            )
            extract_error_context(e, "Instagram", "login dialog", "")
            self.error_handler.handle_exception(
                e, "Showing Instagram login dialog", "Instagram"
            )
            self._handle_auth_failure(callback)

    def _get_instagram_credentials(self, parent_window) -> Optional[tuple[str, str]]:
        """Get Instagram credentials from login dialog.

        Returns:
            Tuple of (username, password) or None if cancelled
        """
        dialog = LoginDialog(
            parent_window,
            error_handler=self.error_handler,
            message_queue=None,
        )
        dialog.wait_window()

        if not dialog.username or not dialog.password:
            return None

        return (dialog.username, dialog.password)

    def _show_loading_dialog(
        self, parent_window, message: str = "Loading..."
    ) -> Optional[object]:
        """Show loading dialog after credentials are entered.

        Args:
            parent_window: Parent window for the dialog
            message: Customizable loading message text

        Returns:
            Loading dialog instance or None
        """
        try:
            dialog = LoadingDialog(
                parent_window,
                message=message,
                timeout=60,
                max_dots=self.config.ui.loading_dialog_max_dots,
                dot_animation_interval=self.config.ui.loading_dialog_animation_interval,
            )
            logger.info(
                f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog created: {message}"
            )
            return dialog
        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error creating loading dialog: {e}",
                exc_info=True,
            )
        return None

    def _authenticate_in_background(
        self,
        username: str,
        password: str,
        loading_dialog: Optional[object],
        callback: Optional[Callable],
        parent_window=None,
    ) -> None:
        """Perform authentication in background thread."""
        try:
            logger.info(
                f"[PLATFORM_DIALOG_COORDINATOR] Auth worker started for user: {username[:3]}***"
            )
            downloader = InstagramDownloader(
                error_handler=self.error_handler, config=self.config
            )
            logger.info(
                "[PLATFORM_DIALOG_COORDINATOR] Calling downloader.authenticate()"
            )
            success = downloader.authenticate(username, password)
            logger.info(
                f"[PLATFORM_DIALOG_COORDINATOR] Authentication result: {success}"
            )

            error_msg = "" if success else "Authentication failed"
            # DO NOT close dialog from background thread - it will crash Tkinter!
            # Schedule UI update on main thread instead
            self._handle_auth_completion(
                success,
                username,
                downloader,
                loading_dialog,
                callback,
                error_msg,
                parent_window,
            )
        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Authentication error: {e}",
                exc_info=True,
            )
            extract_error_context(e, "Instagram", "authentication", "")
            self.error_handler.handle_exception(
                e, "Instagram authentication", "Instagram"
            )
            # Get parent_window from loading_dialog if available
            parent_window = (
                getattr(loading_dialog, "master", None) if loading_dialog else None
            )
            # DO NOT close dialog from background thread - it will crash Tkinter!
            # Schedule UI update on main thread instead
            self._handle_auth_exception(
                username, loading_dialog, callback, e, parent_window
            )

    def _handle_auth_completion(
        self,
        success: bool,
        username: str,
        downloader: InstagramDownloader,
        loading_dialog: Optional[object],
        callback: Optional[Callable],
        error_msg: str,
        parent_window=None,
    ) -> None:
        """Handle authentication completion on main thread."""
        context = "success" if success else "failure"

        def update_ui():
            try:
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Updating UI for {context} path, loading_dialog: {loading_dialog is not None}"
                )

                # Close loading dialog first - CRITICAL
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Closing loading dialog for {context} path"
                )
                self._close_loading_dialog(loading_dialog, error_path=not success)
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog closed for {context} path"
                )

                match success:
                    case True:
                        self.instagram_auth_manager.set_authenticated_downloader(
                            downloader
                        )
                        logger.info(
                            "[PLATFORM_DIALOG_COORDINATOR] Stored authenticated Instagram downloader instance"
                        )
                    case False:
                        self.instagram_auth_manager.set_authenticating(False)
                        logger.info(
                            "[PLATFORM_DIALOG_COORDINATOR] Set authenticating flag to False"
                        )

                self._handle_auth_result(success, username, callback, error_msg)
            except Exception as e:
                logger.error(
                    f"[PLATFORM_DIALOG_COORDINATOR] Error in update_ui for {context} path: {e}",
                    exc_info=True,
                )
                # Still try to close the dialog even if there's an error
                try:
                    self._close_loading_dialog(loading_dialog, error_path=True)
                except Exception as close_error:
                    logger.error(
                        f"[PLATFORM_DIALOG_COORDINATOR] Error closing dialog in error handler: {close_error}",
                        exc_info=True,
                    )

        # Try to execute immediately if we're on main thread, otherwise schedule
        if threading.current_thread() is threading.main_thread():
            logger.info(
                f"[PLATFORM_DIALOG_COORDINATOR] Already on main thread, executing update immediately ({context} path)"
            )
            try:
                update_ui()
            except Exception as e:
                logger.error(
                    f"[PLATFORM_DIALOG_COORDINATOR] Error executing update on main thread: {e}",
                    exc_info=True,
                )
        else:
            self._schedule_ui_update(update_ui, f"{context} path", parent_window)

    def _handle_auth_exception(
        self,
        username: str,
        loading_dialog: Optional[object],
        callback: Optional[Callable],
        error: Exception,
        parent_window=None,
    ) -> None:
        """Handle authentication exception on main thread."""

        def update_ui():
            try:
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Updating UI for exception path, loading_dialog: {loading_dialog is not None}"
                )
                self._close_loading_dialog(loading_dialog, error_path=True)
                logger.info(
                    "[PLATFORM_DIALOG_COORDINATOR] Loading dialog closed for exception path"
                )
                self.instagram_auth_manager.set_authenticating(False)

                # Show user-friendly error message
                user_friendly_msg = "Instagram authentication failed. Please check your username and password, then try again."
                self.error_handler.show_error(
                    "Instagram Authentication Failed", user_friendly_msg
                )

                self._handle_auth_result(False, username, callback, str(error))
            except Exception as e:
                logger.error(
                    f"[PLATFORM_DIALOG_COORDINATOR] Error in exception handler update_ui: {e}",
                    exc_info=True,
                )
                # Still try to close the dialog
                try:
                    self._close_loading_dialog(loading_dialog, error_path=True)
                except Exception as close_error:
                    logger.error(
                        f"[PLATFORM_DIALOG_COORDINATOR] Error closing dialog in exception handler: {close_error}",
                        exc_info=True,
                    )

        self._schedule_ui_update(update_ui, "error path", parent_window)

    def _close_loading_dialog(
        self, dialog: Optional[LoadingDialog], error_path: bool = False
    ) -> None:
        """Close loading dialog using shared utility.

        Args:
            dialog: LoadingDialog instance to close
            error_path: Whether this is an error path (for logging)
        """
        close_loading_dialog(dialog, error_path)

    def _schedule_ui_update(
        self, update_func: Callable, context: str, parent_window=None
    ) -> None:
        """Schedule UI update on main thread using centralized queue from MediaDownloaderApp."""
        if not self.root:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Root window not available, cannot queue update ({context})"
            )
            return

        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Queuing UI update ({context})")

        # Wrap update_func with logging
        def execute_update():
            try:
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Executing UI update ({context})"
                )
                update_func()
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] UI update completed ({context})"
                )
            except Exception as e:
                logger.error(
                    f"[PLATFORM_DIALOG_COORDINATOR] Error executing UI update ({context}): {e}",
                    exc_info=True,
                )

        # Use centralized queue from MediaDownloaderApp (no duplication!)
        # self.root is always MediaDownloaderApp which has run_on_main_thread
        self.root.run_on_main_thread(execute_update)

    def _handle_auth_cancellation(self, callback: Optional[Callable]) -> None:
        """Handle authentication cancellation."""
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Instagram login cancelled")
        self.instagram_auth_manager.set_authenticating(False)
        if callback:
            callback(InstagramAuthStatus.FAILED)
        self.error_handler.show_info("Instagram Login", "Login cancelled")

    def _handle_auth_failure(self, callback: Optional[Callable]) -> None:
        """Handle authentication failure."""
        if self.instagram_auth_manager:
            self.instagram_auth_manager.set_authenticating(False)
        if callback:
            callback(InstagramAuthStatus.FAILED)

    def _handle_auth_result(
        self,
        success: bool,
        username: str,
        callback: Optional[Callable] = None,
        error_message: str = "",
    ) -> None:
        """Handle authentication result on main thread."""
        logger.info(
            f"[PLATFORM_DIALOG_COORDINATOR] _handle_auth_result called: success={success}, callback={callback is not None}"
        )

        match success:
            case True:
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication successful for {username[:3]}***"
                )
                if callback:
                    logger.info(
                        "[PLATFORM_DIALOG_COORDINATOR] Calling callback with AUTHENTICATED status"
                    )
                callback(InstagramAuthStatus.AUTHENTICATED)
                self.error_handler.show_info(
                    "Instagram Login", f"Successfully authenticated as {username}"
                )
            case False:
                logger.warning(
                    f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication failed for {username[:3]}***"
                )
                if callback:
                    logger.info(
                        "[PLATFORM_DIALOG_COORDINATOR] Calling callback with FAILED status"
                    )
                callback(InstagramAuthStatus.FAILED)

                # Show user-friendly error message
                user_friendly_msg = "Instagram authentication failed. Please check your username and password, then try again."
                self.error_handler.show_error(
                    "Instagram Authentication Failed", user_friendly_msg
                )
