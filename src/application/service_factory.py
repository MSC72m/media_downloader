from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from src.core.config import AppConfig, get_config
from src.core.enums import ServiceType
from src.core.interfaces import (
    BaseDownloader,
    IAutoCookieManager,
    ICookieHandler,
    IErrorNotifier,
    IFileService,
)
from src.services.cookies import (
    RadioJavanCookieManager,
    SoundCloudCookieManager,
    SpotifyCookieManager,
)
from src.services.instagram import InstagramAuthManager
from src.services.instagram.downloader import InstagramDownloader
from src.services.pinterest.downloader import PinterestDownloader
from src.services.radiojavan.downloader import RadioJavanDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.services.spotify.downloader import SpotifyDownloader
from src.services.tiktok.downloader import TikTokDownloader
from src.services.twitter.downloader import TwitterDownloader
from src.services.youtube.downloader import YouTubeDownloader
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.models import Download

logger = get_logger(__name__)


class ServiceFactory:
    def __init__(
        self,
        cookie_handler: ICookieHandler | None = None,
        cookie_manager: ICookieHandler | None = None,
        auto_cookie_manager: IAutoCookieManager | None = None,
        rj_cookie_manager: RadioJavanCookieManager | None = None,
        sc_cookie_manager: SoundCloudCookieManager | None = None,
        spotify_cookie_manager: SpotifyCookieManager | None = None,
        error_handler: IErrorNotifier | None = None,
        instagram_auth_manager: InstagramAuthManager | None = None,
        file_service: IFileService | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        self.cookie_handler = cookie_handler if cookie_handler is not None else cookie_manager
        self.auto_cookie_manager = auto_cookie_manager
        self.rj_cookie_manager = rj_cookie_manager
        self.sc_cookie_manager = sc_cookie_manager
        self.spotify_cookie_manager = spotify_cookie_manager
        self.error_handler = error_handler
        self.instagram_auth_manager = instagram_auth_manager
        self.file_service = file_service
        self.config = resolved_config
        logger.info("[SERVICE_FACTORY] Initialized")

    def get_cookie_handler(self) -> ICookieHandler | None:
        return self.cookie_handler

    def get_cookie_manager(self) -> ICookieHandler | None:
        """Backward-compatible alias for older tests/callers."""
        return self.cookie_handler

    def get_auto_cookie_manager(self) -> IAutoCookieManager | None:
        return self.auto_cookie_manager

    def detect_service_type(self, url: str) -> ServiceType:
        parsed = urlparse(url if "://" in url else f"//{url}")
        host = (parsed.hostname or "").lower().rstrip(".")

        service_map = {
            ServiceType.YOUTUBE: {"youtube.com", "youtu.be"},
            ServiceType.SOUNDCLOUD: {"soundcloud.com", "soundcloud.app.goo.gl"},
            ServiceType.TWITTER: {"twitter.com", "x.com"},
            ServiceType.INSTAGRAM: {"instagram.com"},
            ServiceType.PINTEREST: {
                "pinterest.com",
                "pinterest.com.au",
                "pinterest.ca",
                "pinterest.co.uk",
                "pinterest.de",
                "pinterest.fr",
                "pin.it",
            },
            ServiceType.TIKTOK: {"tiktok.com"},
            ServiceType.RADIOJAVAN: {"radiojavan.com", "rj.app"},
            ServiceType.SPOTIFY: {
                "spotify.com",
                "spotify.link",
                "song.link",
                "album.link",
                "playlist.link",
            },
        }

        for service_type, domains in service_map.items():
            if any(host == domain or host.endswith(f".{domain}") for domain in domains):
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

    def get_downloader(
        self,
        url: str,
        service_type: ServiceType | None = None,
        download: Download | None = None,
    ) -> BaseDownloader | None:
        if service_type is None:
            service_type = self.detect_service_type(url)
        logger.info(f"[SERVICE_FACTORY] Getting downloader for service: {service_type}")

        downloader_map = {
            ServiceType.SOUNDCLOUD: lambda: SoundCloudDownloader(
                download_playlist=(
                    bool(download and download.download_playlist) or "/sets/" in url.lower()
                ),
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
                cookie_manager=self.sc_cookie_manager,
            ),
            ServiceType.YOUTUBE: lambda: YouTubeDownloader(
                quality=(download.quality if download and download.quality else "720p"),
                download_playlist=bool(download and download.download_playlist),
                audio_only=bool(download and download.audio_only),
                video_only=bool(download and download.video_only),
                format=(download.format if download and download.format else "video"),
                download_subtitles=bool(download and download.download_subtitles),
                selected_subtitles=(download.selected_subtitles if download else None),
                download_thumbnail=(download.download_thumbnail if download else True),
                embed_metadata=(download.embed_metadata if download else True),
                speed_limit=(download.speed_limit if download else None),
                retries=(download.retries if download else 3),
                cookie_handler=self.cookie_handler,
                auto_cookie_manager=self.auto_cookie_manager,
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
            ServiceType.TIKTOK: lambda: TikTokDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
            ),
            ServiceType.RADIOJAVAN: lambda: RadioJavanDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
                cookie_manager=self.rj_cookie_manager,
            ),
            ServiceType.SPOTIFY: lambda: SpotifyDownloader(
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
                cookie_handler=self.cookie_handler,
                auto_cookie_manager=self.auto_cookie_manager,
                spotify_cookie_manager=self.spotify_cookie_manager,
            ),
        }

        if not (downloader_factory := downloader_map.get(service_type)):
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

    def _get_instagram_downloader(self) -> InstagramDownloader:
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
        if shared_downloader := self.instagram_auth_manager.get_downloader():
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

    def get_service(self, service_type: str) -> None:
        logger.debug(f"[SERVICE_FACTORY] Getting service for: {service_type}")
