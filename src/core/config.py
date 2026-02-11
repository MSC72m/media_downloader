import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class CookieConfig(BaseModel):
    storage_dir: Path = Field(
        default_factory=lambda: Path.home() / ".media_downloader",
        description="Directory to store cookies and state files",
    )
    cookie_file_name: str = Field(default="cookies.json", description="Cookie JSON file name")
    netscape_file_name: str = Field(
        default="cookies.txt", description="Netscape format cookie file name"
    )
    state_file_name: str = Field(default="cookie_state.json", description="Cookie state file name")
    cookie_expiry_hours: int = Field(default=8, description="Cookie expiry time in hours")
    generation_timeout: int = Field(default=20, description="Cookie generation timeout in seconds")
    wait_after_load: float = Field(default=1.0, description="Wait time after page load in seconds")
    wait_for_network_idle: float = Field(
        default=5.0, description="Wait time for network idle in seconds"
    )
    scroll_delay: float = Field(
        default=0.5, description="Delay after scroll interaction in seconds"
    )
    viewport_width: int = Field(default=412, description="Browser viewport width (Android mobile)")
    viewport_height: int = Field(
        default=915, description="Browser viewport height (Android mobile)"
    )


class PathConfig(BaseModel):
    downloads_dir: Path = Field(
        default_factory=lambda: Path.home() / "Downloads",
        description="Default downloads directory",
    )
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".media_downloader",
        description="Application configuration directory",
    )

    @field_validator("downloads_dir", "config_dir", mode="before")
    @classmethod
    def validate_path(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class DownloadConfig(BaseModel):
    """Download-related configuration."""

    max_concurrent_downloads: int = Field(default=1, description="Maximum concurrent downloads")
    retry_count: int = Field(default=3, description="Number of retries for failed downloads")
    retry_delay: float = Field(default=3.0, description="Delay between retries in seconds")
    socket_timeout: int = Field(default=15, description="Socket timeout in seconds")
    chunk_size: int = Field(default=8192, description="Download chunk size in bytes")
    thread_sleep_interval: float = Field(
        default=0.1, description="Thread sleep interval in seconds"
    )
    default_timeout: int = Field(default=10, description="Default download timeout in seconds")
    kb_to_bytes: int = Field(default=1024, description="KB to bytes conversion constant")


class NetworkConfig(BaseModel):
    """Network-related configuration."""

    default_timeout: int = Field(default=10, description="Default network timeout in seconds")
    twitter_api_timeout: int = Field(default=10, description="Twitter API timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="Default user agent string",
    )
    cookie_user_agent: str = Field(
        default="Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        description="User agent for cookie generation (Android mobile)",
    )
    minimal_user_agent: str = Field(
        default="Mozilla/5.0", description="Minimal user agent for basic requests"
    )
    service_domains: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "youtube": ["youtube.com", "youtu.be", "www.youtube.com", "music.youtube.com"],
            "twitter": ["twitter.com", "x.com", "www.twitter.com", "www.x.com"],
            "instagram": ["instagram.com", "www.instagram.com"],
            "pinterest": ["pinterest.com", "www.pinterest.com", "pin.it"],
            "soundcloud": ["soundcloud.com", "www.soundcloud.com"],
            "tiktok": ["tiktok.com", "www.tiktok.com", "vm.tiktok.com"],
            "radiojavan": ["play.radiojavan.com", "radiojavan.com", "rj.app"],
            "spotify": ["open.spotify.com", "spotify.com", "spotify.link"],
        },
        description="Service domain mappings (deprecated - use services.service_types)",
    )


class NotificationTemplatesConfig(BaseModel):
    """Notification message templates for handlers."""

    youtube: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "cookies_generating": {
                "text": "YouTube cookies are being generated. Please wait a moment and try again.",
                "title": "YouTube Cookies Generating",
                "level": "INFO",
            },
            "cookies_unavailable": {
                "text": "YouTube cookies are not available. Some videos may fail to download.",
                "title": "YouTube Cookies Unavailable",
                "level": "WARNING",
            },
            "service_unavailable": {
                "text": "YouTube service is temporarily unavailable. Please try again later.",
                "title": "YouTube Service Unavailable",
                "level": "ERROR",
            },
        },
        description="YouTube notification templates",
    )

    instagram: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "authenticating": {
                "text": "Instagram authentication is in progress. Please wait a moment and try again.",
                "title": "Instagram Authentication",
                "level": "INFO",
            },
            "authentication_required": {
                "text": "Instagram authentication is required to download content.",
                "title": "Instagram Authentication Required",
                "level": "INFO",
            },
        },
        description="Instagram notification templates",
    )

    twitter: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "service_unavailable": {
                "text": "Twitter service is temporarily unavailable. Please try again later.",
                "title": "Twitter Service Unavailable",
                "level": "ERROR",
            }
        },
        description="Twitter notification templates",
    )

    pinterest: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "service_unavailable": {
                "text": "Pinterest service is temporarily unavailable. Please try again later.",
                "title": "Pinterest Service Unavailable",
                "level": "ERROR",
            }
        },
        description="Pinterest notification templates",
    )

    soundcloud: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "service_unavailable": {
                "text": "SoundCloud service is temporarily unavailable. Please try again later.",
                "title": "SoundCloud Service Unavailable",
                "level": "ERROR",
            }
        },
        description="SoundCloud notification templates",
    )

    radiojavan: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "service_unavailable": {
                "text": "Radio Javan service is temporarily unavailable. Please try again later.",
                "title": "Radio Javan Service Unavailable",
                "level": "ERROR",
            }
        },
        description="Radio Javan notification templates",
    )

    tiktok: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "service_unavailable": {
                "text": "TikTok service is temporarily unavailable. Please try again later.",
                "title": "TikTok Service Unavailable",
                "level": "ERROR",
            }
        },
        description="TikTok notification templates",
    )

    spotify: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "no_match_found": {
                "text": "Could not find a matching video on YouTube. Try searching manually.",
                "title": "No YouTube Match Found",
                "level": "WARNING",
            },
            "metadata_extraction_failed": {
                "text": "Failed to extract Spotify metadata. Check URL and try again.",
                "title": "Metadata Extraction Failed",
                "level": "ERROR",
            },
            "playlist_processing": {
                "text": "Processing {count} tracks from playlist...",
                "title": "Processing Playlist",
                "level": "INFO",
            },
        },
        description="Spotify notification templates",
    )


