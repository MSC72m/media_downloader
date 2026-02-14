import re
from urllib.parse import parse_qs, urlparse

import requests

from src.core.config import AppConfig, get_config
from src.core.interfaces import (
    IAutoCookieManager,
    ICookieHandler,
    IErrorNotifier,
    IYouTubeMetadataService,
    SubtitleInfo,
    YouTubeMetadata,
)

from ...utils.error_helpers import extract_error_context
from ...utils.logger import get_logger
from .info_extractor import YouTubeInfoExtractor
from .metadata_parser import YouTubeMetadataParser
from .subtitle_extractor import YouTubeSubtitleExtractor

logger = get_logger(__name__)


class YouTubeMetadataService(IYouTubeMetadataService):
    """Service for fetching YouTube video metadata using yt-dlp library."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        auto_cookie_manager: IAutoCookieManager | None = None,
        cookie_handler: ICookieHandler | None = None,
        config: AppConfig = get_config(),
    ) -> None:
        self.config = config
        self.error_handler = error_handler
        self.info_extractor = YouTubeInfoExtractor(
            error_handler=error_handler,
            auto_cookie_manager=auto_cookie_manager,
            cookie_handler=cookie_handler,
            config=config,
        )
        self.metadata_parser = YouTubeMetadataParser(config=config)
        self.subtitle_extractor = YouTubeSubtitleExtractor(
            error_handler=error_handler,
            auto_cookie_manager=auto_cookie_manager,
            cookie_handler=cookie_handler,
            config=config,
        )

    def fetch_metadata(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> YouTubeMetadata | None:
        """Fetch basic metadata for a YouTube URL.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction

        Returns:
            YouTubeMetadata object or None if fetch fails
        """
        try:
            logger.info(f"[METADATA_SERVICE] Fetching metadata for URL: {url}")

            if not self.validate_url(url):
                error_msg = "Invalid YouTube URL"
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "YouTube", "metadata fetch", error_msg, url
                    )
                return YouTubeMetadata(error=error_msg)

            if not (info := self.info_extractor.extract_info(url, cookie_path, browser)):
                if oembed_fallback := self._fetch_oembed_metadata(url):
                    logger.warning(
                        "[METADATA_SERVICE] Falling back to YouTube oEmbed metadata due to yt-dlp extraction failure"
                    )
                    return oembed_fallback

                error_msg = "Failed to fetch video information"
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "YouTube", "metadata fetch", error_msg, url
                    )
                return YouTubeMetadata(error=error_msg)

            parsed_info = self.metadata_parser.parse_info(info)

            if subtitle_data := self.subtitle_extractor.extract_subtitles(
                url, cookie_path, browser
            ):
                parsed_info["subtitles"] = subtitle_data.get("subtitles", {})
                parsed_info["automatic_captions"] = subtitle_data.get("automatic_captions", {})

            available_qualities = self.metadata_parser.extract_qualities(parsed_info)
            available_formats = self.metadata_parser.extract_formats(parsed_info)
            available_subtitles = self.metadata_parser.extract_subtitles(parsed_info)

            return YouTubeMetadata(
                title=parsed_info.get("title", ""),
                duration=self.metadata_parser.format_duration(parsed_info.get("duration", 0)),
                view_count=self.metadata_parser.format_view_count(parsed_info.get("view_count", 0)),
                upload_date=self.metadata_parser.format_upload_date(
                    parsed_info.get("upload_date", "")
                ),
                channel=parsed_info.get("channel", ""),
                description=parsed_info.get("description", ""),
                thumbnail=parsed_info.get("thumbnail", ""),
                available_qualities=available_qualities,
                available_formats=available_formats,
                available_subtitles=available_subtitles,
                is_playlist="entries" in info,
                playlist_count=len(info.get("entries", [])),
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"[METADATA_SERVICE] Error fetching metadata: {error_msg}",
                exc_info=True,
            )
            if self.error_handler:
                extract_error_context(e, "YouTube", "metadata fetch", url)
                self.error_handler.handle_exception(e, "YouTube metadata fetch", "YouTube")
            return YouTubeMetadata(error=f"Failed to fetch metadata: {error_msg}")

    def get_available_qualities(self, url: str) -> list[str]:
        """Get available video qualities for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            return metadata.available_qualities if metadata else []
        except Exception as e:
            logger.error(f"[METADATA_SERVICE] Error fetching qualities: {e!s}")
            return []

    def get_available_formats(self, url: str) -> list[str]:
        """Get available formats for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            return metadata.available_formats if metadata else []
        except Exception as e:
            logger.error(f"[METADATA_SERVICE] Error fetching formats: {e!s}")
            return []

    def get_available_subtitles(self, url: str) -> list[SubtitleInfo]:
        """Get available subtitles for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            if not metadata or not metadata.available_subtitles:
                return []

            subtitles: list[SubtitleInfo] = []
            for sub in metadata.available_subtitles:
                language_code = sub.get("language_code")
                language_name = sub.get("language_name")
                is_auto_generated = sub.get("is_auto_generated")
                subtitle_url = sub.get("url")

                if not isinstance(language_code, str):
                    continue
                if not isinstance(language_name, str):
                    continue
                if not isinstance(is_auto_generated, bool):
                    continue
                if not isinstance(subtitle_url, str):
                    continue

                subtitles.append(
                    SubtitleInfo(
                        language_code=language_code,
                        language_name=language_name,
                        is_auto_generated=is_auto_generated,
                        url=subtitle_url,
                    )
                )
            return subtitles
        except Exception as e:
            logger.error(f"[METADATA_SERVICE] Error fetching subtitles: {e!s}")
            return []

    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube URL."""
        if any(re.match(pattern, url) for pattern in self.config.youtube.url_patterns):
            return True
        return self.extract_video_id(url) is not None

    def extract_video_id(self, url: str) -> str | None:
        """Extract video ID from YouTube URL."""
        try:
            parsed_url = urlparse(url)
            hostname = (parsed_url.hostname or "").lower()

            if hostname in {"www.youtube.com", "youtube.com", "music.youtube.com", "m.youtube.com"}:
                if parsed_url.path == "/watch":
                    query = parse_qs(parsed_url.query)
                    return query.get("v", [None])[0]
                if parsed_url.path.startswith("/embed/") or parsed_url.path.startswith("/v/"):
                    return parsed_url.path.split("/")[2]
            if hostname == "youtu.be":
                return parsed_url.path[1:]  # Remove leading slash

            return None
        except Exception:
            return None

    def _fetch_oembed_metadata(self, url: str) -> YouTubeMetadata | None:
        """Fetch minimal metadata via YouTube oEmbed as a resilient fallback."""
        if not (video_id := self.extract_video_id(url)):
            return None

        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        timeout = self.config.network.default_timeout
        try:
            response = requests.get(
                "https://www.youtube.com/oembed",
                params={"url": canonical_url, "format": "json"},
                timeout=timeout,
            )
            if response.status_code != 200:
                logger.warning(
                    f"[METADATA_SERVICE] oEmbed fallback failed with status {response.status_code}"
                )
                return None

            data = response.json()
            return YouTubeMetadata(
                title=str(data.get("title", "")),
                duration="Unknown",
                view_count="N/A",
                upload_date="Unknown",
                channel=str(data.get("author_name", "")),
                description="",
                thumbnail=str(data.get("thumbnail_url", "")),
                available_qualities=list(self.config.youtube.video_qualities),
                available_formats=["video", "audio"],
                available_subtitles=[],
                is_playlist=False,
                playlist_count=0,
            )
        except Exception as exc:
            logger.warning(f"[METADATA_SERVICE] oEmbed fallback error: {exc}")
            return None
