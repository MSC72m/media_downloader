from typing import Any

import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier
from src.services.youtube.subtitle_parser import YouTubeSubtitleParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeSubtitleExtractor:
    """Extracts YouTube subtitle information using yt-dlp library."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        self.error_handler = error_handler
        self.config = config
        self.subtitle_parser = YouTubeSubtitleParser(config)

    def extract_subtitles(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> dict[str, Any]:
        """Extract subtitle information from YouTube video.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction

        Returns:
            Dict with 'subtitles' and 'automatic_captions' keys
        """
        clients_to_try = ["android", "ios", "tv_embedded"]

        for client in clients_to_try:
            opts = self._build_options(cookie_path, browser, client)
            logger.debug(f"[SUBTITLE_EXTRACTOR] Trying subtitle extraction with {client} client")

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
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
                        f"{len(valid_auto_deduped)} auto subtitles with {client} client "
                        f"(filtered from {len(subtitles)} manual, {len(automatic_captions)} auto, "
                        f"{len(valid_auto) - len(valid_auto_deduped)} duplicates removed)"
                    )
                    return {
                        "subtitles": valid_subtitles,
                        "automatic_captions": valid_auto_deduped,
                    }
            except Exception as e:
                logger.debug(f"[SUBTITLE_EXTRACTOR] {client} client subtitle extraction error: {e}")
                continue

        logger.info("[SUBTITLE_EXTRACTOR] No subtitles found for this video")
        return {"subtitles": {}, "automatic_captions": {}}

    def _build_options(
        self,
        cookie_path: str | None = None,
        browser: str | None = None,
        client: str = "android",
    ) -> dict[str, Any]:
        """Build yt-dlp options for subtitle extraction."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "extractor_args": {"youtube": {"player_client": [client]}},
        }

        if cookie_path:
            opts["cookiefile"] = cookie_path
        elif browser:
            opts["cookiesfrombrowser"] = (browser,)

        return opts
