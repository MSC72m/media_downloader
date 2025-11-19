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
    def _set_instagram_status(self, status) -> None:
        """Set Instagram authentication status.

        Args:
            status: InstagramAuthStatus enum value
        """
        status_name = status.name if hasattr(status, "name") else str(status)
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

    def refresh_handlers(self):
        """Refresh handler references from container."""
        self._cookie_handler = self.container.get("cookie_handler")
        self._auth_handler = self.container.get("auth_handler")
        self.error_handler = self.container.get("error_handler")
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Handlers refreshed")

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

    # Authentication
    def authenticate_instagram(self, parent_window) -> None:
        """Show Instagram authentication dialog.

        This is the SINGLE SOURCE OF TRUTH for Instagram auth UI updates.
        """
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Authenticating Instagram")

        if not self._auth_handler:
            logger.error("[PLATFORM_DIALOG_COORDINATOR] Auth handler not available")
            return

        self._set_instagram_status(InstagramAuthStatus.LOGGING_IN)

        try:
            self._auth_handler.authenticate_instagram(
                parent_window or self.root,
                lambda success, error_message=None: self._handle_instagram_auth_result(
                    success, error_message
                ),
            )
        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error authenticating Instagram: {e}",
                exc_info=True,
            )
            self._set_instagram_status(InstagramAuthStatus.FAILED)
            if self.error_handler:
                self.error_handler.show_error(
                    "Instagram Authentication Error",
                    f"An error occurred during authentication: {str(e)}",
                )

    def _handle_instagram_auth_result(
        self, success: bool, error_message: Optional[str] = None
    ) -> None:
        """Handle Instagram authentication result.

        Thread-safe: Uses queue-based status bar and error handler.
        """
        status_bar = self.container.get("status_bar")

        if success:
            self._set_instagram_status(InstagramAuthStatus.AUTHENTICATED)
            if status_bar:
                status_bar.show_message("Instagram authenticated successfully")
            return

        self._set_instagram_status(InstagramAuthStatus.FAILED)
        if error_message and self.error_handler:
            self.error_handler.show_error("Instagram Authentication", error_message)
        elif status_bar:
            status_bar.show_error("Instagram authentication failed")
