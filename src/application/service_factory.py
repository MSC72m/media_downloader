from src.core.config import AppConfig, get_config
from src.core.enums import ServiceType
from src.core.interfaces import IErrorNotifier, IFileService
from src.services.instagram import InstagramAuthManager
from src.services.instagram.downloader import InstagramDownloader
from src.services.pinterest.downloader import PinterestDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.services.twitter.downloader import TwitterDownloader
from src.services.youtube.downloader import YouTubeDownloader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceFactory:
    def __init__(
        self,
        cookie_manager,
        error_handler: IErrorNotifier | None = None,
        instagram_auth_manager: InstagramAuthManager | None = None,
        file_service: IFileService | None = None,
        config: AppConfig = get_config(),
    ):
        self.cookie_manager = cookie_manager
        self.error_handler = error_handler
        self.instagram_auth_manager = instagram_auth_manager
        self.file_service = file_service
        self.config = config
        logger.info("[SERVICE_FACTORY] Initialized")

    def get_cookie_manager(self):
        return self.cookie_manager

    def detect_service_type(self, url: str) -> ServiceType:
        url_lower = url.lower()

        service_map = {
            ServiceType.YOUTUBE: ["youtube.com", "youtu.be"],
            ServiceType.SOUNDCLOUD: ["soundcloud.com"],
            ServiceType.TWITTER: ["twitter.com", "x.com"],
            ServiceType.INSTAGRAM: ["instagram.com"],
            ServiceType.PINTEREST: ["pinterest.com", "pin.it"],
        }

        for service_type, patterns in service_map.items():
            if any(pattern in url_lower for pattern in patterns):
                return service_type

        logger.warning(f"[SERVICE_FACTORY] Unknown service type for URL: {url}")
        if self.error_handler:
            self.error_handler.handle_service_failure(
                "Service Factory",
                "service detection",
                f"Unknown service type for URL: {url}",
                url,
            )
        return ServiceType.GENERIC

    def get_downloader(self, url: str):
        service_type = self.detect_service_type(url)
        logger.info(f"[SERVICE_FACTORY] Getting downloader for service: {service_type}")

        downloader_map = {
            ServiceType.SOUNDCLOUD: lambda: SoundCloudDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
            ),
            ServiceType.YOUTUBE: lambda: YouTubeDownloader(
                cookie_manager=self.cookie_manager,
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
            ),
            ServiceType.TWITTER: lambda: TwitterDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
            ),
            ServiceType.INSTAGRAM: self._get_instagram_downloader,
            ServiceType.PINTEREST: lambda: PinterestDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
            ),
        }

        downloader_factory = downloader_map.get(service_type)
        if not downloader_factory:
            logger.error(f"[SERVICE_FACTORY] No factory for service type: {service_type}")
            return None

        try:
            return downloader_factory()
        except Exception as e:
            logger.error(f"[SERVICE_FACTORY] Failed to create downloader: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, f"Creating {service_type} downloader", "Service Factory"
                )
            return None

        error_msg = f"No downloader available for: {service_type}"
        logger.error(f"[SERVICE_FACTORY] {error_msg}")
        if self.error_handler:
            self.error_handler.handle_service_failure(
                "Service Factory", "downloader creation", error_msg, url
            )
        return None

    def _get_instagram_downloader(self):
        if not self.instagram_auth_manager:
            logger.warning("[SERVICE_FACTORY] Instagram auth manager not available")
            return InstagramDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
            )

        logger.info(
            "[SERVICE_FACTORY] Checking Instagram auth manager for authenticated downloader"
        )
        shared_downloader = self.instagram_auth_manager.get_downloader()
        if shared_downloader:
            logger.info("[SERVICE_FACTORY] Using shared authenticated Instagram downloader")
            return shared_downloader

        logger.warning(
            "[SERVICE_FACTORY] Instagram auth manager exists but no authenticated downloader available"
        )
        logger.info("[SERVICE_FACTORY] Creating new Instagram downloader instance")
        return InstagramDownloader(
            error_handler=self.error_handler,
            file_service=self.file_service,
            config=self.config,
        )

    def get_service(self, service_type: str):
        logger.debug(f"[SERVICE_FACTORY] Getting service for: {service_type}")