class YouTubeConfig(BaseModel):
    """YouTube-specific configuration."""

    player_client: str = Field(default="web", description="Default YouTube player client")
    metadata_timeout: int = Field(default=30, description="Metadata fetch timeout in seconds")
    fallback_timeout: int = Field(default=20, description="Fallback command timeout in seconds")
    subtitle_timeout: int = Field(default=5, description="Subtitle fetch timeout in seconds")
    client_fallback_timeout: int = Field(
        default=15, description="Client fallback timeout in seconds"
    )
    retry_sleep_multiplier: int = Field(
        default=3, description="Retry sleep multiplier for fragment retries"
    )
    default_quality: str = Field(default="720p", description="Default video quality")
    supported_qualities: list[str] = Field(
        default_factory=lambda: [
            "144p",
            "240p",
            "360p",
            "480p",
            "720p",
            "1080p",
            "1440p",
            "4K",
            "8K",
        ],
        description="Supported video quality options",
    )
    video_qualities: list[str] = Field(
        default_factory=lambda: ["best", "1080p", "720p", "480p", "360p"],
        description="Video quality options for video formats",
    )
    quality_format_map: dict[str, str] = Field(
        default_factory=lambda: {
            "best": "best",
            "highest": "best",
            "lowest": "worst",
            "192": "192",  # Audio quality
        },
        description="Quality to format mapping",
    )
    file_extensions: dict[str, str] = Field(
        default_factory=lambda: {
            "video": ".mp4",
            "audio": ".mp3",
        },
        description="File extensions by format type",
    )
    audio_codec: str = Field(default="mp3", description="Default audio codec")
    playlist_item_limit: str = Field(default="1", description="Playlist item limit (single item)")
    default_retry_wait: int = Field(default=3, description="Default retry wait time in seconds")
    ytdlp_default_options: dict[str, Any] = Field(
        default_factory=lambda: {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "extract_flat": "discard_in_playlist",
            "playlistend": 1,
            "writeinfojson": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "skip_download": True,
        },
        description="Default yt-dlp options for metadata fetching",
    )
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
            r"^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+",
            r"^https?://(?:www\.)?youtu\.be/[\w-]+",
            r"^https?://(?:www\.)?youtube\.com/embed/[\w-]+",
            r"^https?://(?:www\.)?youtube\.com/v/[\w-]+",
            r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
            r"^https?://music\.youtube\.com/watch\?v=[\w-]+",
            r"^https?://music\.youtube\.com/playlist\?list=[\w-]+",
        ],
        description="YouTube URL validation patterns",
    )
    youtube_domains: list[str] = Field(
        default_factory=lambda: ["www.youtube.com", "youtube.com", "youtu.be"],
        description="Valid YouTube domain names",
    )
    supported_languages: dict[str, str] = Field(
        default_factory=lambda: {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "fa": "Persian",
            "nl": "Dutch",
            "pl": "Polish",
            "tr": "Turkish",
            "vi": "Vietnamese",
            "th": "Thai",
            "id": "Indonesian",
            "sv": "Swedish",
            "no": "Norwegian",
            "da": "Danish",
            "fi": "Finnish",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "el": "Greek",
            "he": "Hebrew",
            "uk": "Ukrainian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mt": "Maltese",
            "ga": "Irish",
            "cy": "Welsh",
            "eu": "Basque",
            "ca": "Catalan",
            "gl": "Galician",
            "sr": "Serbian",
            "mk": "Macedonian",
            "sq": "Albanian",
            "bs": "Bosnian",
            "is": "Icelandic",
            "ms": "Malay",
            "tl": "Tagalog",
            "sw": "Swahili",
            "af": "Afrikaans",
            "zu": "Zulu",
            "xh": "Xhosa",
            "bn": "Bengali",
            "ta": "Tamil",
            "te": "Telugu",
            "ml": "Malayalam",
            "kn": "Kannada",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "ur": "Urdu",
            "ne": "Nepali",
            "si": "Sinhala",
            "my": "Myanmar",
            "km": "Khmer",
            "lo": "Lao",
            "ka": "Georgian",
            "hy": "Armenian",
            "az": "Azerbaijani",
            "kk": "Kazakh",
            "ky": "Kyrgyz",
            "uz": "Uzbek",
            "mn": "Mongolian",
            "be": "Belarusian",
        },
        description="Language code to name mapping",
    )


