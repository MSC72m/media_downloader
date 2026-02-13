from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import ClassVar
from urllib.parse import quote, unquote

import requests
from requests.cookies import RequestsCookieJar

from src.core.config import get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from src.services.cookies import RadioJavanSessionManager
from src.services.network.downloader import download_file

from ...utils.logger import get_logger

logger = get_logger(__name__)


class RadioJavanDownloader(BaseDownloader):
    """Radio Javan downloader using API and URL validation."""

    CDN_HOSTS: ClassVar[list[str]] = [
        "https://rj1.media",
        "https://rj2.media",
        "https://rj3.media",
        "https://rjmedia.app",
        "https://rj.app",
    ]

    MP3_PATHS: ClassVar[list[str]] = [
        "/media/mp3/mp3-320/{media_name}.mp3",
        "/media/mp3/mp3-256/{media_name}.mp3",
        "/media/mp3/{media_name}.mp3",
        "/media/mp3/{media_name}",
        "/mp3/{media_name}",
        "/mp3s/{media_name}",
    ]

    MP4_PATHS: ClassVar[list[str]] = [
        "/media/music_video/hd/{media_name}.mp4",
        "/media/music_video/hq/{media_name}.mp4",
        "/media/music_video/lq/{media_name}.mp4",
        "/media/mp4/{media_name}.mp4",
        "/media/mp4/{media_name}",
        "/mp4/{media_name}",
        "/mp4s/{media_name}",
    ]

    MIN_FILE_SIZE = 1024
    PLAY_SEARCH_BASE: ClassVar[str] = "https://play.radiojavan.com/search"

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config=None,
        session_manager: RadioJavanSessionManager | None = None,
    ):
        if config is None:
            config = get_config()
        super().__init__(error_handler, file_service, config)
        self.default_timeout = config.radiojavan.default_timeout
        self.max_retries = config.radiojavan.max_retries
        self._api_base = str(config.radiojavan.api_base_url).rstrip("/")
        self._site_base = self._api_base.removesuffix("/api2")
        self._base_headers = {"User-Agent": self.config.network.user_agent}
        self._session_manager = session_manager or RadioJavanSessionManager(config=self.config)

    def _request_context(
        self,
        force_refresh: bool = False,
    ) -> tuple[dict[str, str], RequestsCookieJar | None]:
        """Build headers/cookies context for requests calls."""
        default_headers = dict(self._base_headers)
        if not self.config.radiojavan.session_enabled:
            return default_headers, None

        context = self._session_manager.get_request_context(force_refresh=force_refresh)
        if not context:
            return default_headers, None

        session_headers, session_cookies = context
        merged_headers = {**default_headers, **session_headers}
        return merged_headers, session_cookies

    @staticmethod
    def _is_challenge_response(
        text: str,
        cf_mitigated: str | None,
        status_code: int | None,
    ) -> bool:
        return RadioJavanSessionManager.is_challenge_response(
            text=text,
            cf_mitigated=cf_mitigated,
            status_code=status_code,
        )

    def _validate_download_inputs(self, url: str, save_path: str) -> bool:
        """Validate download inputs.

        Args:
            url: Radio Javan URL
            save_path: Path to save file

        Returns:
            True if valid, False otherwise
        """
        if not url:
            error_msg = "No URL provided"
            logger.error(f"[RADIOJAVAN_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Radio Javan", "download", error_msg, "")
            return False

        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            error_msg = f"Save directory does not exist: {save_dir}"
            logger.error(f"[RADIOJAVAN_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Radio Javan", "download", error_msg, url)
            return False

        return True

    def _extract_media_name(self, url: str) -> str | None:
        """Extract media name from Radio Javan URL.

        Args:
            url: Radio Javan URL

        Returns:
            Media name or None
        """
        patterns = [
            r"/mp3s/mp3/([\w%-]+)",
            r"/videos/video/([\w%-]+)",
            r"/mp3/([\w%-]+)",
            r"/mp4/([\w%-]+)",
            r"/song/([\w%-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return unquote(match.group(1))
        return None

    @staticmethod
    def _detect_media_type(url: str) -> str | None:
        """Detect whether URL points to mp3 or mp4 content."""
        lowered = url.lower()
        match lowered:
            case value if any(token in value for token in ("/mp3s/mp3/", "/mp3/", "/song/")):
                return "mp3"
            case value if any(token in value for token in ("/videos/video/", "/mp4/")):
                return "mp4"
            case _:
                return None

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Normalize host string into full https://base form."""
        cleaned = host.strip().rstrip("/")
        if cleaned.startswith(("http://", "https://")):
            return cleaned
        return f"https://{cleaned}"

    @staticmethod
    def _normalize_slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @staticmethod
    def _requires_session_for_url(url: str) -> bool:
        lowered = url.lower()
        return "radiojavan.com" in lowered or "rj.app" in lowered

    def _request_context_for_url(
        self,
        url: str,
        force_refresh: bool = False,
    ) -> tuple[dict[str, str], RequestsCookieJar | None]:
        if not self._requires_session_for_url(url):
            return dict(self._base_headers), None
        return self._request_context(force_refresh=force_refresh)

    def _candidate_hosts(self, media_name: str, media_type: str) -> list[str]:
        """Get candidate hosts using Radio Javan API first, then static fallbacks."""
        hosts: list[str] = []

        for endpoint in self._host_lookup_endpoints(media_type):
            host = self._fetch_host_from_endpoint(endpoint, media_name)
            if host:
                hosts.append(self._normalize_host(host))

        configured_hosts = [self._normalize_host(h) for h in self.config.radiojavan.cdn_hosts]
        fallback_hosts = [self._normalize_host(h) for h in self.CDN_HOSTS]
        hosts.extend(configured_hosts)
        hosts.extend(fallback_hosts)

        unique_hosts: list[str] = []
        seen: set[str] = set()
        for host in hosts:
            if host in seen:
                continue
            seen.add(host)
            unique_hosts.append(host)
        return unique_hosts

    def _host_lookup_endpoints(self, media_type: str) -> list[str]:
        """Build host lookup endpoints for current media type."""
        endpoint_map = {
            "mp3": "mp3s/mp3_host",
            "mp4": "videos/video_host",
        }
        endpoint = endpoint_map.get(media_type)
        if not endpoint:
            return []

        # RadioJavan host endpoints are typically under the site root.
        # Keep api2 endpoint as fallback for compatibility.
        return [
            f"{self._site_base}/{endpoint}",
            f"{self._api_base}/{endpoint}",
        ]

    def _fetch_host_from_endpoint(self, endpoint: str, media_name: str) -> str | None:
        """Fetch CDN host from a RadioJavan host endpoint."""
        response = self._post_host_lookup(endpoint, media_name, force_refresh=False)
        if response is None:
            return None

        if self._is_host_lookup_challenge(response):
            logger.warning(
                "[RADIOJAVAN_DOWNLOADER] Challenge detected for host lookup, refreshing "
                "session and retrying: %s",
                endpoint,
            )
            self._session_manager.invalidate_and_refresh()
            response = self._post_host_lookup(endpoint, media_name, force_refresh=True)
            if response is None:
                return None
            if self._is_host_lookup_challenge(response):
                logger.warning(
                    "[RADIOJAVAN_DOWNLOADER] Challenge still present after session refresh: %s",
                    endpoint,
                )
                return None

        payload = self._parse_host_payload(
            response.text,
            content_type=response.headers.get("content-type"),
        )
        host = payload.get("host")
        if isinstance(host, str) and host.strip():
            return host

        logger.debug(
            "[RADIOJAVAN_DOWNLOADER] Host field missing in endpoint response: %s",
            endpoint,
        )
        return None

    @staticmethod
    def _parse_host_payload(
        text: str,
        content_type: str | None = None,
    ) -> dict[str, str]:
        """Parse host JSON payload from RadioJavan endpoint response."""
        if not isinstance(text, str):
            return {}

        normalized_content_type = (content_type or "").lower()
        looks_like_json = "json" in normalized_content_type or text.lstrip().startswith("{")

        if looks_like_json:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return {str(k): str(v) for k, v in parsed.items() if isinstance(k, str)}
            except Exception:
                pass

        host_match = re.search(r'"host"\s*:\s*"([^"]+)"', text)
        if host_match:
            return {"host": host_match.group(1)}

        return {}

    def _post_host_lookup(
        self,
        endpoint: str,
        media_name: str,
        force_refresh: bool,
    ) -> requests.Response | None:
        headers, cookies = self._request_context(force_refresh=force_refresh)
        try:
            response = requests.post(
                endpoint,
                params={"id": media_name},
                headers=headers,
                cookies=cookies,
                timeout=self.default_timeout,
            )
            status_code = response.status_code if isinstance(response.status_code, int) else 0
            if status_code >= 400 and not self._is_host_lookup_challenge(response):
                logger.warning(
                    "[RADIOJAVAN_DOWNLOADER] Host API lookup returned %s (%s, refresh=%s)",
                    status_code,
                    endpoint,
                    force_refresh,
                )
                return None
            return response
        except Exception as exc:
            logger.warning(
                "[RADIOJAVAN_DOWNLOADER] Host API lookup failed (%s, refresh=%s): %s",
                endpoint,
                force_refresh,
                exc,
            )
            return None

    def _is_host_lookup_challenge(self, response: requests.Response) -> bool:
        text = response.text if isinstance(response.text, str) else ""
        cf_mitigated = response.headers.get("cf-mitigated")
        if not isinstance(cf_mitigated, str):
            cf_mitigated = None
        status_code = response.status_code if isinstance(response.status_code, int) else None
        return self._is_challenge_response(
            text=text,
            cf_mitigated=cf_mitigated,
            status_code=status_code,
        )

    def _candidate_paths(self, media_type: str) -> list[str]:
        """Get URL path candidates for media type."""
        return self.MP3_PATHS if media_type == "mp3" else self.MP4_PATHS

    @classmethod
    def _search_query_candidates(cls, media_name: str) -> list[str]:
        words = [token for token in cls._normalize_slug(media_name).split("-") if token]
        if not words:
            return []

        candidates = [
            " ".join(words),
            " ".join(words[:2]),
            words[0],
        ]

        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            cleaned = candidate.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            deduped.append(cleaned)
        return deduped

    @staticmethod
    def _extract_media_entries_from_play_html(
        html: str,
        media_type: str,
    ) -> list[tuple[str, str]]:
        if not isinstance(html, str):
            return []

        match media_type:
            case "mp3":
                extension = "mp3"
            case "mp4":
                extension = "mp4"
            case _:
                return []

        normalized_html = html.replace('\\"', '"').replace("\\/", "/")
        pattern = re.compile(
            rf'"link":"(https://[^"]+?\.{extension})".{{0,4000}}?"permlink":"([^"]+)"',
            re.S,
        )
        entries: list[tuple[str, str]] = []
        for link, permlink in pattern.findall(normalized_html):
            entries.append((permlink, link))
        return entries

    @classmethod
    def _select_best_media_link(
        cls,
        media_name: str,
        entries: list[tuple[str, str]],
    ) -> str | None:
        if not entries:
            return None

        target = cls._normalize_slug(media_name)
        exact_match = next(
            (link for permlink, link in entries if cls._normalize_slug(permlink) == target),
            None,
        )
        if exact_match:
            return exact_match

        partial_match = next(
            (
                link
                for permlink, link in entries
                if target in cls._normalize_slug(permlink)
                or cls._normalize_slug(permlink) in target
            ),
            None,
        )
        if partial_match:
            return partial_match

        return None

    def _resolve_direct_media_url_from_play(
        self,
        media_name: str,
        media_type: str,
    ) -> str | None:
        headers = {
            **self._base_headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        for query in self._search_query_candidates(media_name):
            search_url = f"{self.PLAY_SEARCH_BASE}/{quote(query)}"
            try:
                response = requests.get(
                    search_url,
                    headers=headers,
                    timeout=self.default_timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                logger.debug(
                    "[RADIOJAVAN_DOWNLOADER] Play search lookup failed (%s): %s",
                    search_url,
                    e,
                )
                continue

            cf_mitigated = response.headers.get("cf-mitigated")
            if cf_mitigated == "challenge":
                continue
            if response.status_code == 403 and self._is_challenge_response(
                text=response.text,
                cf_mitigated=cf_mitigated,
                status_code=response.status_code,
            ):
                continue

            entries = self._extract_media_entries_from_play_html(response.text, media_type)
            direct_link = self._select_best_media_link(media_name, entries)
            if not direct_link:
                continue

            logger.info(
                "[RADIOJAVAN_DOWNLOADER] Resolved direct %s URL via play search: %s",
                media_type,
                direct_link,
            )
            return direct_link
        return None

    def _construct_download_url(self, url: str) -> str | None:
        """Construct direct download URL from Radio Javan URL.

        Args:
            url: Radio Javan URL

        Returns:
            Direct download URL or None if construction failed
        """
        media_name = self._extract_media_name(url)
        if not media_name:
            return None

        media_type = self._detect_media_type(url)
        if not media_type:
            logger.warning(f"[RADIOJAVAN_DOWNLOADER] Could not detect media type: {url}")
            return None

        direct_link = self._resolve_direct_media_url_from_play(media_name, media_type)
        if direct_link:
            return direct_link

        hosts = self._candidate_hosts(media_name, media_type)
        paths = self._candidate_paths(media_type)

        first_candidate: str | None = None
        for host in hosts:
            for path in paths:
                download_url = f"{host}{path.format(media_name=media_name)}"
                if first_candidate is None:
                    first_candidate = download_url
                if self._validate_url(download_url):
                    logger.debug(f"[RADIOJAVAN_DOWNLOADER] Valid URL found: {download_url}")
                    return download_url

        if first_candidate:
            logger.warning(
                "[RADIOJAVAN_DOWNLOADER] No candidate URL validated; returning best-effort URL: "
                f"{first_candidate}"
            )
            return first_candidate

        logger.warning(f"[RADIOJAVAN_DOWNLOADER] Could not construct valid URL for: {url}")
        return None

    def _validate_url(self, url: str) -> bool:
        """Validate if URL returns a valid file.

        Args:
            url: Download URL to validate

        Returns:
            True if valid file, False otherwise
        """
        return self._validate_with_head(url) or self._validate_with_range_get(url)

    @staticmethod
    def _is_media_content_type(content_type: str) -> bool:
        lowered = content_type.lower()
        return any(token in lowered for token in ("audio", "video", "octet-stream"))

    def _validate_with_head(self, url: str) -> bool:
        should_retry_after_refresh = True
        while True:
            headers, cookies = self._request_context_for_url(
                url,
                force_refresh=not should_retry_after_refresh,
            )
            try:
                logger.debug(f"[RADIOJAVAN_DOWNLOADER] Validating URL via HEAD: {url}")
                response = requests.head(
                    url,
                    timeout=self.default_timeout,
                    allow_redirects=True,
                    headers=headers,
                    cookies=cookies,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.debug("[RADIOJAVAN_DOWNLOADER] HEAD validation failed (%s): %s", url, exc)
                return False

            if self._is_host_lookup_challenge(response):
                if not self._requires_session_for_url(url) or not should_retry_after_refresh:
                    return False
                should_retry_after_refresh = False
                self._session_manager.invalidate_and_refresh()
                continue

            content_type = response.headers.get("content-type", "")
            if not self._is_media_content_type(content_type):
                return False

            content_length = response.headers.get("content-length", "0")
            file_size = int(content_length) if content_length.isdigit() else 0
            if file_size and file_size < self.MIN_FILE_SIZE:
                logger.warning(f"[RADIOJAVAN_DOWNLOADER] File too small: {file_size} bytes")
                return False

            logger.debug(f"[RADIOJAVAN_DOWNLOADER] URL valid: {file_size} bytes")
            return True

    def _validate_with_range_get(self, url: str) -> bool:
        should_retry_after_refresh = True
        while True:
            headers, cookies = self._request_context_for_url(
                url,
                force_refresh=not should_retry_after_refresh,
            )
            try:
                response = requests.get(
                    url,
                    timeout=self.default_timeout,
                    allow_redirects=True,
                    headers={**headers, "Range": "bytes=0-1"},
                    cookies=cookies,
                    stream=True,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.debug("[RADIOJAVAN_DOWNLOADER] Range validation failed (%s): %s", url, exc)
                return False
            except Exception as exc:
                logger.error("[RADIOJAVAN_DOWNLOADER] Error validating URL: %s", exc)
                return False

            if self._is_host_lookup_challenge(response):
                if not self._requires_session_for_url(url) or not should_retry_after_refresh:
                    return False
                should_retry_after_refresh = False
                self._session_manager.invalidate_and_refresh()
                continue

            content_type = response.headers.get("content-type", "")
            return self._is_media_content_type(content_type)

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download a Radio Javan media file.

        Args:
            url: Radio Javan URL
            save_path: Path to save file (without extension)
            progress_callback: Optional callback for progress updates (progress%, speed)

        Returns:
            bool: True if download successful, False otherwise
        """
        if not self._validate_download_inputs(url, save_path):
            return False

        logger.info(f"[RADIOJAVAN_DOWNLOADER] Starting download: {url}")
        logger.info(f"[RADIOJAVAN_DOWNLOADER] Save path: {save_path}")

        download_url = self._construct_download_url(url)
        if not download_url:
            error_msg = "Could not construct valid download URL"
            logger.error(f"[RADIOJAVAN_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Radio Javan", "download", error_msg, url)
            return False

        headers, cookies = self._request_context_for_url(download_url, force_refresh=False)
        if download_file(
            url=download_url,
            save_path=save_path,
            progress_callback=progress_callback,
            config=self.config,
            headers=headers,
            cookies=cookies,
        ):
            return True

        if not self.config.radiojavan.session_enabled:
            return False
        if not self._requires_session_for_url(download_url):
            return False

        logger.warning(
            "[RADIOJAVAN_DOWNLOADER] Download failed, retrying once with refreshed session"
        )
        self._session_manager.invalidate_and_refresh()
        headers, cookies = self._request_context_for_url(download_url, force_refresh=True)
        return download_file(
            url=download_url,
            save_path=save_path,
            progress_callback=progress_callback,
            config=self.config,
            headers=headers,
            cookies=cookies,
        )
