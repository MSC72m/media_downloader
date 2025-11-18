"""Platform Dialog Coordinator - Handles platform-specific UI dialogs."""

import os
from typing import Optional

from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.models import Download
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PlatformDialogCoordinator:
    """Coordinates platform-specific UI dialogs - delegates to platform handlers."""

    def __init__(self, container, root_window):
        """Initialize with service container and root window."""
        self.container = container
        self.root = root_window
        self._cookie_handler = None
        self._auth_handler = None
        self.error_handler = None

    # Instagram Authentication State Management
    def _set_instagram_status(self, status, status_name: str) -> None:
        """Set Instagram authentication status.

        Args:
            status: InstagramAuthStatus enum value
            status_name: Human-readable status name for logging
        """
        options_bar = self.container.get("options_bar")
        if not options_bar:
            logger.warning(
                f"[PLATFORM_DIALOG_COORDINATOR] Options bar not available: {status_name}"
            )
            return

        try:
            options_bar.set_instagram_status(status)
        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error setting Instagram {status_name} state: {e}"
            )

    def _set_instagram_logging_in(self) -> None:
        """Set Instagram authentication state to logging in."""
        from src.core.enums.instagram_auth_status import InstagramAuthStatus

        self._set_instagram_status(InstagramAuthStatus.LOGGING_IN, "LOGGING_IN")

    def _set_instagram_authenticated(self) -> None:
        """Set Instagram authentication state to authenticated."""
        from src.core.enums.instagram_auth_status import InstagramAuthStatus

        self._set_instagram_status(InstagramAuthStatus.AUTHENTICATED, "AUTHENTICATED")

    def _set_instagram_failed(self) -> None:
        """Set Instagram authentication state to failed."""
        from src.core.enums.instagram_auth_status import InstagramAuthStatus

        self._set_instagram_status(InstagramAuthStatus.FAILED, "FAILED")

    def refresh_handlers(self):
        """Refresh handler references from container."""
        self._cookie_handler = self.container.get("cookie_handler")
        self._auth_handler = self.container.get("auth_handler")
        self.error_handler = self.container.get("error_handler")
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Handlers refreshed")

    # YouTube Dialog
    def show_youtube_dialog(self, url: str, on_download_callback) -> None:
        """Show YouTube download dialog - uses youtube_handler."""
        logger.info(f"[PLATFORM_DIALOG_COORDINATOR] Showing YouTube dialog for: {url}")

        try:
            from src.ui.dialogs.browser_cookie_dialog import BrowserCookieDialog
            from src.ui.dialogs.youtube_downloader_dialog import (
                YouTubeDownloaderDialog,
            )

            metadata_service = self.container.get("youtube_metadata")

            def on_cookie_selected(cookie_path: Optional[str], browser: Optional[str]):
                """Handle cookie selection."""
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Cookie selected: {cookie_path}, browser: {browser}"
                )

                # Validate cookie path
                if cookie_path and self._cookie_handler:
                    success = self._cookie_handler.set_cookie_file(cookie_path)
                    if not success:
                        logger.error(
                            f"[PLATFORM_DIALOG_COORDINATOR] Failed to set cookie file: {cookie_path}"
                        )

                # Show YouTube downloader dialog
                def create_youtube_dialog():
                    try:
                        YouTubeDownloaderDialog(
                            self.root,
                            url=url,
                            cookie_handler=self._cookie_handler,
                            metadata_service=metadata_service,
                            on_download=on_download_callback,
                            pre_fetched_metadata=None,
                            initial_cookie_path=cookie_path,
                            initial_browser=browser,
                        )
                        logger.info(
                            "[PLATFORM_DIALOG_COORDINATOR] YouTubeDownloaderDialog created"
                        )
                    except Exception as e:
                        logger.error(
                            f"[PLATFORM_DIALOG_COORDINATOR] Failed to create YouTube dialog: {e}",
                            exc_info=True,
                        )
                        if self.error_handler:
                            self.error_handler.show_error(
                                "YouTube Dialog Error",
                                f"Failed to create YouTube dialog: {str(e)}",
                            )

                if hasattr(self.root, "after"):
                    self.root.after(0, create_youtube_dialog)
                else:
                    create_youtube_dialog()

            # Show cookie selection dialog first
            def create_cookie_dialog():
                try:
                    BrowserCookieDialog(self.root, on_cookie_selected)
                    logger.info(
                        "[PLATFORM_DIALOG_COORDINATOR] BrowserCookieDialog created"
                    )
                except Exception as e:
                    logger.error(
                        f"[PLATFORM_DIALOG_COORDINATOR] Failed to create cookie dialog: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        self.error_handler.show_error(
                            "Cookie Dialog Error",
                            f"Failed to show cookie selector: {str(e)}",
                        )
                    # Fallback: show YouTube dialog without cookies
                    on_cookie_selected(None, None)

            if hasattr(self.root, "after"):
                self.root.after(0, create_cookie_dialog)
            else:
                create_cookie_dialog()

        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error showing YouTube dialog: {e}",
                exc_info=True,
            )
            if self.error_handler:
                self.error_handler.show_error(
                    "YouTube Error", f"Failed to show YouTube dialog: {str(e)}"
                )

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

    # Authentication
    def authenticate_instagram(self, parent_window) -> None:
        """Show Instagram authentication dialog.

        This is the SINGLE SOURCE OF TRUTH for Instagram auth UI updates.
        """
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Authenticating Instagram")

        if not self._auth_handler:
            logger.error("[PLATFORM_DIALOG_COORDINATOR] Auth handler not available")
            # Failsafe: Reset button state directly if UI state manager not available
            self._reset_instagram_button_state()
            return

        # Set to logging in state BEFORE calling auth - use UI state manager
        try:
            # Set button to "Logging in..." state
            self._set_instagram_logging_in()
            logger.info(
                "[PLATFORM_DIALOG_COORDINATOR] Instagram state set to LOGGING_IN"
            )
        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error setting Instagram logging in state: {e}"
            )
            self._set_instagram_button_direct(InstagramAuthStatus.LOGGING_IN)

        try:

            def on_auth_complete(success: bool, error_message: Optional[str] = None):
                """Handle authentication completion - SINGLE PLACE for all UI updates."""
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Auth complete: success={success}, error={error_message}"
                )

                # Always use thread-safe UI updates by scheduling in main thread
                def update_ui_thread_safe():
                    try:
                        if success:
                            # SUCCESS PATH - Update state and status bar
                            try:
                                self._set_instagram_authenticated()
                                logger.info(
                                    "[PLATFORM_DIALOG_COORDINATOR] State set to AUTHENTICATED"
                                )
                            except Exception as e:
                                logger.error(
                                    f"[PLATFORM_DIALOG_COORDINATOR] Error setting Instagram authenticated state: {e}"
                                )
                                self._reset_instagram_button_state()

                            # Update status bar
                            status_bar = self.container.get("status_bar")
                            if status_bar:
                                status_bar.show_message(
                                    "Instagram authenticated successfully"
                                )
                        else:
                            # FAILURE PATH - Update state and status bar only (no error dialogs)
                            try:
                                self._set_instagram_failed()
                                logger.info(
                                    "[PLATFORM_DIALOG_COORDINATOR] State set to FAILED"
                                )
                            except Exception as e:
                                logger.error(
                                    f"[PLATFORM_DIALOG_COORDINATOR] Error setting Instagram failed state: {e}"
                                )
                                self._reset_instagram_button_state()

                            # Update status bar with failure message (no error dialogs)
                            failure_message = f"Instagram authentication failed"
                            if error_message:
                                failure_message += f": {error_message}"
                            status_bar = self.container.get("status_bar")
                            if status_bar:
                                status_bar.show_error(failure_message)

                        logger.info(
                            "[PLATFORM_DIALOG_COORDINATOR] UI update completed successfully"
                        )
                    except Exception as ui_error:
                        logger.error(
                            f"[PLATFORM_DIALOG_COORDINATOR] Error in thread-safe UI update: {ui_error}",
                            exc_info=True,
                        )

                # Try safe UI update with comprehensive error handling
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] *** TRYING SAFE UI UPDATE *** root exists: {hasattr(self.root, 'after_idle')}"
                )
                try:
                    update_ui_thread_safe()
                    logger.info(
                        f"[PLATFORM_DIALOG_COORDINATOR] *** UI UPDATE COMPLETED SUCCESSFULLY ***"
                    )
                except Exception as direct_error:
                    logger.error(
                        f"[PLATFORM_DIALOG_COORDINATOR] Direct UI update failed: {direct_error}",
                        exc_info=True,
                    )

                    # Don't crash - just log the error and continue
                    # The status update will have been handled by the callback itself
                    logger.warning(
                        "[PLATFORM_DIALOG_COORDINATOR] Continuing after UI update failure - no crash"
                    )

            self._auth_handler.authenticate_instagram(
                parent_window or self.root, on_auth_complete
            )

        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error authenticating Instagram: {e}",
                exc_info=True,
            )
            # EXCEPTION PATH - Reset state and show error
            # FAILURE PATH - Update state and status bar only (no error dialogs)
            try:
                self._set_instagram_failed()
                logger.info("[PLATFORM_DIALOG_COORDINATOR] State set to FAILED")
            except Exception as reset_error:
                logger.error(
                    f"[PLATFORM_DIALOG_COORDINATOR] Error resetting Instagram state: {reset_error}"
                )
                self._reset_instagram_button_state()

            if self.error_handler:
                self.error_handler.show_error(
                    "Instagram Authentication Error",
                    f"An error occurred during authentication: {str(e)}",
                )

            # Update status bar
            status_bar = self.container.get("status_bar")
            if status_bar:
                status_bar.show_error("Instagram authentication error")

    def _reset_instagram_button_state(self) -> None:
        """Failsafe method to reset Instagram button directly when component_state not available."""
        try:
            from src.core.enums.instagram_auth_status import InstagramAuthStatus

            options_bar = self.container.get("options_bar")
            if options_bar:
                options_bar.set_instagram_status(InstagramAuthStatus.FAILED)
                logger.info(
                    "[PLATFORM_DIALOG_COORDINATOR] Instagram button reset directly to FAILED"
                )
            else:
                logger.error(
                    "[PLATFORM_DIALOG_COORDINATOR] Options bar not available for reset"
                )
        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error resetting button: {e}")

    def _set_instagram_button_direct(self, status) -> None:
        """Failsafe method to set Instagram button state directly when component_state not available."""
        try:
            options_bar = self.container.get("options_bar")
            if options_bar:
                options_bar.set_instagram_status(status)
                logger.info(
                    f"[PLATFORM_DIALOG_COORDINATOR] Instagram button set directly to {status}"
                )
            else:
                logger.error("[PLATFORM_DIALOG_COORDINATOR] Options bar not available")
        except Exception as e:
            logger.error(f"[PLATFORM_DIALOG_COORDINATOR] Error setting button: {e}")