class TwitterConfig(BaseModel):
    """Twitter/X-specific configuration."""

    default_timeout: int = Field(default=10, description="Default request timeout in seconds")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?twitter\.com/[\w]+/status/[\d]+",
            r"^https?://(?:www\.)?x\.com/[\w]+/status/[\d]+",
            r"^https?://(?:www\.)?twitter\.com/i/spaces/[\w]+",
            r"^https?://(?:www\.)?x\.com/i/spaces/[\w]+",
            r"^https?://(?:mobile\.)?twitter\.com/[\w]+/status/[\d]+",
            r"^https?://(?:mobile\.)?x\.com/[\w]+/status/[\d]+",
        ],
        description="Twitter/X URL validation patterns",
    )


class InstagramConfig(BaseModel):
    """Instagram-specific configuration."""

    max_login_attempts: int = Field(default=3, description="Maximum login attempts")
    login_cooldown_seconds: int = Field(
        default=600, description="Cooldown period after max login attempts in seconds"
    )
    default_timeout: int = Field(default=10, description="Default request timeout in seconds")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?instagram\.com/p/[\w-]+",
            r"^https?://(?:www\.)?instagram\.com/reel/[\w-]+",
            r"^https?://(?:www\.)?instagram\.com/stories/[\w-]+",
            r"^https?://(?:www\.)?instagram\.com/tv/[\w-]+",
            r"^https?://(?:www\.)?instagram\.com/[\w]+/p/[\w-]+",
            r"^https?://(?:www\.)?instagram\.com/[\w]+/reel/[\w-]+",
        ],
        description="Instagram URL validation patterns",
    )


class PinterestConfig(BaseModel):
    """Pinterest-specific configuration."""

    default_timeout: int = Field(default=10, description="Default request timeout in seconds")
    oembed_timeout: int = Field(default=10, description="OEmbed API timeout in seconds")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?pinterest\.com/pin/[\d]+",
            r"^https?://(?:www\.)?pinterest\.com/[\w]+/[\w-]+/[\d]+",
            r"^https?://(?:www\.)?pin\.it/[\w]+",
            r"^https?://(?:www\.)?pinterest\.com\.au/pin/[\d]+",
            r"^https?://(?:www\.)?pinterest\.ca/pin/[\d]+",
            r"^https?://(?:www\.)?pinterest\.co\.uk/pin/[\d]+",
            r"^https?://(?:www\.)?pinterest\.de/pin/[\d]+",
            r"^https?://(?:www\.)?pinterest\.fr/pin/[\d]+",
        ],
        description="Pinterest URL validation patterns",
    )


class SoundCloudConfig(BaseModel):
    """SoundCloud-specific configuration."""

    default_retries: int = Field(default=3, description="Default number of retries")
    socket_timeout: int = Field(default=15, description="Socket timeout in seconds")
    default_audio_format: str = Field(default="mp3", description="Default audio format")
    default_audio_quality: str = Field(default="best", description="Default audio quality")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+",
            r"^https?://(?:www\.)?soundcloud\.com/[\w-]+/sets/[\w-]+",
            r"^https?://(?:m\.)?soundcloud\.com/[\w-]+/[\w-]+",
            r"^https?://(?:m\.)?soundcloud\.com/[\w-]+/sets/[\w-]+",
            r"^https?://soundcloud\.app\.goo\.gl/[\w]+",
        ],
        description="SoundCloud URL validation patterns",
    )


class RadioJavanConfig(BaseModel):
    """Radio Javan-specific configuration."""

    default_timeout: int = Field(default=30, description="Default request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?play\.radiojavan\.com/(?:mp3|mp4|song)/[\w-]+",
            r"^https?://(?:www\.)?radiojavan\.com/artist/[\w-]+/songs",
            r"^https?://(?:www\.)?radiojavan\.com/mp3s/mp3/[\w-]+",
            r"^https?://(?:www\.)?radiojavan\.com/videos/video/[\w-]+",
            r"^https?://rj\.app/[\w-]+",
            r"^https?://(?:www\.)?radiojavan\.com/(?:mp3|mp4|song)/[\w-]+",
        ],
        description="Radio Javan URL validation patterns",
    )

    # These config options map to real API and CDN patterns
    api_base_url: str = Field(
        default="https://www.radiojavan.com/api2", description="Radio Javan API base URL"
    )
    cdn_hosts: list[str] = Field(
        default_factory=lambda: [
            "www.radiojavan.com",
            "rj1.media",
            "rj2.media",
            "rj3.media",
            "rjmedia.app",
            "rj.app",
        ],
        description="Available CDN hosts",
    )
    media_type_paths: dict[str, str] = Field(
        default_factory=lambda: {
            "mp3": "/mp3/{media_name}",
            "mp4": "/mp4/{media_name}",
        },
        description="Media type URL path patterns",
    )


class TikTokConfig(BaseModel):
    """TikTok-specific configuration."""

    default_timeout: int = Field(default=10, description="Default request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:www\.)?tiktok\.com/[@\w]+/video/[\d]+",
            r"^https?://(?:vm\.)?tiktok\.com/[\w-]+",
            r"^https?://(?:www\.)?tiktok\.com/t/[\w-]+",
        ],
        description="TikTok URL validation patterns",
    )


