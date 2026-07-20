import json
import re
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any

import requests
import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import (
    BaseDownloader,
    IAutoCookieManager,
    ICookieHandler,
    IErrorNotifier,
    IFileService,
)

from ...utils.logger import get_logger
from ...utils.proxy import get_request_proxies
from ..youtube.downloader import YouTubeDownloader

logger = get_logger(__name__)
_REQUEST_EXCEPTION = (
    requests.exceptions.RequestException
    if isinstance(getattr(requests, "exceptions", None), object)
    and isinstance(getattr(requests.exceptions, "RequestException", None), type)
    and issubclass(requests.exceptions.RequestException, BaseException)
    else Exception
)
_TIMEOUT_EXCEPTION = (
    requests.Timeout
    if isinstance(getattr(requests, "Timeout", None), type)
    and issubclass(requests.Timeout, BaseException)
    else _REQUEST_EXCEPTION
)


class SpotifyDownloader(BaseDownloader):
    """Downloads Spotify content by finding matches on YouTube.

    This downloader:
    1. Extracts metadata from Spotify OEmbed API
    2. For playlists/albums: Scrapes track list from Spotify
    3. Searches YouTube for each track
    4. Returns search results for user selection
    5. Downloads selected YouTube video using YouTubeDownloader
    """

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config: AppConfig = get_config(),
        cookie_handler: ICookieHandler | None = None,
        auto_cookie_manager: IAutoCookieManager | None = None,
        spotify_cookie_manager: Any = None,
    ) -> None:
        super().__init__(error_handler, file_service, config)
        self.default_timeout = config.spotify.default_timeout
        self.oembed_timeout = config.spotify.oembed_timeout
        self.max_search_results = config.spotify.max_search_results
        self.min_similarity_threshold = config.spotify.min_similarity_threshold
        self.cookie_handler = cookie_handler
        self.auto_cookie_manager = auto_cookie_manager
        self.spotify_cookie_manager = spotify_cookie_manager

    def _detect_url_type(self, url: str) -> str:
        """Detect if URL is track, album, playlist, or artist.

        Args:
            url: Spotify URL

        Returns:
            URL type: 'track', 'album', 'playlist', 'artist', or 'unknown'
        """
        lowered = url.lower()
        if "spotify.com" not in lowered and "spotify:" not in lowered:
            return "unknown"

        match lowered:
            case value if "/track/" in value or "spotify:track:" in value:
                return "track"
            case value if "/album/" in value or "spotify:album:" in value:
                return "album"
            case value if "/playlist/" in value or "spotify:playlist:" in value:
                return "playlist"
            case value if "/artist/" in value or "spotify:artist:" in value:
                return "artist"
            case _:
                return "unknown"

    def _extract_spotify_id(self, url: str) -> str | None:
        """Extract Spotify content ID from URL.

        Args:
            url: Spotify URL

        Returns:
            Spotify content ID or None
        """
        match = re.search(r"/(?:track|album|playlist|artist)/([\w-]+)", url)
        return match.group(1) if match else None

    def _extract_spotify_metadata(self, url: str) -> dict[str, Any]:
        """Extract metadata from Spotify OEmbed API.

        Args:
            url: Spotify URL

        Returns:
            Dictionary with metadata (title, thumbnail, type, id)
        """
        try:
            oembed_url = f"https://open.spotify.com/oembed?url={url}"

            for attempt in range(3):
                try:
                    response = requests.get(
                        oembed_url,
                        timeout=30,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        },
                        proxies=get_request_proxies(self.config),
                    )
                    response.raise_for_status()
                    data = response.json()

                    return {
                        "title": data.get("title", "Unknown"),
                        "type": self._detect_url_type(url),
                        "thumbnail": data.get("thumbnail_url", ""),
                        "original_url": url,
                        "id": self._extract_spotify_id(url),
                    }
                except _TIMEOUT_EXCEPTION:
                    logger.warning(f"[SPOTIFY_DOWNLOADER] OEmbed timeout, attempt {attempt + 1}/3")
                    if attempt < 2:
                        continue
                    raise
            # All retries exhausted without raising (shouldn't reach here)
            return {
                "title": "Spotify Track",
                "type": self._detect_url_type(url),
                "thumbnail": "",
                "original_url": url,
                "id": self._extract_spotify_id(url),
            }
        except _REQUEST_EXCEPTION as e:
            logger.error(f"[SPOTIFY_DOWNLOADER] OEmbed request failed: {e}")
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Spotify", "metadata extraction", str(e), url
                )
            return {
                "title": "Spotify Track",
                "type": self._detect_url_type(url),
                "thumbnail": "",
                "original_url": url,
                "id": self._extract_spotify_id(url),
            }
        except Exception as e:
            logger.error(f"[SPOTIFY_DOWNLOADER] Metadata extraction error: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Spotify metadata extraction", "Spotify")
            return {
                "title": "Spotify Track",
                "type": self._detect_url_type(url),
                "thumbnail": "",
                "original_url": url,
                "id": self._extract_spotify_id(url),
            }

    @staticmethod
    def _parse_artist_track(title: str) -> tuple[str, str]:
        """Parse artist and track name from Spotify title.

        Common formats:
        - "Artist - Track Name"
        - "Artist · Track Name"
        - "Track Name by Artist"

        Args:
            title: Spotify title

        Returns:
            Tuple of (artist, track)
        """
        if dash_match := re.match(r"^([^·–-]+)[·–-]+(.+)$", title):
            return dash_match.group(1).strip(), dash_match.group(2).strip()

        if by_match := re.match(r"^(.+)\s+by\s+(.+)$", title, re.IGNORECASE):
            return by_match.group(2).strip(), by_match.group(1).strip()

        return "", title

    def _scrape_playlist_tracks(self, url: str) -> list[dict[str, str]]:
        """Fetch a playlist/album track list via Spotify's public embed JSON.

        The embed page (https://open.spotify.com/embed/<type>/<id>) ships a
        ``__NEXT_DATA__`` JSON blob containing the full track list — no API key
        required and stable, unlike scraping the JS-rendered main SPA (which
        matched ``div[role=row]`` that never exist server-side and returned []).
        """
        url_type = self._detect_url_type(url)
        content_id = self._extract_spotify_id(url)
        if not content_id or url_type not in ("album", "playlist"):
            return []

        embed_url = f"https://open.spotify.com/embed/{url_type}/{content_id}"
        try:
            logger.info(f"[SPOTIFY_DOWNLOADER] Fetching embed JSON: {embed_url}")
            response = requests.get(
                embed_url,
                timeout=self.default_timeout,
                headers={"User-Agent": self.config.network.user_agent},
                proxies=get_request_proxies(self.config),
            )
            response.raise_for_status()
        except _REQUEST_EXCEPTION as e:
            logger.error(f"[SPOTIFY_DOWNLOADER] Embed fetch failed: {e}")
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Spotify", "playlist scraping", str(e), url
                )
            return []

        data = self._extract_next_data(response.text)
        if data is None:
            logger.warning("[SPOTIFY_DOWNLOADER] No __NEXT_DATA__ JSON in embed page")
            return []

        tracks: list[dict[str, str]] = []
        for i, item in enumerate(self._find_track_list(data)):
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            artist = str(item.get("subtitle") or "").strip()
            display = f"{artist} - {title}" if artist else title
            tracks.append(
                {
                    "title": display,
                    "artist": artist,
                    "track": title,
                    "position": str(i + 1),
                }
            )

        logger.info(f"[SPOTIFY_DOWNLOADER] Parsed {len(tracks)} tracks from embed JSON")
        return tracks

    @staticmethod
    def _extract_next_data(html: str) -> Any | None:
        """Extract and parse the __NEXT_DATA__ JSON blob from embed HTML."""
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _find_track_list(data: Any) -> list[dict[str, Any]]:
        """Recursively locate the first non-empty ``trackList`` array."""
        stack: list[Any] = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                track_list = node.get("trackList")
                if isinstance(track_list, list) and track_list:
                    return [t for t in track_list if isinstance(t, dict)]
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
        return []

    def _search_youtube(self, artist: str, track: str) -> list[dict[str, Any]]:
        """Search YouTube for matching videos.

        Args:
            artist: Artist name
            track: Track name

        Returns:
            List of YouTube search results
        """
        try:
            max_results = self.max_search_results
            query_format = self.config.spotify.youtube_search_format
            query = query_format.format(max=max_results, artist=artist, track=track)

            logger.debug(f"[SPOTIFY_DOWNLOADER] YouTube search query: {query}")

            for attempt in range(3):
                try:
                    with yt_dlp.YoutubeDL(
                        {
                            "quiet": True,
                            "no_warnings": True,
                            "extract_flat": "in_playlist",
                            "playlistend": max_results,
                            "socket_timeout": 30,
                            "retries": 3,
                        }
                    ) as ydl:
                        results = ydl.extract_info(query, download=False)
                        return list(results.get("entries", []))  # type: ignore[arg-type]
                except Exception as e:
                    if attempt < 2:
                        logger.warning(
                            f"[SPOTIFY_DOWNLOADER] YouTube search retry {attempt + 1}/3: {e}"
                        )
                        continue
                    raise
            return []  # All retries exhausted without raising

        except Exception as e:
            logger.error(f"[SPOTIFY_DOWNLOADER] YouTube search failed: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "YouTube search", "Spotify")
            return []

    def _calculate_similarity(self, spotify_track: str, youtube_title: str) -> float:
        """Calculate similarity score between Spotify track and YouTube title.

        Args:
            spotify_track: Spotify track name
            youtube_title: YouTube video title

        Returns:
            Similarity score (0.0 to 1.0)
        """
        spotify_lower = spotify_track.lower()
        youtube_lower = youtube_title.lower()

        common_words = {
            "official",
            "video",
            "music",
            "audio",
            "lyrics",
            "hd",
            "remix",
            "live",
            "version",
            "feat",
            "ft",
        }

        spotify_words = [w for w in spotify_lower.split() if w not in common_words]
        youtube_words = [w for w in youtube_lower.split() if w not in common_words]

        if not spotify_words or not youtube_words:
            return 0.0

        matcher = SequenceMatcher(None, " ".join(spotify_words), " ".join(youtube_words))
        return matcher.ratio()

    def _select_best_match(
        self, spotify_track: str, search_results: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Select best YouTube match based on similarity score.

        Args:
            spotify_track: Spotify track name
            search_results: YouTube search results

        Returns:
            Best matching YouTube result or None
        """
        threshold = self.min_similarity_threshold
        best_match = None
        best_score = 0.0

        for result in search_results:
            youtube_title = result.get("title", "")
            score = self._calculate_similarity(spotify_track, youtube_title)

            youtube_lower = youtube_title.lower()

            if "official" in youtube_lower:
                score += 0.1

            if "audio" in youtube_lower:
                score += 0.05

            if "music" in youtube_lower:
                score += 0.05

            if score > best_score and score >= threshold:
                best_score = score
                best_match = result

        return best_match

    def get_metadata(self, url: str) -> dict[str, Any]:
        """Get Spotify metadata for URL.

        Args:
            url: Spotify URL

        Returns:
            Dictionary with metadata
        """
        metadata = self._extract_spotify_metadata(url)

        if metadata.get("type", "unknown") in ("album", "playlist"):
            tracks = self._scrape_playlist_tracks(url)
            metadata["tracks"] = tracks

        return metadata

    def get_search_results(self, artist: str, track: str) -> list[dict[str, Any]]:
        """Get YouTube search results for a track.

        Args:
            artist: Artist name
            track: Track name

        Returns:
            List of YouTube search results
        """
        return self._search_youtube(artist, track)

    @staticmethod
    def _extract_youtube_url(result: dict[str, Any]) -> str | None:
        """Extract a playable YouTube URL from a search result entry."""
        webpage_url = result.get("webpage_url")
        if isinstance(webpage_url, str) and webpage_url:
            return webpage_url

        direct_url = result.get("url")
        if isinstance(direct_url, str) and direct_url.startswith(("http://", "https://")):
            return direct_url

        video_id = result.get("id")
        if isinstance(video_id, str) and video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

        return None

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download Spotify track by matching and downloading from YouTube."""
        metadata = self._extract_spotify_metadata(url)
        title = str(metadata.get("title", "")).strip()

        artist, track = self._parse_artist_track(title)
        if not track:
            track = title
        if not track:
            error_msg = "Could not determine Spotify track name"
            logger.error(f"[SPOTIFY_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Spotify", "download", error_msg, url)
            return False

        if not (search_results := self._search_youtube(artist, track)):
            error_msg = "No YouTube results found for Spotify track"
            logger.error(f"[SPOTIFY_DOWNLOADER] {error_msg}: artist={artist!r}, track={track!r}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Spotify", "download", error_msg, url)
            return False

        match_key = f"{artist} {track}".strip()
        best_match = (
            self._select_best_match(match_key or track, search_results) or search_results[0]
        )
        if not (youtube_url := self._extract_youtube_url(best_match)):
            error_msg = "YouTube search did not return a playable URL"
            logger.error(f"[SPOTIFY_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Spotify", "download", error_msg, url)
            return False

        logger.info(
            "[SPOTIFY_DOWNLOADER] Matched Spotify track to YouTube URL: %s",
            youtube_url,
        )

        try:
            yt_downloader = YouTubeDownloader(
                quality="lowest",
                audio_only=True,
                download_thumbnail=False,
                embed_metadata=True,
                error_handler=self.error_handler,
                file_service=self.file_service,
                config=self.config,
                cookie_handler=self.cookie_handler,
                auto_cookie_manager=self.auto_cookie_manager,
            )
            return yt_downloader.download(youtube_url, save_path, progress_callback)
        except Exception as e:
            logger.error(f"[SPOTIFY_DOWNLOADER] Download failed: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Spotify direct download", "Spotify")
            return False
