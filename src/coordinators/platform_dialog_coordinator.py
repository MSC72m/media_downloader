"""Platform Dialog Coordinator - SOLID polymorphic dialog handling."""

import os
import threading
from abc import ABC, abstractmethod
from functools import partial
from typing import Callable, Optional

from src.core.config import AppConfig, get_config
from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.models import Download
from src.interfaces.service_interfaces import ICookieHandler, IErrorHandler
from src.services.instagram.auth_manager import InstagramAuthManager
from src.services.instagram.downloader import InstagramDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.ui.components.loading_dialog import LoadingDialog
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
        instagram_auth_manager: Optional[InstagramAuthManager] = None,
        orchestrator=None,
        config: AppConfig = get_config()
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
        """Start Instagram authentication flow.
        
        Args:
            parent_window: Parent window for dialogs
            callback: Optional callback for auth status updates (receives InstagramAuthStatus)
        """
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Starting Instagram authentication")

        if not self.instagram_auth_manager:
            logger.error("[PLATFORM_DIALOG_COORDINATOR] Instagram auth manager not available")
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
            loading_dialog = self._show_loading_dialog(parent_window, "Authenticating with Instagram...")
            
            thread = threading.Thread(
                target=self._authenticate_in_background,
                args=(username, password, loading_dialog, callback),
                daemon=True
            )
            thread.start()

        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error showing login dialog: {e}", exc_info=True)
            extract_error_context(e, "Instagram", "login dialog", "")
            self.error_handler.handle_exception(e, "Showing Instagram login dialog", "Instagram")
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

    def _show_loading_dialog(self, parent_window, message: str = "Loading...") -> Optional[object]:
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
                dot_animation_interval=self.config.ui.loading_dialog_animation_interval
            )
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog created: {message}")
            return dialog
        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error creating loading dialog: {e}", exc_info=True)
            return None

    def _authenticate_in_background(
        self,
        username: str,
        password: str,
        loading_dialog: Optional[object],
        callback: Optional[Callable]
    ) -> None:
        """Perform authentication in background thread."""
        try:
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Auth worker started for user: {username[:3]}***")
            downloader = InstagramDownloader(error_handler=self.error_handler, config=self.config)
            logger.info("[PLATFORM_DIALOG_COORDINATOR] Calling downloader.authenticate()")
            success = downloader.authenticate(username, password)
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Authentication result: {success}")
            
            error_msg = "" if success else "Authentication failed"
            self._handle_auth_completion(success, username, downloader, loading_dialog, callback, error_msg)
        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Authentication error: {e}", exc_info=True)
            extract_error_context(e, "Instagram", "authentication", "")
            self.error_handler.handle_exception(e, "Instagram authentication", "Instagram")
            self._handle_auth_exception(username, loading_dialog, callback, e)

    def _handle_auth_completion(
        self,
        success: bool,
        username: str,
        downloader: InstagramDownloader,
        loading_dialog: Optional[object],
        callback: Optional[Callable],
        error_msg: str
    ) -> None:
        """Handle authentication completion on main thread."""
        context = "success" if success else "failure"
        
        def update_ui():
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Updating UI for {context} path, loading_dialog: {loading_dialog is not None}")
            
            # Close loading dialog first
            self._close_loading_dialog(loading_dialog, error_path=not success)
            
            match success:
                case True:
                    self.instagram_auth_manager.set_authenticated_downloader(downloader)
                    logger.info("[PLATFORM_DIALOG_COORDINATOR] Stored authenticated Instagram downloader instance")
                case False:
                    self.instagram_auth_manager.set_authenticating(False)
            
            self._handle_auth_result(success, username, callback, error_msg)

        self._schedule_ui_update(update_ui, f"{context} path")

    def _handle_auth_exception(
        self,
        username: str,
        loading_dialog: Optional[object],
        callback: Optional[Callable],
        error: Exception
    ) -> None:
        """Handle authentication exception on main thread."""
        def update_ui():
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Updating UI for exception path, loading_dialog: {loading_dialog is not None}")
            self._close_loading_dialog(loading_dialog, error_path=True)
            self.instagram_auth_manager.set_authenticating(False)
            
            # Show user-friendly error message
            user_friendly_msg = "Instagram authentication failed. Please check your username and password, then try again."
            self.error_handler.show_error("Instagram Authentication Failed", user_friendly_msg)
            
            self._handle_auth_result(False, username, callback, str(error))

        self._schedule_ui_update(update_ui, "error path")

    def _close_loading_dialog(self, dialog: Optional[object], error_path: bool = False) -> None:
        """Close loading dialog with robust error handling using finally blocks.
        
        Args:
            dialog: Loading dialog instance to close
            error_path: Whether this is an error path (for logging)
        """
        path_suffix = " (error path)" if error_path else ""
        
        if not dialog:
            logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] No loading dialog to close{path_suffix}")
            return

        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Attempting to close loading dialog{path_suffix}, dialog type: {type(dialog).__name__}")

        # Use finally block to ensure cleanup always happens
        try:
            # Check if dialog still exists
            if hasattr(dialog, 'winfo_exists'):
                if not dialog.winfo_exists():
                    logger.debug(f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog already destroyed{path_suffix}")
                    return

            # Try close() first - this should release grab and destroy properly
            if hasattr(dialog, 'close'):
                try:
                    dialog.close()
                    logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog closed via close(){path_suffix}")
                    # Give it a moment to process
                    if hasattr(dialog, 'update_idletasks'):
                        dialog.update_idletasks()
                    # Verify it's actually closed
                    if hasattr(dialog, 'winfo_exists') and not dialog.winfo_exists():
                        return
                    # If still exists, fall through to destroy()
                except Exception as close_error:
                    logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] close() failed{path_suffix}: {close_error}")
                    # Fall through to destroy()

            # Fallback to destroy() if close() doesn't exist or failed
            if hasattr(dialog, 'destroy'):
                dialog.destroy()
                logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog destroyed via destroy(){path_suffix}")

        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error closing loading dialog{path_suffix}: {e}", exc_info=True)
        finally:
            # Ensure dialog is always cleaned up in finally block - always try to destroy
            try:
                if hasattr(dialog, 'winfo_exists'):
                    if dialog.winfo_exists():
                        if hasattr(dialog, 'destroy'):
                            dialog.destroy()
                            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog force-destroyed in finally block{path_suffix}")
                elif hasattr(dialog, 'destroy'):
                    # No winfo_exists, try destroy anyway as safety measure
                    try:
                        dialog.destroy()
                        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Loading dialog force-destroyed in finally block (no winfo_exists){path_suffix}")
                    except Exception:
                        # Already destroyed or error - ignore
                        pass
            except Exception as final_error:
                logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error in finally block{path_suffix}: {final_error}", exc_info=True)

    def _schedule_ui_update(self, update_func: Callable, context: str) -> None:
        """Schedule UI update on main thread or execute immediately."""
        if not self.root:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Root window not available, calling update directly ({context})")
            update_func()
            return

        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Scheduling UI update on main thread ({context})")
        # Use after_idle to ensure it runs after all pending events
        self.root.after_idle(update_func)

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
        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] _handle_auth_result called: success={success}, callback={callback is not None}")
        
        match success:
            case True:
                logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication successful for {username[:3]}***")
                if callback:
                    logger.info("[PLATFORM_DIALOG_COORDINATOR] Calling callback with AUTHENTICATED status")
                    callback(InstagramAuthStatus.AUTHENTICATED)
                self.error_handler.show_info("Instagram Login", f"Successfully authenticated as {username}")
            case False:
                logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication failed for {username[:3]}***")
                if callback:
                    logger.info("[PLATFORM_DIALOG_COORDINATOR] Calling callback with FAILED status")
                    callback(InstagramAuthStatus.FAILED)
                
                # Show user-friendly error message
                user_friendly_msg = "Instagram authentication failed. Please check your username and password, then try again."
                self.error_handler.show_error("Instagram Authentication Failed", user_friendly_msg)

    