class SpotifyConfig(BaseModel):
    """Spotify-specific configuration."""

    default_timeout: int = Field(default=10, description="Default request timeout in seconds")
    oembed_timeout: int = Field(default=10, description="OEmbed API timeout in seconds")
    max_search_results: int = Field(default=5, description="Maximum YouTube search results")
    min_similarity_threshold: float = Field(
        default=0.5, description="Minimum similarity score (0-1)"
    )
    youtube_search_format: str = Field(
        default="ytsearch{max}:{artist} - {track}", description="YouTube search query format"
    )
    default_audio_quality: str = Field(default="best", description="Default audio quality")
    url_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^https?://(?:open\.)?spotify\.com/track/[\w-]+",
            r"^https?://(?:open\.)?spotify\.com/album/[\w-]+",
            r"^https?://(?:open\.)?spotify\.com/playlist/[\w-]+",
            r"^https?://(?:open\.)?spotify\.com/artist/[\w-]+",
            r"^spotify:(track|album|playlist|artist|episode|show):[\w-]+$",
            r"^https?://(?:spotify\.link|song\.link|album\.link|playlist\.link)/[\w-]+",
        ],
        description="Spotify URL validation patterns",
    )


class ServiceConfig(BaseModel):
    """Centralized service configuration for agnostic service handling.

    This configuration:
    - Centralizes all service data (URL patterns, domains, handler/downloader paths)
    - Enables dynamic service registration and detection
    - Follows Open/Closed Principle (adding services only requires config update)
    """

    youtube: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "youtube",
            "url_patterns": [
                r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
                r"^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+",
                r"^https?://(?:www\.)?youtu\.be/[\w-]+",
                r"^https?://(?:www\.)?youtube\.com/embed/[\w-]+",
                r"^https?://(?:www\.)?youtube\.com/v/[\w-]+",
                r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
                r"^https?://music\.youtube\.com/watch\?v=[\w-]+",
                r"^https?://music\.youtube\.com/playlist\?list=[\w-]+",
            ],
            "domains": ["youtube.com", "youtu.be", "www.youtube.com"],
            "downloader_module": "src.services.youtube.downloader",
            "downloader_class": "YouTubeDownloader",
            "handler_module": "src.handlers.youtube_handler",
            "handler_class": "YouTubeHandler",
        },
        description="YouTube service configuration",
    )

    twitter: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "twitter",
            "url_patterns": [
                r"^https?://(?:www\.)?twitter\.com/[\w]+/status/[\d]+",
                r"^https?://(?:www\.)?x\.com/[\w]+/status/[\d]+",
                r"^https?://(?:www\.)?twitter\.com/i/spaces/[\w]+",
                r"^https?://(?:www\.)?x\.com/i/spaces/[\w]+",
                r"^https?://(?:mobile\.)?twitter\.com/[\w]+/status/[\d]+",
                r"^https?://(?:mobile\.)?x\.com/[\w]+/status/[\d]+",
            ],
            "domains": ["twitter.com", "x.com", "api.x.com", "mobile.x.com"],
            "downloader_module": "src.services.twitter.downloader",
            "downloader_class": "TwitterDownloader",
            "handler_module": "src.handlers.twitter_handler",
            "handler_class": "TwitterHandler",
        },
        description="Twitter/X service configuration",
    )

    instagram: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "instagram",
            "url_patterns": [
                r"^https?://(?:www\.)?instagram\.com/p/[\w-]+",
                r"^https?://(?:www\.)?instagram\.com/reel/[\w-]+",
                r"^https?://(?:www\.)?instagram\.com/stories/[\w-]+",
                r"^https?://(?:www\.)?instagram\.com/tv/[\w-]+",
                r"^https?://(?:www\.)?instagram\.com/[\w]+/p/[\w-]+",
                r"^https?://(?:www\.)?instagram\.com/[\w]+/reel/[\w-]+",
            ],
            "domains": ["instagram.com", "www.instagram.com", "m.instagram.com"],
            "downloader_module": "src.services.instagram.downloader",
            "downloader_class": "InstagramDownloader",
            "handler_module": "src.handlers.instagram_handler",
            "handler_class": "InstagramHandler",
        },
        description="Instagram service configuration",
    )

    pinterest: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "pinterest",
            "url_patterns": [
                r"^https?://(?:www\.)?pinterest\.com/pin/[\d]+",
                r"^https?://(?:www\.)?pinterest\.com/[\w]+/[\w-]+/[\d]+",
                r"^https?://(?:www\.)?pin\.it/[\w-]+",
                r"^https?://(?:www\.)?pinterest\.com\.au/pin/[\d]+",
                r"^https?://(?:www\.)?pinterest\.ca/pin/[\d]+",
                r"^https?://(?:www\.)?pinterest\.co\.uk/pin/[\d]+",
                r"^https?://(?:www\.)?pinterest\.de/pin/[\d]+",
                r"^https?://(?:www\.)?pinterest\.fr/pin/[\d]+",
            ],
            "domains": ["pinterest.com", "www.pinterest.com"],
            "downloader_module": "src.services.pinterest.downloader",
            "downloader_class": "PinterestDownloader",
            "handler_module": "src.handlers.pinterest_handler",
            "handler_class": "PinterestHandler",
        },
        description="Pinterest service configuration",
    )

    soundcloud: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "soundcloud",
            "url_patterns": [
                r"^https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+",
                r"^https?://(?:www\.)?soundcloud\.com/[\w-]+/sets/[\w-]+",
                r"^https?://(?:m\.)?soundcloud\.com/[\w-]+/[\w-]+",
                r"^https?://(?:m\.)?soundcloud\.com/[\w-]+/sets/[\w-]+",
                r"^https?://soundcloud\.app\.goo\.gl/[\w]+",
            ],
            "domains": ["soundcloud.com", "www.soundcloud.com"],
            "downloader_module": "src.services.soundcloud.downloader",
            "downloader_class": "SoundCloudDownloader",
            "handler_module": "src.handlers.soundcloud_handler",
            "handler_class": "SoundCloudHandler",
        },
        description="SoundCloud service configuration",
    )

    tiktok: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "tiktok",
            "url_patterns": [
                r"^https?://(?:www\.)?tiktok\.com/[@\w]+/video/[\d]+",
                r"^https?://(?:vm\.)?tiktok\.com/[\w-]+",
                r"^https?://(?:www\.)?tiktok\.com/t/[\w-]+",
            ],
            "domains": ["tiktok.com", "vm.tiktok.com", "www.tiktok.com"],
            "downloader_module": "src.services.tiktok.downloader",
            "downloader_class": "TikTokDownloader",
            "handler_module": "src.handlers.tiktok_handler",
            "handler_class": "TikTokHandler",
        },
        description="TikTok service configuration",
    )

    radiojavan: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "radiojavan",
            "url_patterns": [
                r"^https?://(?:www\.)?play\.radiojavan\.com/(?:mp3|mp4)/[\w-]+",
                r"^https?://(?:www\.)?radiojavan\.com/artist/[\w-]+/songs",
                r"^https?://(?:www\.)?radiojavan\.com/mp3s/mp3/[\w-]+",
                r"^https?://(?:www\.)?radiojavan\.com/videos/video/[\w-]+",
                r"^https?://rj\.app/[\w-]+",
                r"^https?://(?:www\.)?radiojavan\.com/(?:mp3|mp4)/[\w-]+",
            ],
            "domains": ["play.radiojavan.com", "radiojavan.com", "rj.app"],
            "downloader_module": "src.services.radiojavan.downloader",
            "downloader_class": "RadioJavanDownloader",
            "handler_module": "src.handlers.radiojavan_handler",
            "handler_class": "RadioJavanHandler",
        },
        description="Radio Javan service configuration",
    )

    spotify: dict[str, Any] = Field(
        default_factory=lambda: {
            "service_type": "spotify",
            "url_patterns": [
                r"^https?://(?:open\.)?spotify\.com/track/[\w-]+",
                r"^https?://(?:open\.)?spotify\.com/album/[\w-]+",
                r"^https?://(?:open\.)?spotify\.com/playlist/[\w-]+",
                r"^https?://(?:open\.)?spotify\.com/artist/[\w-]+",
                r"^spotify:(track|album|playlist|artist|episode|show):[\w-]+$",
                r"^https?://(?:spotify\.link|song\.link|album\.link|playlist\.link)/[\w-]+",
            ],
            "domains": ["open.spotify.com", "spotify.com", "spotify.link"],
            "downloader_module": "src.services.spotify.downloader",
            "downloader_class": "SpotifyDownloader",
            "handler_module": "src.handlers.spotify_handler",
            "handler_class": "SpotifyHandler",
        },
        description="Spotify service configuration",
    )

    @property
    def all_services(self) -> dict[str, dict[str, Any]]:
        """Get all service configurations as a dictionary."""
        return {
            "youtube": self.youtube,
            "twitter": self.twitter,
            "instagram": self.instagram,
            "pinterest": self.pinterest,
            "soundcloud": self.soundcloud,
            "tiktok": self.tiktok,
            "radiojavan": self.radiojavan,
            "spotify": self.spotify,
        }

    @property
    def service_types(self) -> dict[str, str]:
        """Map domain to service type."""
        return {
            **dict.fromkeys(self.youtube["domains"], "youtube"),
            **dict.fromkeys(self.twitter["domains"], "twitter"),
            **dict.fromkeys(self.instagram["domains"], "instagram"),
            **dict.fromkeys(self.pinterest["domains"], "pinterest"),
            **dict.fromkeys(self.soundcloud["domains"], "soundcloud"),
            **dict.fromkeys(self.tiktok["domains"], "tiktok"),
            **dict.fromkeys(self.radiojavan["domains"], "radiojavan"),
            **dict.fromkeys(self.spotify["domains"], "spotify"),
        }


