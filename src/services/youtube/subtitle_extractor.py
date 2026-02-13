from __future__ import annotations

from typing import Any

import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import IAutoCookieManager, ICookieHandler, IErrorNotifier
from src.services.cookies import YouTubeAuthConfig, YouTubeCookieSourceCoordinator
from src.services.youtube.subtitle_parser import YouTubeSubtitleParser
from src.utils.logger import get_logger

from .error_handler import YouTubeErrorBucket, YouTubeErrorHandler

logger = get_logger(__name__)


class YouTubeSubtitleExtractor:
    """Extracts YouTube subtitle information using shared auth-source strategies."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        auto_cookie_manager: IAutoCookieManager | None = None,
        cookie_handler: ICookieHandler | None = None,
        config: AppConfig = get_config(),
    ):
        self.error_handler = error_handler
        self.config = config
        self.subtitle_parser = YouTubeSubtitleParser(config)
        self.cookie_source_coordinator = YouTubeCookieSourceCoordinator(
            auto_cookie_manager=auto_cookie_manager,
            cookie_handler=cookie_handler,
            config=config,
        )
        self.youtube_error_handler = YouTubeErrorHandler(error_handler=error_handler)
        self._last_error_message: str | None = None

    def extract_subtitles(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> dict[str, Any]:
        """Extract subtitle info from YouTube with auth strategy fallback."""
        auth_strategies = self.cookie_source_coordinator.build_auth_strategies(
            cookie_path_hint=cookie_path,
            preferred_browser=browser,
        )
        subtitle_strategies = [
            strategy for strategy in auth_strategies if strategy.source != "browser"
        ]
        if subtitle_strategies:
            auth_strategies = subtitle_strategies

        for auth_strategy in auth_strategies:
            subtitles = self._extract_for_strategy(url, auth_strategy)
            if subtitles:
                return subtitles

            bucket = self.youtube_error_handler.classify_ytdlp_error(self._last_error_message or "")
            if not self._should_try_next_source(bucket):
                break

        logger.info("[SUBTITLE_EXTRACTOR] No subtitles found for this video")
        return {"subtitles": {}, "automatic_captions": {}}

    def _extract_for_strategy(
        self,
        url: str,
        auth_strategy: YouTubeAuthConfig,
    ) -> dict[str, Any] | None:
        clients_to_try: list[str | None] = [None]

        for client in clients_to_try:
            opts = self._build_options(auth_strategy.ytdlp_options, client)
            client_label = client or "default"
            logger.debug(
                "[SUBTITLE_EXTRACTOR] Trying subtitle extraction with "
                f"{client_label} client ({auth_strategy.label})"
            )

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        continue

                    subtitles = info.get("subtitles", {}) or {}
                    automatic_captions = info.get("automatic_captions", {}) or {}
                    video_id = info.get("id", "")

                    valid_subtitles = {
                        lang: sub_list
                        for lang, sub_list in subtitles.items()
                        if (
                            sub_list
                            and isinstance(sub_list, list)
                            and len(sub_list) > 0
                            and (sub_url := sub_list[0].get("url", ""))
                            and self.subtitle_parser.validate(
                                sub_url, {"video_id": video_id, "language_code": lang}
                            )
                        )
                    }

                    valid_auto = {
                        lang: sub_list
                        for lang, sub_list in automatic_captions.items()
                        if (
                            sub_list
                            and isinstance(sub_list, list)
                            and len(sub_list) > 0
                            and (sub_url := sub_list[0].get("url", ""))
                            and self.subtitle_parser.validate(
                                sub_url, {"video_id": video_id, "language_code": lang}
                            )
                        )
                    }

                    if not (valid_subtitles or valid_auto):
                        continue

                    seen_langs = set(valid_subtitles.keys())
                    valid_auto_deduped = {
                        lang: sub_list
                        for lang, sub_list in valid_auto.items()
                        if lang not in seen_langs
                    }

                    logger.info(
                        f"[SUBTITLE_EXTRACTOR] Found {len(valid_subtitles)} manual and "
                        f"{len(valid_auto_deduped)} auto subtitles with {client_label} client "
                        f"({auth_strategy.label})"
                    )
                    self._last_error_message = None
                    return {
                        "subtitles": valid_subtitles,
                        "automatic_captions": valid_auto_deduped,
                    }
            except Exception as exc:
                self._last_error_message = str(exc)
                logger.debug(
                    "[SUBTITLE_EXTRACTOR] Subtitle extraction error with "
                    f"{client_label} / {auth_strategy.label}: {exc}"
                )
                continue

        return None

    def _build_options(self, auth_options: dict[str, Any], client: str | None) -> dict[str, Any]:
        """Build yt-dlp options for subtitle extraction."""
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "ignoreconfig": True,
            "ignoreerrors": True,
            "skip_download": True,
            "socket_timeout": 15,
        }
        if client:
            opts["extractor_args"] = {"youtube": {"player_client": [client]}}

        opts.update(auth_options)
        return opts

    @staticmethod
    def _should_try_next_source(bucket: YouTubeErrorBucket) -> bool:
        """Route source fallback by normalized error bucket."""
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
                return False
            case YouTubeErrorBucket.OTHER:
                return True
