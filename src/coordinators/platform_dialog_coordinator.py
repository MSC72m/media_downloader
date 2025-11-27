"""Platform Dialog Coordinator - Handles platform-specific UI dialogs with clean DI."""

import os
from typing import Optional

from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.interfaces import ICookieHandler, IErrorHandler
from src.core.models import Download
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PlatformDialogCoordinator:
    """Coordinates platform-specific UI dialogs - delegates to platform handlers."""

    def __init__(self, root_window, error_handler: IErrorHandler,
                 cookie_handler: Optional[ICookieHandler] = None,
                 orchestrator=None):
        """Initialize with proper dependency injection."""
        self.root = root_window
        self.error_handler = error_handler
        self.cookie_handler = cookie_handler
        self.orchestrator = orchestrator

    
    
    # YouTube Dialog
    def show_youtube_dialog(self, url: str, on_download_callback) -> None:
        """Show YouTube download dialog.

        Note: YouTube handler already handles the full dialog flow.
        This is just a stub for compatibility.
        """
        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] YouTube dialog called for: {url}")
        logger.warning(
            "[PLATFORM_DIALOG_COORDINATOR] YouTube handler should handle dialogs directly, not coordinator"
        )

        # The YouTube handler already creates and manages the dialog
        # This shouldn't be called directly - kept for compatibility only
        pass

    # Twitter Dialog
    def show_twitter_dialog(self, url: str, on_download_callback) -> None:
        """Show Twitter download dialog - uses twitter_handler."""
        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Showing Twitter dialog for: {url}")

        # TODO: Implement Twitter dialog
        logger.warning(
            "[PLATFORM_DIALOG_COORDINATOR] Twitter dialog not yet implemented"
        )

        # Fallback to generic download
        download = Download(
            url=url,
            name=os.path.basename(url) or "twitter_download",
            service_type="twitter",
        )
        on_download_callback(download)

    # Instagram Dialog
    def show_instagram_dialog(self, url: str, on_download_callback) -> None:
        """Show Instagram download dialog - uses instagram_handler."""
        logger.info(
            f"[PLATFORM_DIALOG_COORDINATOR] Showing Instagram dialog for: {url}"
        )

        # TODO: Implement Instagram dialog
        logger.warning(
            "[PLATFORM_DIALOG_COORDINATOR] Instagram dialog not yet implemented"
        )

        # Fallback to generic download
        download = Download(
            url=url,
            name=os.path.basename(url) or "instagram_download",
            service_type="instagram",
        )
        on_download_callback(download)

    # Pinterest Dialog
    def show_pinterest_dialog(self, url: str, on_download_callback) -> None:
        """Show Pinterest download dialog - uses pinterest_handler."""
        logger.info(
            f"[PLATFORM_DIALOG_COORDINATOR] Showing Pinterest dialog for: {url}"
        )

        # TODO: Implement Pinterest dialog
        logger.warning(
            "[PLATFORM_DIALOG_COORDINATOR] Pinterest dialog not yet implemented"
        )

        # Fallback to generic download
        download = Download(
            url=url,
            name=os.path.basename(url) or "pinterest_download",
            service_type="pinterest",
        )
        on_download_callback(download)

    # SoundCloud Dialog
    def show_soundcloud_dialog(self, url: str, on_download_callback) -> None:
        """Show SoundCloud download dialog - uses soundcloud_handler."""
        logger.info(
            f"[PLATFORM_DIALOG_COORDINATOR] Showing SoundCloud dialog for: {url}"
        )

        try:
            # For now, use simple generic download
            # TODO: Create dedicated SoundCloud dialog with audio quality options
            from src.services.soundcloud.downloader import SoundCloudDownloader

            # Get track info for better naming and premium check
            downloader = SoundCloudDownloader()
            info = downloader.get_info(url)

            if info:
                # Check if track is premium/Go+ only
                if downloader._is_premium_track(info):
                    error_msg = (
                        "This SoundCloud track requires a Go+ subscription.\n\n"
                        "Premium tracks cannot be downloaded without a paid subscription."
                    )
                    logger.warning(
                        f"[PLATFORM_DIALOG_COORDINATOR] Premium SoundCloud track rejected: {url}"
                    )
                    if self.error_handler:
                        self.error_handler.show_error(
                            "SoundCloud Go+ Required", error_msg
                        )
                    return

                # Create download with proper name
                track_name = (
                    f"{info.get('artist', 'Unknown')} - {info.get('title', 'Unknown')}"
                )
                download = Download(
                    url=url,
                    name=track_name,
                    service_type="soundcloud",
                )
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] SoundCloud track info retrieved: {track_name}"
                )
            else:
                # Fallback if info retrieval fails
                download = Download(
                    url=url,
                    name=os.path.basename(url) or "soundcloud_download",
                    service_type="soundcloud",
                )
                logger.warning(
                    "[PLATFORM_DIALOG_COORDINATOR] Could not retrieve SoundCloud track info"
                )

            on_download_callback(download)
            logger.info("[PLATFORM_DIALOG_COORDINATOR] SoundCloud download added")

        except Exception as e:
            error_str = str(e).lower()

            # Check for premium/subscription errors
            if any(
                keyword in error_str
                for keyword in ["premium", "go+", "subscription", "not available"]
            ):
                error_msg = (
                    "This SoundCloud track requires a Go+ subscription.\n\n"
                    "Premium tracks cannot be downloaded without a paid subscription."
                )
                logger.error(
                    f"[PLATFORM_DIALOG_COORDINATOR] Premium SoundCloud track error: {e}"
                )
                if self.error_handler:
                    self.error_handler.show_error("SoundCloud Go+ Required", error_msg)
                return

            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error showing SoundCloud dialog: {e}",
                exc_info=True,
            )
            # Show error via centralized error handler
            if self.error_handler:
                self.error_handler.show_error(
                    "SoundCloud Error", f"Failed to process SoundCloud URL: {str(e)}"
                )
            # Don't add to download list on error - just show error dialog

    # Generic Download
    def generic_download(
        self, url: str, name: Optional[str], on_download_callback
    ) -> None:
        """Generic download (no platform-specific dialog)."""
        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Generic download: {url}")

        try:
            # Create a simple download object
            download = Download(
                url=url,
                name=name or os.path.basename(url) or "download",
                service_type="generic",
            )

            # Call the download callback directly
            on_download_callback(download)
            logger.info("[PLATFORM_DIALOG_COORDINATOR] Generic download handled")

        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error handling generic download: {e}",
                exc_info=True,
            )

    # Authentication - Restored full authentication flow
    def authenticate_instagram(self, parent_window, callback=None) -> None:
        """Show Instagram authentication dialog with full login flow.
        
        Args:
            parent_window: Parent window for dialogs
            callback: Optional callback to update button state (receives InstagramAuthStatus)
        """
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Starting Instagram authentication")

        # Get options bar to update button state
        options_bar = self._get_options_bar(parent_window)
        
        # Update button to logging in state
        if options_bar:
            from src.core.enums.instagram_auth_status import InstagramAuthStatus
            options_bar.set_instagram_status(InstagramAuthStatus.LOGGING_IN)
        elif callback:
            # Use callback if options_bar not available
            from src.core.enums.instagram_auth_status import InstagramAuthStatus
            callback(InstagramAuthStatus.LOGGING_IN)

        try:
            from src.services.instagram.downloader import InstagramDownloader
            from src.ui.dialogs.login_dialog import LoginDialog

            # Create login dialog
            logger.info("[PLATFORM_DIALOG_COORDINATOR] Creating login dialog")
            dialog = LoginDialog(parent_window)
            dialog.wait_window()
            logger.info("[PLATFORM_DIALOG_COORDINATOR] Login dialog closed")

            # Check if user provided credentials
            if not dialog.username or not dialog.password:
                logger.info("[PLATFORM_DIALOG_COORDINATOR] Instagram login cancelled by user")
                # Reset button state
                from src.core.enums.instagram_auth_status import InstagramAuthStatus
                if options_bar:
                    options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
                elif callback:
                    callback(InstagramAuthStatus.FAILED)
                if self.error_handler:
                    self.error_handler.show_info("Instagram Login", "Login cancelled")
                return

            # Start authentication in background thread
            username = dialog.username
            password = dialog.password
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Starting authentication for user: {username[:3]}***")

            def auth_worker():
                """Background thread worker for authentication."""
                try:
                    downloader = InstagramDownloader()
                    success = downloader.authenticate(username, password)
                    error_msg = "" if success else "Authentication failed"

                    # Update UI on main thread - capture variables in closure
                    def update_ui():
                        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Calling _handle_auth_result: success={success}")
                        self._handle_auth_result(success, username, options_bar, callback, error_msg)
                    
                    self.root.after(0, update_ui)
                except Exception as e:
                    logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Authentication error: {e}", exc_info=True)
                    error_msg = str(e)

                    # Update UI on main thread - capture error in closure
                    def update_ui_error():
                        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Calling _handle_auth_result with error: {error_msg}")
                        self._handle_auth_result(False, username, options_bar, callback, error_msg)
                    
                    self.root.after(0, update_ui_error)

            import threading
            thread = threading.Thread(target=auth_worker, daemon=True)
            thread.start()
            logger.info("[PLATFORM_DIALOG_COORDINATOR] Authentication thread started")

        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error showing login dialog: {e}", exc_info=True)
            # Reset button state on error
            from src.core.enums.instagram_auth_status import InstagramAuthStatus
            if options_bar:
                options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
            elif callback:
                callback(InstagramAuthStatus.FAILED)

            if self.error_handler:
                self.error_handler.show_error("Instagram Login Error", f"Failed to show login dialog: {str(e)}")

    def _get_options_bar(self, parent_window):
        """Get options bar from parent window or orchestrator."""
        try:
            # Try to find options bar in the window hierarchy
            if hasattr(parent_window, 'options_bar'):
                return parent_window.options_bar
            # Try to get from orchestrator if available
            if self.orchestrator:
                ui_components = getattr(self.orchestrator, 'ui_components', {})
                return ui_components.get('options_bar')
            # Fallback: try parent window's orchestrator
            if hasattr(parent_window, 'orchestrator'):
                ui_components = getattr(parent_window.orchestrator, 'ui_components', {})
                return ui_components.get('options_bar')
        except Exception as e:
            logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] Could not get options bar: {e}")
        return None

    def _handle_auth_result(self, success: bool, username: str, options_bar, callback=None, error_message: str = "") -> None:
        """Handle authentication result on main thread."""
        
        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] _handle_auth_result called: success={success}, username={username[:3]}***, has_options_bar={options_bar is not None}, has_callback={callback is not None}")
        
        if success:
            logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication successful for {username[:3]}***")
            # Update button to authenticated state
            if options_bar:
                logger.info("[PLATFORM_DIALOG_COORDINATOR] Updating options_bar to AUTHENTICATED")
                options_bar.set_instagram_status(InstagramAuthStatus.AUTHENTICATED)
            elif callback:
                logger.info("[PLATFORM_DIALOG_COORDINATOR] Calling callback with AUTHENTICATED")
                callback(InstagramAuthStatus.AUTHENTICATED)
            if self.error_handler:
                self.error_handler.show_info("Instagram Login", f"Successfully authenticated as {username}")
        else:
            logger.warning(f"[PLATFORM_DIALOG_COORDINATOR] Instagram authentication failed for {username[:3]}***")
            # Update button to failed state
            if options_bar:
                logger.info("[PLATFORM_DIALOG_COORDINATOR] Updating options_bar to FAILED")
                options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
            elif callback:
                logger.info("[PLATFORM_DIALOG_COORDINATOR] Calling callback with FAILED")
                callback(InstagramAuthStatus.FAILED)
            error_msg = error_message or "Invalid credentials or authentication failed"
            if self.error_handler:
                self.error_handler.show_error("Instagram Login Failed", error_msg)

    