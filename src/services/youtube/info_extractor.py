from __future__ import annotations

import shutil
from typing import Any, cast

import requests
import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import IAutoCookieManager, ICookieHandler, IErrorNotifier
from src.services.cookies import YouTubeAuthConfig, YouTubeCookieSourceCoordinator
from src.services.ytdlp_logger import YTDLPLoggerBridge
from src.utils.logger import get_logger

from .error_handler import YouTubeErrorBucket, YouTubeErrorHandler

logger = get_logger(__name__)


class YouTubeInfoExtractor:
    """Extracts YouTube metadata using the shared auth-source coordinator."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        auto_cookie_manager: IAutoCookieManager | None = None,
        cookie_handler: ICookieHandler | None = None,
        config: AppConfig = get_config(),
    ):
        self.error_handler = error_handler
        self.config = config
        self.cookie_source_coordinator = YouTubeCookieSourceCoordinator(
            auto_cookie_manager=auto_cookie_manager,
            cookie_handler=cookie_handler,
            config=config,
        )
        self.youtube_error_handler = YouTubeErrorHandler(error_handler=error_handler)
        self._last_error_message: str | None = None

    def extract_info(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract video info from YouTube with ordered auth strategy fallback."""
        auth_strategies = self.cookie_source_coordinator.build_auth_strategies(
            cookie_path_hint=cookie_path,
            preferred_browser=browser,
        )
        logger.info(
            "[INFO_EXTRACTOR] Auth strategies: "
            + ", ".join(strategy.label for strategy in auth_strategies)
        )

        for strategy in auth_strategies:
            if info := self._try_auth_strategy(url, strategy):
                return info

            bucket = self.youtube_error_handler.classify_ytdlp_error(self._last_error_message or "")
            if not self._should_try_next_source(bucket):
                logger.warning(
                    "[INFO_EXTRACTOR] Stopping fallback chain after "
                    f"{strategy.label} due to bucket={bucket.value}"
                )
                break

        if fallback := self._fetch_oembed_fallback(url):
            logger.warning(
                "[INFO_EXTRACTOR] Falling back to oEmbed metadata after yt-dlp extraction failure"
            )
            return fallback

        logger.error("[INFO_EXTRACTOR] All extraction strategies exhausted")
        return None

    def _try_auth_strategy(
        self, url: str, auth_strategy: YouTubeAuthConfig
    ) -> dict[str, Any] | None:
        clients = ["web", "default"]
        for client in clients:
            label = f"{auth_strategy.label}+{client}"
            info = self._extract_single(
                url,
                auth_options=auth_strategy.ytdlp_options,
                client=client,
                label=label,
            )
            if info:
                return info

        return None

    def _extract_single(
        self,
        url: str,
        auth_options: dict[str, Any],
        client: str | None,
        label: str,
    ) -> dict[str, Any] | None:
        """Run a single yt-dlp extraction attempt."""
        opts = self._build_options(auth_options=auth_options, client=client)
        logger.info(f"[INFO_EXTRACTOR] Trying extraction: {label}")

        try:
            with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
                if raw_info := ydl.extract_info(url, download=False):
                    self._last_error_message = None
                    logger.info(f"[INFO_EXTRACTOR] Success with: {label}")
                    return cast(dict[str, Any], raw_info)
        except yt_dlp.utils.DownloadError as exc:  # type: ignore[attr-defined]
            error_msg = str(exc)
            self._last_error_message = error_msg
            short = error_msg[:220]

            if self._is_format_error(error_msg) and client and client != "default":
                logger.warning(
                    "[INFO_EXTRACTOR] Format error with "
                    f"{label}; retrying without client override: {short}"
                )
                return self._retry_without_client(url, auth_options, label)

            bucket = self.youtube_error_handler.classify_ytdlp_error(error_msg)
            logger.warning(
                f"[INFO_EXTRACTOR] Download error with {label} (bucket={bucket.value}): {short}"
            )
        except Exception as exc:
            self._last_error_message = str(exc)
            logger.warning(
                f"[INFO_EXTRACTOR] Unexpected error with {label}: {exc}",
                exc_info=True,
            )

        return None

    def _retry_without_client(
        self,
        url: str,
        auth_options: dict[str, Any],
        label: str,
    ) -> dict[str, Any] | None:
        """Retry extraction without player_client override."""
        opts = self._build_options(auth_options=auth_options, client=None)
        retry_label = f"{label}(no-client-override)"

        try:
            with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
                if raw_info := ydl.extract_info(url, download=False):
                    logger.info(f"[INFO_EXTRACTOR] Success with: {retry_label}")
                    return cast(dict[str, Any], raw_info)
        except Exception as exc:
            self._last_error_message = str(exc)
            logger.debug(f"[INFO_EXTRACTOR] Retry failed ({retry_label}): {exc}")

        return None

    def _build_options(
        self,
        auth_options: dict[str, Any],
        client: str | None,
    ) -> dict[str, Any]:
        """Build yt-dlp options for metadata extraction."""
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "skip_download": True,
            "ignoreconfig": True,
            "nocheckcertificate": True,
            "socket_timeout": 15,
            "logger": YTDLPLoggerBridge("INFO_EXTRACTOR"),
        }

        if shutil.which("node"):
            opts["js_runtimes"] = {"node": {}}
            opts["remote_components"] = "ejs:github"

        if client and client != "default":
            opts["extractor_args"] = {"youtube": {"player_client": [client]}}

        opts.update(auth_options)
        return opts

    @staticmethod
    def _should_try_next_source(bucket: YouTubeErrorBucket) -> bool:
        """Route source fallback by normalized yt-dlp error bucket."""
        match bucket:
            case (
                YouTubeErrorBucket.LOGIN_REQUIRED
                | YouTubeErrorBucket.BROWSER_UNAVAILABLE
                | YouTubeErrorBucket.KEYCHAIN
            ):
                return True
            case YouTubeErrorBucket.NETWORK:
                return True
            case YouTubeErrorBucket.FORMAT:
                return True
            case YouTubeErrorBucket.OTHER:
                return True

    @staticmethod
    def _is_format_error(error_msg: str) -> bool:
        indicators = [
            "requested format is not available",
            "no video formats found",
            "format is not available",
        ]
        lower = error_msg.lower()
        return any(indicator in lower for indicator in indicators)

    def _fetch_oembed_fallback(self, url: str) -> dict[str, Any] | None:
        """Fetch minimal metadata from YouTube oEmbed endpoint."""
        try:
            response = requests.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
                timeout=self.config.network.default_timeout,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            return {
                "title": data.get("title", ""),
                "uploader": data.get("author_name", ""),
                "channel": data.get("author_name", ""),
                "thumbnail": data.get("thumbnail_url", ""),
                "duration": 0,
                "view_count": 0,
                "formats": [],
            }
        except Exception:
            return None
