"""Instagram authentication manager service."""

from threading import Lock

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier
from src.services.instagram.downloader import InstagramDownloader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InstagramAuthManager:
    """Manages Instagram authentication state and authenticated downloader instance."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        """Initialize Instagram authentication manager.

        Args:
            error_handler: Optional error handler for user notifications
            config: AppConfig instance (defaults to get_config() if None)
        """
        self.config = config
        self.error_handler = error_handler
        self._downloader: InstagramDownloader | None = None
        self._authenticating: bool = False
        self._lock = Lock()

    def is_authenticated(self) -> bool:
        """Check if Instagram is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        with self._lock:
            return self._downloader is not None and self._downloader.authenticated

    def is_authenticating(self) -> bool:
        """Check if Instagram authentication is in progress.

        Returns:
            True if authenticating, False otherwise
        """
        with self._lock:
            return self._authenticating

    def get_downloader(self) -> InstagramDownloader | None:
        """Get the shared authenticated Instagram downloader instance.

        Returns:
            Authenticated InstagramDownloader instance or None if not authenticated
        """
        with self._lock:
            # Check directly without calling is_authenticated() to avoid deadlock
            # (is_authenticated() also tries to acquire the same lock)
            if is_auth := (self._downloader is not None and self._downloader.authenticated):
                logger.info(
                    f"[INSTAGRAM_AUTH_MANAGER] get_downloader called: is_authenticated={is_auth}, downloader={self._downloader is not None}, authenticated={getattr(self._downloader, 'authenticated', None) if self._downloader else None}"
                )
                return self._downloader
            return None

    def set_authenticating(self, value: bool) -> None:
        """Set authenticating flag.

        Args:
            value: True if authenticating, False otherwise
        """
        with self._lock:
            self._authenticating = value
            logger.debug(f"[INSTAGRAM_AUTH_MANAGER] Authenticating flag set to: {value}")

    def set_authenticated_downloader(self, downloader: InstagramDownloader) -> None:
        """Store authenticated downloader instance.

        Args:
            downloader: Authenticated InstagramDownloader instance
        """
        with self._lock:
            self._downloader = downloader
            self._authenticating = False
            logger.info("[INSTAGRAM_AUTH_MANAGER] Authenticated downloader stored")

    def clear_authentication(self) -> None:
        """Clear authentication state."""
        with self._lock:
            self._downloader = None
            self._authenticating = False
            logger.info("[INSTAGRAM_AUTH_MANAGER] Authentication cleared")
