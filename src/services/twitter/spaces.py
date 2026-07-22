"""Twitter Spaces downloader.

Uses Twitter's guest GraphQL API to fetch space metadata and audio stream
URL, then downloads the HLS stream via ffmpeg.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from typing import Any

import requests

from src.core.config import AppConfig
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from src.utils.ffmpeg import get_ffmpeg_path
from src.utils.logger import get_logger
from src.utils.proxy import get_request_proxies

logger = get_logger(__name__)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_SPACE_ID_PATTERN = re.compile(r"/i/spaces/([a-zA-Z0-9_]+)")
_BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"  # noqa: S105
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
_GRAPHQL_URL = "https://twitter.com/i/api/graphql/kZ9wfR8EBtiP0As3sFFrBA/AudioSpaceById"


class _SpaceUnavailableError(RuntimeError):
    """Raised when a Space is private, deleted, replay-disabled, or otherwise unavailable."""


class TwitterSpacesDownloader(BaseDownloader):
    """Downloads Twitter Spaces audio using GraphQL guest auth and ffmpeg."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config: AppConfig | None = None,
    ) -> None:
        super().__init__(error_handler, file_service, config)
        self._guest_token: str | None = None

    @staticmethod
    def extract_space_id(url: str) -> str | None:
        match = _SPACE_ID_PATTERN.search(url)
        return match.group(1) if match else None

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        space_id = self.extract_space_id(url)
        if not space_id:
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Twitter Spaces", "download", "No space ID found in URL", url
                )
            return False

        try:
            self._guest_token = self._activate_guest_token()
            space_data = self._fetch_space_data(space_id)
            stream_url = self._extract_stream_url(space_data)
            metadata = space_data.get("metadata", {})

            title = self._format_title(metadata) or f"twitter_space_{space_id}"
            output_path = os.path.join(
                os.path.dirname(save_path),
                self.file_service.sanitize_filename(f"{title}.m4a")
                if self.file_service
                else f"{title}.m4a",
            )
            self._download_hls(stream_url, output_path, progress_callback)
            if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
                raise RuntimeError("ffmpeg completed without producing a non-empty audio file")
            return True

        except _SpaceUnavailableError as exc:
            logger.warning("[SPACES] Space %s unavailable: %s", space_id, exc)
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Twitter Spaces",
                    "download",
                    str(exc),
                    url,
                )
            return False
        except Exception as e:
            logger.error(f"[SPACES] Failed to download space {space_id}: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, f"Downloading Twitter Space {space_id}", "Twitter Spaces"
                )
            return False

    def _activate_guest_token(self) -> str:
        resp = requests.post(
            "https://api.twitter.com/1.1/guest/activate.json",
            headers={
                "Authorization": f"Bearer {_BEARER_TOKEN}",
                "User-Agent": _UA,
            },
            proxies=get_request_proxies(self.config),
            timeout=self.config.twitter.default_timeout,
        )
        resp.raise_for_status()
        return str(resp.json()["guest_token"])

    def _fetch_space_data(self, space_id: str) -> dict[str, Any]:
        if not self._guest_token:
            self._guest_token = self._activate_guest_token()
        variables = json.dumps(
            {
                "id": space_id,
                "isMetatagsQuery": False,
                "withListeners": True,
                "withReplays": True,
            }
        )
        features = json.dumps(
            {
                "spaces_2022_h2_spaces_communities": True,
                "spaces_2022_h2_clipping": True,
            }
        )
        params = {"variables": variables, "features": features}
        headers = {
            "Authorization": f"Bearer {_BEARER_TOKEN}",
            "x-guest-token": self._guest_token or "",
            "content-type": "application/json",
            "User-Agent": _UA,
        }
        resp = requests.get(
            _GRAPHQL_URL,
            params=params,
            headers=headers,
            proxies=get_request_proxies(self.config),
            timeout=self.config.twitter.default_timeout,
        )
        if resp.status_code == 403:
            raise _SpaceUnavailableError(
                "Guest API access was denied; this Space may require authentication or be private."
            )
        resp.raise_for_status()
        data = resp.json()
        raw_errors = data.get("errors")
        space = data.get("data", {}).get("audioSpace")
        if raw_errors and not space:
            messages = [
                str(item.get("message", item)) if isinstance(item, dict) else str(item)
                for item in raw_errors
            ]
            raise RuntimeError(f"Twitter GraphQL metadata error: {'; '.join(messages)}")
        if not isinstance(space, dict) or not space.get("metadata"):
            raise _SpaceUnavailableError(
                f"Space {space_id} is unavailable. It may be private, deleted, "
                "or have replay disabled."
            )
        return space

    def _extract_stream_url(self, space_data: dict[str, Any]) -> str:
        stream = space_data.get("stream") or {}
        location: str | None = (
            stream.get("location") or stream.get("url") or stream.get("playlistUrl")
        )
        if location:
            return location

        meta = space_data.get("metadata") or {}
        if meta.get("is_space_available_for_replay") and meta.get("media_key"):
            location = self._fetch_replay_url(meta["media_key"])
            if location:
                return location

        state = meta.get("state", "unknown")
        raise _SpaceUnavailableError(
            f"Space is {state} and has no stream URL. "
            f"Replay available: {meta.get('is_space_available_for_replay', False)}"
        )

    def _fetch_replay_url(self, media_key: str) -> str | None:
        resp = requests.get(
            f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}",
            headers={
                "Authorization": f"Bearer {_BEARER_TOKEN}",
                "x-guest-token": self._guest_token or "",
                "User-Agent": _UA,
            },
            proxies=get_request_proxies(self.config),
            timeout=self.config.twitter.default_timeout,
        )
        if not resp.ok:
            logger.warning(
                f"[SPACES] Failed to fetch replay URL for media_key {media_key}: {resp.status_code}"
            )
            return None
        data = resp.json()
        return data.get("source", {}).get("location") or data.get("location")

    @staticmethod
    def _format_title(metadata: dict[str, Any]) -> str | None:
        title = metadata.get("title") or metadata.get("name") or ""
        creator_results = metadata.get("creator_results") or {}
        creator_result = creator_results.get("result") or {}
        legacy = creator_result.get("legacy") or {}
        creator_name = legacy.get("name") or legacy.get("screen_name") or ""
        if title and creator_name:
            return f"{creator_name} - {title}"
        if title:
            return str(title)
        if creator_name:
            return f"Twitter Space - {creator_name}"
        return None

    def _download_hls(
        self,
        stream_url: str,
        output_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> None:
        ffmpeg = get_ffmpeg_path()
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required to download Twitter Spaces audio")

        ffmpeg_args = [
            ffmpeg,
            "-y",
            "-i",
            stream_url,
            "-c",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            "-movflags",
            "+faststart",
            output_path,
        ]

        logger.info(f"[SPACES] Starting ffmpeg download: {output_path}")
        if progress_callback:
            progress_callback(0.0, 0.0)
        process = subprocess.Popen(
            ffmpeg_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _, stderr = process.communicate(
                timeout=self.config.twitter.space_download_timeout_seconds
            )
        except subprocess.TimeoutExpired as exc:
            process.kill()
            _, stderr = process.communicate()
            with contextlib.suppress(OSError):
                os.remove(output_path)
            raise RuntimeError(
                "ffmpeg exceeded the configured Twitter Spaces download timeout"
            ) from exc

        if process.returncode != 0:
            with contextlib.suppress(OSError):
                os.remove(output_path)
            raise RuntimeError(f"ffmpeg failed: {stderr[-500:]}")
        if progress_callback:
            progress_callback(100.0, 0.0)
        logger.info(f"[SPACES] Download complete: {output_path}")
