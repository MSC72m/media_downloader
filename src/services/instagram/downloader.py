import os
from collections.abc import Callable
from urllib.parse import urlparse

import instaloader

from src.core.config import AppConfig, get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from src.services.instagram.session_provider import InstagramSessionProvider

from ...core.enums import ServiceType
from ...utils.logger import get_logger
from ..file.service import FileService
from ..network.checker import check_site_connection

logger = get_logger(__name__)

# Instaloader exception type names that indicate authentication is required.
# Matched by name so the check works even when ``instaloader`` is patched/mocked.
_AUTH_REQUIRED_ERROR_NAMES = frozenset(
    {
        "LoginRequiredException",
        "LoginException",
        "PrivateProfileNotFollowedException",
        "QueryReturnedForbiddenException",
        "TwoFactorAuthRequiredException",
    }
)

# Actionable guidance shown when a post cannot be fetched without login.
INSTAGRAM_AUTH_REQUIRED_MESSAGE = (
    "Instagram requires you to be logged in for this content. "
    "Media Downloader no longer uses username/password login (Instagram blocks it). "
    "Instead, either:\n"
    "  1. Log in to Instagram in your browser (Chrome/Firefox/Edge), then retry — "
    "your session cookies are imported automatically, or\n"
    "  2. Run `instaloader --login=YOUR_USERNAME` and copy the generated "
    "`session-YOUR_USERNAME` file into the `instagram` folder of the app's cookie "
    "storage directory."
)


