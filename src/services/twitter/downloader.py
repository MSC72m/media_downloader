import json
import os
import re
from collections.abc import Callable
from typing import Any

import requests

from src.core.config import get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService

from ...core.enums import ServiceType
from ...utils.logger import get_logger
from ..file.service import FileService
from ..network.checker import check_site_connection

logger = get_logger(__name__)


class TwitterDownloader(BaseDownloader):
    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config=None,
    ):
        """Initialize Twitter downloader.

        Args:
            error_handler: Optional error handler for user notifications
            file_service: Optional file service for file operations
            config: AppConfig instance (defaults to get_config() if None)
        """
        if config is None:
            config = get_config()
        super().__init__(error_handler, file_service, config)
        if not self.file_service:
            self.file_service = FileService()

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """
        Download media from Twitter URLs.

        Args:
            url: Twitter URL to download from
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        try:
            connected, error_msg = check_site_connection(ServiceType.TWITTER)
            if not connected:
                logger.error(f"Cannot download from Twitter: {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Twitter", "download", error_msg or "Connection failed", url
                    )
                return False

            if not (tweet_refs := self._extract_tweet_references(url)):
                error_msg = "No tweet IDs found in URL"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure("Twitter", "download", error_msg, url)
                return False

            success = False
            for i, (username, tweet_id) in enumerate(tweet_refs):
                if not (tweet_data := self._scrape_tweet_data(tweet_id, username)):
                    continue

                save_name = f"{save_path}_{i}" if len(tweet_refs) > 1 else save_path
                media_success = self._download_media(
                    tweet_data.get("media", []), save_name, progress_callback
                )
                artifact_success = self._save_tweet_artifacts(save_name, tweet_data)

                if media_success or artifact_success:
                    success = True

            if not success:
                error_msg = "Failed to download media from tweet"
                if self.error_handler:
                    self.error_handler.handle_service_failure("Twitter", "download", error_msg, url)

            return success

        except Exception as e:
            logger.error(f"Error downloading from Twitter: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Twitter download", "Twitter")
            return False

    @staticmethod
    def _extract_tweet_ids(text: str) -> list[str] | None:
        """Extract tweet IDs from a Twitter/X URL."""
        refs = TwitterDownloader._extract_tweet_references(text)
        ids = [tweet_id for _, tweet_id in refs]
        return ids or None

    @staticmethod
    def _extract_tweet_references(text: str) -> list[tuple[str | None, str]]:
        """Extract (username, tweet_id) tuples from a Twitter/X URL."""
        patterns = (
            re.compile(
                r"(?:https?://)?(?:mobile\.)?(?:twitter|x)\.com/"
                r"(?P<username>[A-Za-z0-9_]{1,15})/status(?:es)?/(?P<tweet_id>[0-9]{1,20})",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:https?://)?(?:mobile\.)?(?:twitter|x)\.com/"
                r"i/web/status/(?P<tweet_id>[0-9]{1,20})",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:https?://)?(?:mobile\.)?(?:twitter|x)\.com/"
                r"status/(?P<tweet_id>[0-9]{1,20})",
                re.IGNORECASE,
            ),
        )

        refs_by_id: dict[str, str | None] = {}
        for pattern in patterns:
            for match in pattern.finditer(text):
                tweet_id = match.group("tweet_id")
                username = match.groupdict().get("username")
                if tweet_id not in refs_by_id:
                    refs_by_id[tweet_id] = username
                    continue
                if username and not refs_by_id[tweet_id]:
                    refs_by_id[tweet_id] = username

        return [(username, tweet_id) for tweet_id, username in refs_by_id.items()]

    def _scrape_tweet_data(self, tweet_id: str, username: str | None = None) -> dict | None:
        """Scrape tweet data including media and text from FixTweet/VX endpoints."""
        endpoints: list[str] = []
        if username:
            endpoints.append(f"https://api.fxtwitter.com/{username}/status/{tweet_id}")
        endpoints.extend(
            [
                f"https://api.fxtwitter.com/status/{tweet_id}",
                f"https://api.vxtwitter.com/Twitter/status/{tweet_id}",
                f"https://api.vxtwitter.com/status/{tweet_id}",
            ]
        )

        headers = {"User-Agent": self.config.network.user_agent}
        try:
            for endpoint in endpoints:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    verify=True,
                    timeout=self.config.network.twitter_api_timeout,
                )
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                match content_type:
                    case value if "application/json" in value:
                        data = response.json()
                        if not (tweet_data := self._select_tweet_payload(data)):
                            continue

                        media = self._normalize_media(tweet_data)
                        return {
                            "media": media,
                            "text": str(tweet_data.get("text", "")).strip(),
                            "raw": tweet_data,
                        }
                    case value if "text/html" in value:
                        if "Failed to scan your link" in response.text:
                            logger.warning(
                                "[TWITTER_DOWNLOADER] vxTwitter API is currently unavailable "
                                "for this tweet (upstream API limitation)"
                            )
                        continue
                    case _:
                        continue

            logger.warning(
                "[TWITTER_DOWNLOADER] No usable JSON response from configured tweet API endpoints"
            )
            return None
        except Exception as e:
            logger.error(f"Error scraping tweet data: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, f"Scraping tweet {tweet_id}", "Twitter")
            return None

    def _save_tweet_artifacts(self, save_path: str, tweet_data: dict[str, Any]) -> bool:
        """Persist scraped tweet text/JSON for reliability when media CDNs are blocked."""
        base_name = os.path.basename(save_path)
        save_dir = os.path.dirname(save_path) if os.path.dirname(save_path) else "."
        saved_any = False

        if text := str(tweet_data.get("text", "")).strip():
            caption_filename = self.file_service.sanitize_filename(f"{base_name}_description.txt")
            caption_path = os.path.join(save_dir, caption_filename)
            self.file_service.save_text_file(text, caption_path)
            saved_any = True

        raw_payload = tweet_data.get("raw")
        if isinstance(raw_payload, dict):
            json_filename = self.file_service.sanitize_filename(f"{base_name}_tweet.json")
            json_path = os.path.join(save_dir, json_filename)
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(raw_payload, f, ensure_ascii=False, indent=2)
                saved_any = True
            except Exception as e:
                logger.warning(f"[TWITTER_DOWNLOADER] Failed to save tweet JSON artifact: {e}")

        return saved_any

    @staticmethod
    def _select_tweet_payload(data: dict[str, Any]) -> dict[str, Any] | None:
        """Support both FixTweet schema and legacy vxTwitter schema."""
        tweet = data.get("tweet")
        if isinstance(tweet, dict):
            return tweet
        return data if isinstance(data, dict) else None

    @staticmethod
    def _best_variant_url(variants: Any) -> str | None:
        """Pick highest bitrate MP4 from variant list when present."""
        if not isinstance(variants, list):
            return None

        candidates: list[tuple[int, str]] = []
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            url = variant.get("url")
            if not isinstance(url, str) or not url:
                continue
            if (content_type := str(variant.get("content_type", ""))) and "mp4" not in content_type:
                continue
            bitrate = int(variant.get("bitrate") or 0)
            candidates.append((bitrate, url))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _normalize_media(self, tweet_data: dict[str, Any]) -> list[dict[str, str]]:
        """Normalize media payloads from different tweet API schemas."""
        media_entries = self._extract_legacy_media_entries(tweet_data)
        media_entries.extend(self._extract_modern_media_entries(tweet_data))

        deduped: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for item in media_entries:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(item)
        return deduped

    @staticmethod
    def _extract_legacy_media_entries(tweet_data: dict[str, Any]) -> list[dict[str, str]]:
        """Extract media from legacy vxTwitter schema."""
        entries: list[dict[str, str]] = []
        legacy = tweet_data.get("media_extended")
        if not isinstance(legacy, list):
            return entries

        for item in legacy:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            media_type = str(item.get("type", "photo"))
            if isinstance(url, str) and url:
                entries.append({"url": url, "type": media_type})
        return entries

    def _extract_modern_media_entries(self, tweet_data: dict[str, Any]) -> list[dict[str, str]]:
        """Extract media from FixTweet schema."""
        media = tweet_data.get("media")
        match media:
            case {"all": list(all_media)}:
                source_items = all_media
            case list() as media_list:
                source_items = media_list
            case _:
                source_items = []

        return [
            normalized
            for item in source_items
            if (normalized := self._normalize_modern_media_item(item))
        ]

    def _normalize_modern_media_item(self, item: Any) -> dict[str, str] | None:
        """Normalize a single media item from FixTweet payload."""
        if not isinstance(item, dict):
            return None

        media_type = str(item.get("type", "photo"))
        url = item.get("url")
        if not isinstance(url, str) or not url:
            url = self._best_variant_url(item.get("variants"))
        if not url:
            return None

        normalized_type = "video" if media_type in {"video", "animated_gif", "gif"} else "photo"
        return {"url": url, "type": normalized_type}

    def _download_media(
        self,
        media: list[dict],
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download media files from tweet media data."""
        success = False

        for i, item in enumerate(media):
            try:
                if not (url := item.get("url")):
                    continue

                match item.get("type"):
                    case "video" | "animated_gif" | "gif":
                        ext = ".mp4"
                    case "photo":
                        ext = ".jpg"
                    case _:
                        ext = ".bin"

                if len(media) > 1:
                    filename = self.file_service.sanitize_filename(
                        f"{os.path.basename(save_path)}_{i}{ext}"
                    )
                else:
                    filename = self.file_service.sanitize_filename(
                        f"{os.path.basename(save_path)}{ext}"
                    )

                full_path = os.path.join(os.path.dirname(save_path), filename)

                file_service = self.file_service if self.file_service else FileService()
                if (
                    (
                        result := file_service.download_file(url, full_path, progress_callback)
                    ).success
                    and os.path.exists(full_path)
                    and os.path.getsize(full_path) > 0
                ):
                    success = True
                elif result.success:
                    logger.warning(
                        f"[TWITTER_DOWNLOADER] Download reported success but file is missing/empty: {full_path}"
                    )
            except Exception as e:
                logger.error(f"Error downloading media item {i}: {e!s}", exc_info=True)
                if self.error_handler:
                    self.error_handler.handle_exception(e, f"Downloading media item {i}", "Twitter")
                continue

        return success