class ThemeConfig(BaseModel):
    """Theme configuration for the application UI."""

    appearance_mode: str = Field(default="dark", description="Appearance mode (light/dark/system)")
    color_theme: str = Field(default="blue", description="Color theme (blue/green/red/purple)")
    theme_persistence: bool = Field(default=True, description="Whether to persist theme changes")

    @field_validator("appearance_mode", mode="before")
    @classmethod
    def validate_appearance_mode(cls, v):
        """Validate appearance mode value."""
        if isinstance(v, AppearanceMode):
            return v.value
        return v

    @field_validator("color_theme", mode="before")
    @classmethod
    def validate_color_theme(cls, v):
        """Validate color theme value."""
        if isinstance(v, ColorTheme):
            return v.value
        return v

    @property
    def appearance_mode_enum(self) -> AppearanceMode:
        """Get appearance mode as enum."""
        return AppearanceMode(self.appearance_mode)

    @property
    def color_theme_enum(self) -> ColorTheme:
        """Get color theme as enum."""
        return ColorTheme(self.color_theme)

    @staticmethod
    def get_color_schemes() -> dict[str, dict[str, Any]]:
        """Get all color schemes for themes."""
        return {
            "light_blue": {
                "fg_color": ["#CCE6FF", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#007BFF", "#0056b3"],
                "button_hover_color": ["#0056b3", "#003d82"],
                "border_color": ["#007BFF", "#0056b3"],
            },
            "dark_blue": {
                "fg_color": ["#1A2332", "#243447"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#007BFF", "#0056b3"],
                "button_hover_color": ["#0056b3", "#003d82"],
                "border_color": ["#007BFF", "#0056b3"],
            },
            "light_green": {
                "fg_color": ["#D4EDDA", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#28A745", "#1E7E34"],
                "button_hover_color": ["#1E7E34", "#155724"],
                "border_color": ["#28A745", "#1E7E34"],
            },
            "dark_green": {
                "fg_color": ["#1A2E1A", "#243424"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#28A745", "#1E7E34"],
                "button_hover_color": ["#1E7E34", "#155724"],
                "border_color": ["#28A745", "#1E7E34"],
            },
            "light_red": {
                "fg_color": ["#F8D7DA", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#DC3545", "#C82333"],
                "button_hover_color": ["#C82333", "#A71E2A"],
                "border_color": ["#DC3545", "#C82333"],
            },
            "dark_red": {
                "fg_color": ["#2E1A1A", "#342424"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#DC3545", "#C82333"],
                "button_hover_color": ["#C82333", "#A71E2A"],
                "border_color": ["#DC3545", "#C82333"],
            },
            "light_purple": {
                "fg_color": ["#E6D7FF", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#6F42C1", "#5A32A3"],
                "button_hover_color": ["#5A32A3", "#4A2790"],
                "border_color": ["#6F42C1", "#5A32A3"],
            },
            "dark_purple": {
                "fg_color": ["#2E1A3A", "#342447"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#6F42C1", "#5A32A3"],
                "button_hover_color": ["#5A32A3", "#4A2790"],
                "border_color": ["#6F42C1", "#5A32A3"],
            },
            "light_orange": {
                "fg_color": ["#FFF3E0", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#FF9800", "#F57C00"],
                "button_hover_color": ["#F57C00", "#E65100"],
                "border_color": ["#FF9800", "#F57C00"],
            },
            "dark_orange": {
                "fg_color": ["#3A2A1A", "#473424"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#FF9800", "#F57C00"],
                "button_hover_color": ["#F57C00", "#E65100"],
                "border_color": ["#FF9800", "#F57C00"],
            },
            "light_teal": {
                "fg_color": ["#E0F2F1", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#009688", "#00796B"],
                "button_hover_color": ["#00796B", "#00695C"],
                "border_color": ["#009688", "#00796B"],
            },
            "dark_teal": {
                "fg_color": ["#1A2E2E", "#243434"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#009688", "#00796B"],
                "button_hover_color": ["#00796B", "#00695C"],
                "border_color": ["#009688", "#00796B"],
            },
            "light_pink": {
                "fg_color": ["#FCE4EC", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#E91E63", "#C2185B"],
                "button_hover_color": ["#C2185B", "#880E4F"],
                "border_color": ["#E91E63", "#C2185B"],
            },
            "dark_pink": {
                "fg_color": ["#3A1A2E", "#472434"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#E91E63", "#C2185B"],
                "button_hover_color": ["#C2185B", "#880E4F"],
                "border_color": ["#E91E63", "#C2185B"],
            },
            "light_indigo": {
                "fg_color": ["#E8EAF6", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#3F51B5", "#303F9F"],
                "button_hover_color": ["#303F9F", "#283593"],
                "border_color": ["#3F51B5", "#303F9F"],
            },
            "dark_indigo": {
                "fg_color": ["#1A1E3A", "#242447"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#3F51B5", "#303F9F"],
                "button_hover_color": ["#303F9F", "#283593"],
                "border_color": ["#3F51B5", "#303F9F"],
            },
            "light_amber": {
                "fg_color": ["#FFF8E1", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#FFC107", "#FFA000"],
                "button_hover_color": ["#FFA000", "#FF6F00"],
                "border_color": ["#FFC107", "#FFA000"],
            },
            "dark_amber": {
                "fg_color": ["#3A2E1A", "#473424"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#FFC107", "#FFA000"],
                "button_hover_color": ["#FFA000", "#FF6F00"],
                "border_color": ["#FFC107", "#FFA000"],
            },
            "light_cyan": {
                "fg_color": ["#E0F7FA", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#00BCD4", "#00ACC1"],
                "button_hover_color": ["#00ACC1", "#0097A7"],
                "border_color": ["#00BCD4", "#00ACC1"],
            },
            "dark_cyan": {
                "fg_color": ["#1A2E3A", "#243447"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#00BCD4", "#00ACC1"],
                "button_hover_color": ["#00ACC1", "#0097A7"],
                "border_color": ["#00BCD4", "#00ACC1"],
            },
            "light_emerald": {
                "fg_color": ["#E8F5E8", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#4CAF50", "#388E3C"],
                "button_hover_color": ["#388E3C", "#2E7D32"],
                "border_color": ["#4CAF50", "#388E3C"],
            },
            "dark_emerald": {
                "fg_color": ["#1A3A1A", "#243424"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#4CAF50", "#388E3C"],
                "button_hover_color": ["#388E3C", "#2E7D32"],
                "border_color": ["#4CAF50", "#388E3C"],
            },
            "light_rose": {
                "fg_color": ["#FFF1F2", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#F43F5E", "#E11D48"],
                "button_hover_color": ["#E11D48", "#BE123C"],
                "border_color": ["#F43F5E", "#E11D48"],
            },
            "dark_rose": {
                "fg_color": ["#3A1A1F", "#472424"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#F43F5E", "#E11D48"],
                "button_hover_color": ["#E11D48", "#BE123C"],
                "border_color": ["#F43F5E", "#E11D48"],
            },
            "light_violet": {
                "fg_color": ["#F3E8FF", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#8B5CF6", "#7C3AED"],
                "button_hover_color": ["#7C3AED", "#6D28D9"],
                "border_color": ["#8B5CF6", "#7C3AED"],
            },
            "dark_violet": {
                "fg_color": ["#2E1A3A", "#342447"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#8B5CF6", "#7C3AED"],
                "button_hover_color": ["#7C3AED", "#6D28D9"],
                "border_color": ["#8B5CF6", "#7C3AED"],
            },
            "light_slate": {
                "fg_color": ["#F8FAFC", "#FFFFFF"],
                "text_color": ["#1A1A1A", "#666666"],
                "button_color": ["#64748B", "#475569"],
                "button_hover_color": ["#475569", "#334155"],
                "border_color": ["#64748B", "#475569"],
            },
            "dark_slate": {
                "fg_color": ["#1A1F2E", "#242434"],
                "text_color": ["#FFFFFF", "#CCCCCC"],
                "button_color": ["#64748B", "#475569"],
                "button_hover_color": ["#475569", "#334155"],
                "border_color": ["#64748B", "#475569"],
            },
        }

    @staticmethod
    def get_theme_json(appearance: AppearanceMode, color: ColorTheme) -> dict[str, Any]:
        """Get CTK theme JSON structure for appearance and color combination."""
        schemes = ThemeConfig.get_color_schemes()
        key = f"{appearance.value}_{color.value}"
        scheme = schemes.get(key, schemes[f"{appearance.value}_blue"])

        # Extract colors - handle both list and string formats
        fg_colors = scheme["fg_color"]
        if isinstance(fg_colors, list):
            fg_color = fg_colors[0]
            top_fg_color = fg_colors[1]
        else:
            fg_color = fg_colors
            top_fg_color = fg_colors

        text_colors = scheme["text_color"]
        if isinstance(text_colors, list):
            text_color = text_colors[0]
            text_color_disabled = text_colors[1]
        else:
            text_color = text_colors
            text_color_disabled = text_colors

        border_colors = scheme.get("border_color", fg_colors)
        border_color = border_colors[0] if isinstance(border_colors, list) else border_colors

        # CTK theme JSON structure
        return {
            "CTk": {
                "fg_color": [fg_color, top_fg_color],
                "top_fg_color": top_fg_color,
                "text_color": [text_color, text_color_disabled],
                "text_color_disabled": text_color_disabled,
                "button_color": scheme["button_color"],
                "button_hover_color": scheme["button_hover_color"],
                "button_border_color": border_color,
                "border_color": [border_color, border_color],
                "border_width": 1,
                "corner_radius": 8,
            },
            "CTkButton": {
                "corner_radius": 12,
                "border_width": 0,
                "fg_color": scheme["button_color"],
                "hover_color": scheme["button_hover_color"],
                "text_color": text_color,
            },
            "CTkEntry": {
                "corner_radius": 12,
                "border_width": 1,
                "fg_color": [fg_color, top_fg_color],
                "border_color": [border_color, border_color],
                "text_color": text_color,
            },
            "CTkFrame": {
                "corner_radius": 12,
                "border_width": 0,
                "fg_color": [fg_color, top_fg_color],
            },
            "CTkLabel": {
                "text_color": text_color,
            },
        }

    def serialize_enums(self) -> dict[str, Any]:
        """Serialize enum values for JSON storage."""
        return {
            "appearance_mode": self.appearance_mode,
            "color_theme": self.color_theme,
            "theme_persistence": self.theme_persistence,
        }


class UIConfig(BaseModel):
    """UI-related configuration."""

    app_title: str = Field(
        default="Media Downloader",
        description="Application title displayed in the header",
    )
    metadata_fetch_timeout: int = Field(
        default=90, description="Metadata fetch dialog timeout in seconds"
    )
    metadata_poll_interval: float = Field(
        default=0.5, description="Polling interval for metadata fetch status in seconds"
    )
    format_options: list[str] = Field(
        default_factory=lambda: ["Video + Audio", "Audio Only", "Video Only"],
        description="Format options for download dialogs",
    )
    message_timeout_seconds: int = Field(
        default=8,
        description="Timeout for status bar messages in seconds (after which shows 'Ready' or next message)",
    )
    error_message_timeout_seconds: int = Field(
        default=15,
        description="Timeout for error messages in seconds (longer than regular messages)",
    )
    loading_dialog_max_dots: int = Field(
        default=3, description="Maximum number of dots in loading dialog before cycling"
    )
    loading_dialog_animation_interval: int = Field(
        default=500,
        description="Milliseconds between dot animation updates in loading dialog",
    )
    subtitle_batch_size: int = Field(
        default=5,
        description="Number of subtitles to load per batch in UI to prevent freezing",
    )
    thumbnail_cache_max_mb: int = Field(
        default=100,
        description="Maximum thumbnail cache size in megabytes",
    )
    thumbnail_cache_max_age_days: int = Field(
        default=30,
        description="Maximum age of cached thumbnails in days",
    )
    theme: ThemeConfig = Field(default_factory=ThemeConfig, description="Theme configuration")


class AppConfig(BaseSettings):
    """Main application configuration.

    Supports YAML and JSON config files. Looks for config.yaml or config.json in:
    1. Current directory
    2. User config directory (~/.media_downloader/)
    3. Environment variables (APP_*)

    Example config file:
        cookies:
          storage_dir: ~/.media_downloader
          cookie_expiry_hours: 8
        downloads:
          max_concurrent_downloads: 3
          retry_count: 3
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        case_sensitive=False,
        env_nested_delimiter="__",
        arbitrary_types_allowed=True,
    )

    cookies: CookieConfig = Field(default_factory=CookieConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    downloads: DownloadConfig = Field(default_factory=DownloadConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    notifications: NotificationTemplatesConfig = Field(default_factory=NotificationTemplatesConfig)
    services: ServiceConfig = Field(default_factory=ServiceConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    instagram: InstagramConfig = Field(default_factory=InstagramConfig)
    pinterest: PinterestConfig = Field(default_factory=PinterestConfig)
    soundcloud: SoundCloudConfig = Field(default_factory=SoundCloudConfig)
    radiojavan: RadioJavanConfig = Field(default_factory=RadioJavanConfig)
    tiktok: TikTokConfig = Field(default_factory=TikTokConfig)
    spotify: SpotifyConfig = Field(default_factory=SpotifyConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @classmethod
    def _load_config_file(cls) -> dict | None:
        """Load configuration from a single YAML or JSON file.

        Priority order:
        1. config.yaml in current directory
        2. config.json in current directory
        3. ~/.media_downloader/config.yaml
        4. ~/.media_downloader/config.json

        Returns:
            Dictionary with config values or None if no file found
        """
        config_dir = Path.home() / ".media_downloader"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Try YAML first, then JSON - single file only
        config_files = [
            Path("config.yaml"),
            Path("config.json"),
            config_dir / "config.yaml",
            config_dir / "config.json",
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, encoding="utf-8") as f:
                        if config_file.suffix in {".yaml", ".yml"}:
                            return yaml.safe_load(f)
                            return json.load(f)
                except Exception as e:
                    logger.debug(f"Error loading config file: {e}")
                    continue

        return None

    @classmethod
    def _settings_customise_sources(
        cls,
        _settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Customize settings sources to include YAML/JSON file."""
        config_dict = cls._load_config_file()

        # Create a settings source from the config file
        def file_settings(_):
            return config_dict or {}

        return (
            init_settings,
            file_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def save_to_file(self) -> None:
        """Save current config to file (JSON or YAML based on existing file).

        Saves to the same file that was loaded, or defaults to ~/.media_downloader/config.json
        """
        config_dir = Path.home() / ".media_downloader"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Find existing config file to determine format
        config_files = [
            Path("config.yaml"),
            Path("config.json"),
            config_dir / "config.yaml",
            config_dir / "config.json",
        ]

        config_file = None
        for file in config_files:
            if file.exists():
                config_file = file
                break

        # Default to JSON in user config directory
        if config_file is None:
            config_file = config_dir / "config.json"

        # Convert to dict, handling Path objects and enums
        # Use mode="json" to properly serialize enums to their values
        config_dict = self.model_dump(mode="json", exclude_none=True, by_alias=False)

        # Convert Path objects to strings
        def convert_paths(obj):
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            if isinstance(obj, Path):
                return str(obj)
            return obj

        config_dict = convert_paths(config_dict)

        # Save to file
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                if config_file.suffix in (".yaml", ".yml"):
                    yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)
                    return
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"[CONFIG] Saved configuration to {config_file}")
            return
        except Exception as e:
            logger.error(f"[CONFIG] Failed to save configuration: {e}", exc_info=True)


_config_instance: AppConfig | None = None


@cache
def get_config() -> AppConfig:
    """Get the singleton configuration instance.

    Returns:
        The application configuration instance
    """
    global _config_instance  # noqa: PLW0603
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance


def set_config(config: AppConfig) -> None:
    """Set the configuration instance (mainly for testing).

    Args:
        config: The configuration instance to set
    """
    global _config_instance  # noqa: PLW0603
    _config_instance = config


def reset_config() -> None:
    """Reset the configuration instance (mainly for testing)."""
    global _config_instance  # noqa: PLW0603
    _config_instance = None