class InstagramDownloader(BaseDownloader):
    """Instagram downloader using session/cookie-based authentication.

    Authentication no longer uses a username/password (Instagram blocks scripted
    logins with 401/checkpoint). Instead an authenticated Instaloader session is
    established from saved session files or cookies imported from the user's
    logged-in browser, via :class:`InstagramSessionProvider`. Public posts still
    resolve anonymously; private/gated content fails with a clear, actionable
    message.
    """

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config: AppConfig = get_config(),
        session_provider: InstagramSessionProvider | None = None,
    ) -> None:
        """Initialize Instagram downloader.

        Args:
            error_handler: Optional error handler for user notifications
            file_service: Optional file service for file operations
            config: AppConfig instance (defaults to global app config)
            session_provider: Optional session provider (defaults to a new one)
        """
        super().__init__(error_handler, file_service, config)
        self.loader = None
        self.authenticated = False
        self.file_service = file_service or FileService()
        self.session_provider = session_provider or InstagramSessionProvider(config=self.config)

    def _create_loader(self) -> instaloader.Instaloader:
        """Create a configured Instaloader instance."""
        return instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            quiet=True,
            user_agent=self.config.network.cookie_user_agent,
            request_timeout=self.config.instagram.default_timeout,
            max_connection_attempts=self.config.instagram.max_login_attempts,
        )

    def authenticate(self, username: str | None = None, password: str | None = None) -> bool:
        """Establish an authenticated Instagram session (no password).

        Username/password are accepted for backward compatibility but ignored:
        Instagram blocks scripted credential logins. A session is instead loaded
        from a saved session file or imported from the user's logged-in browser.

        Args:
            username: Ignored (retained for backward compatibility).
            password: Ignored (retained for backward compatibility).

        Returns:
            True when an authenticated session was established, False otherwise.
        """
        if password:
            logger.info(
                "[INSTAGRAM_DOWNLOADER] Ignoring supplied password; using session/cookie auth"
            )

        connected, error_msg = check_site_connection(ServiceType.INSTAGRAM)
        if not connected:
            logger.error(f"Cannot authenticate with Instagram: {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Instagram", "authentication", error_msg or "Connection failed", ""
                )
            return False

        return self._ensure_session()

    def _ensure_session(self) -> bool:
        """Ensure a loader exists and try to attach an authenticated session.

        Returns:
            True if the loader is authenticated, False if only anonymous access
            is available.
        """
        if not self.loader:
            logger.info("[INSTAGRAM_DOWNLOADER] Creating Instaloader instance")
            self.loader = self._create_loader()

        if self.authenticated:
            return True

        try:
            if username := self.session_provider.load_session(self.loader):
                self.authenticated = True
                logger.info(
                    "[INSTAGRAM_DOWNLOADER] ✅ Authenticated as %s*** via session/cookies",
                    username[:3],
                )
                return True
        except Exception as e:
            logger.error(f"[INSTAGRAM_DOWNLOADER] Session load failed: {e}")
            if self.error_handler:
                self.error_handler.handle_exception(e, "Instagram authentication", "Instagram")

        logger.info("[INSTAGRAM_DOWNLOADER] No session/cookies available; anonymous access only")
        return False

    @staticmethod
    def _is_auth_required_error(exc: Exception) -> bool:
        """Detect whether an exception indicates Instagram login is required."""
        if type(exc).__name__ in _AUTH_REQUIRED_ERROR_NAMES:
            return True
        message = str(exc).lower()
        return "login" in message and ("required" in message or "log in" in message)

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """
        Download media from Instagram URLs.

        Args:
            url: Instagram URL to download from
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        try:
            connected, error_msg = check_site_connection(ServiceType.INSTAGRAM)
            if not connected:
                logger.error(f"Cannot download from Instagram: {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram", "download", error_msg or "Connection failed", url
                    )
                return False

            # Ensure a loader exists and attempt session/cookie auth on demand.
            # Anonymous access still works for public posts if no session found.
            self._ensure_session()

            # Parse URL to determine content type
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) < 2:
                error_msg = "Invalid Instagram URL format"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram", "download", error_msg, url
                    )
                return False

            content_type = path_parts[0]
            shortcode = path_parts[1]

            # Use set for O(1) membership check instead of O(n) list check
            post_content_types = {"p", "reel"}
            if content_type in post_content_types:
                return self._download_post(shortcode, save_path, progress_callback)

            error_msg = f"Unsupported Instagram content type: {content_type}"
            logger.error(error_msg)
            if self.error_handler:
                self.error_handler.handle_service_failure("Instagram", "download", error_msg, url)
            return False

        except Exception as e:
            logger.error(f"Error downloading from Instagram: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Instagram download", "Instagram")
            return False

    def _download_media_from_post(
        self,
        post: instaloader.Post,
        save_dir: str,
        base_name: str,
        file_service: IFileService,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download media files from an Instagram post based on its type.

        Returns True if at least one media file was downloaded successfully.
        """
        if post.is_video:
            if not (video_url := post.video_url):
                logger.error("[INSTAGRAM_DOWNLOADER] No video URL found")
                return False
            filename = self.file_service.sanitize_filename(f"{base_name}.mp4")
            full_path = os.path.join(save_dir, filename)
            return file_service.download_file(video_url, full_path, progress_callback).success

        if post.typename == "GraphSidecar":
            return self._download_sidecar(
                post, save_dir, base_name, file_service, progress_callback
            )

        image_url: str | None = post.url
        if not image_url:
            logger.error("[INSTAGRAM_DOWNLOADER] No image URL found")
            return False
        filename = self.file_service.sanitize_filename(f"{base_name}.jpg")
        full_path = os.path.join(save_dir, filename)
        return file_service.download_file(image_url, full_path, progress_callback).success

    def _download_sidecar(
        self,
        post: instaloader.Post,
        save_dir: str,
        base_name: str,
        file_service: IFileService,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download every carousel item with aggregate, monotonic progress."""
        nodes = list(post.get_sidecar_nodes())
        if not nodes:
            return False

        all_succeeded = True
        total = len(nodes)
        for i, node in enumerate(nodes):
            try:
                ext = ".mp4" if node.is_video else ".jpg"
                media_url: str | None = node.video_url if node.is_video else node.display_url
                if not media_url:
                    logger.warning(f"[INSTAGRAM_DOWNLOADER] No media URL for sidecar item {i}")
                    all_succeeded = False
                    continue
                suffix = f"_{i}" if i > 0 else ""
                filename = self.file_service.sanitize_filename(f"{base_name}{suffix}{ext}")
                full_path = os.path.join(save_dir, filename)

                def aggregate_progress(percent: float, speed: float, index: int = i) -> None:
                    if progress_callback:
                        bounded = min(100.0, max(0.0, percent))
                        progress_callback(((index + bounded / 100.0) / total) * 100.0, speed)

                result = file_service.download_file(
                    media_url,
                    full_path,
                    aggregate_progress if progress_callback else None,
                )
                if not result.success:
                    all_succeeded = False
            except Exception as e:
                logger.error(f"Error downloading sidecar item {i}: {e!s}")
                all_succeeded = False
        return all_succeeded

    def _download_post(
        self,
        shortcode: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download a single Instagram post or reel."""
        try:
            if not self.loader or not self.loader.context:
                logger.error("[INSTAGRAM_DOWNLOADER] Loader not initialized")
                return False
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            save_dir = os.path.dirname(save_path) if os.path.dirname(save_path) else "."
            self.file_service.ensure_directory(save_dir)

            base_name = os.path.basename(save_path)
            media_success = self._download_media_from_post(
                post, save_dir, base_name, self.file_service, progress_callback
            )

            if caption := post.caption:
                caption_filename = self.file_service.sanitize_filename(f"{base_name}_caption.txt")
                caption_path = os.path.join(save_dir, caption_filename)
                self.file_service.save_text_file(caption, caption_path)

            return media_success

        except Exception as e:
            if self._is_auth_required_error(e):
                logger.error(
                    "[INSTAGRAM_DOWNLOADER] Login required for post %s (authenticated=%s)",
                    shortcode,
                    self.authenticated,
                )
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram",
                        "download",
                        INSTAGRAM_AUTH_REQUIRED_MESSAGE,
                        shortcode,
                    )
                return False

            logger.error(f"Error downloading Instagram post: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, f"Downloading Instagram post {shortcode}", "Instagram"
                )
            return False
