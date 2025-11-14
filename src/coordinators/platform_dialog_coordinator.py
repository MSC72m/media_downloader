"""Platform Dialog Coordinator - Handles platform-specific UI dialogs."""

import os
from typing import Optional

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

    def refresh_handlers(self):
        """Refresh handler references from container."""
        self._cookie_handler = self.container.get("cookie_handler")
        self._auth_handler = self.container.get("auth_handler")
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
        """Show Instagram authentication dialog."""
        logger.info("[PLATFORM_DIALOG_COORDINATOR] Authenticating Instagram")

        if not self._auth_handler:
            logger.error("[PLATFORM_DIALOG_COORDINATOR] Auth handler not available")
            return

        try:

            def on_auth_complete(success: bool):
                if success:
                    logger.info(
                        "[PLATFORM_DIALOG_COORDINATOR] Instagram authentication successful"
                    )
                else:
                    logger.warning(
                        "[PLATFORM_DIALOG_COORDINATOR] Instagram authentication failed"
                    )

            self._auth_handler.authenticate_instagram(
                parent_window or self.root, on_auth_complete
            )

        except Exception as e:
            logger.error(
                f"[PLATFORM_DIALOG_COORDINATOR] Error authenticating Instagram: {e}",
                exc_info=True,
            )
