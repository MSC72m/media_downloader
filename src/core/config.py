"""Application configuration using Pydantic Settings with YAML/JSON file support."""

import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, Field, field_serializer, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class CookieConfig(BaseModel):
    """Cookie-related configuration."""

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
    """Path-related configuration."""

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

    max_concurrent_downloads: int = Field(default=3, description="Maximum concurrent downloads")
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
            "youtube": ["youtube.com", "youtu.be", "www.youtube.com"],
            "twitter": ["twitter.com", "x.com", "api.x.com", "mobile.x.com"],
            "instagram": ["instagram.com", "www.instagram.com", "m.instagram.com"],
            "pinterest": ["pinterest.com", "www.pinterest.com"],
            "soundcloud": ["soundcloud.com", "www.soundcloud.com"],
        },
        description="Service domain mappings",
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


class ThemeConfig(BaseModel):
    """Theme-related configuration with color schemes."""

    appearance_mode: AppearanceMode = Field(
        default=AppearanceMode.DARK, description="Appearance mode (dark/light)"
    )
    color_theme: ColorTheme = Field(default=ColorTheme.BLUE, description="Color theme selection")
    theme_persistence: bool = Field(
        default=True, description="Whether to persist theme preference to config file"
    )

    @field_serializer("appearance_mode", "color_theme", mode="plain")
    def serialize_enums(self, value):
        """Serialize enum values to strings to avoid Pydantic warnings."""
        return value.value if hasattr(value, "value") else value

    def __init__(self, **data):
        """Initialize with enum conversion."""
        # Convert string values to enums if provided as strings
        if "appearance_mode" in data and isinstance(data["appearance_mode"], str):
            data["appearance_mode"] = AppearanceMode(data["appearance_mode"])
        if "appearance_mode" not in data:
            data["appearance_mode"] = AppearanceMode.DARK

        if "color_theme" in data and isinstance(data["color_theme"], str):
            data["color_theme"] = ColorTheme(data["color_theme"])
        if "color_theme" not in data:
            data["color_theme"] = ColorTheme.BLUE

        super().__init__(**data)

    @property
    def appearance_mode_enum(self) -> AppearanceMode:
        """Get appearance mode as enum."""
        if isinstance(self.appearance_mode, str):
            return AppearanceMode(self.appearance_mode)
        return self.appearance_mode

    @property
    def color_theme_enum(self) -> ColorTheme:
        """Get color theme as enum."""
        if isinstance(self.color_theme, str):
            return ColorTheme(self.color_theme)
        return self.color_theme

    @staticmethod
    @cache
    def get_color_schemes() -> dict[str, dict[str, Any]]:
        """Get all color schemes for themes (cached for performance)."""
        return {
            # Dark themes - with refined visible borders
            "dark_blue": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#1f538d",
                "button_hover_color": "#14375e",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_green": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#2d8659",
                "button_hover_color": "#1f5c3f",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_purple": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#7b2cbf",
                "button_hover_color": "#5a1f8f",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_orange": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#d97706",
                "button_hover_color": "#92400e",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_teal": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#0d9488",
                "button_hover_color": "#0f766e",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_pink": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#db2777",
                "button_hover_color": "#be185d",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_indigo": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#4f46e5",
                "button_hover_color": "#4338ca",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_amber": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#505050", "#606060"],
                "button_color": "#f59e0b",
                "button_hover_color": "#d97706",
                "text_color": ["#ffffff", "#ffffff"],
            },
            # Light themes - with refined visible borders
            "light_blue": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#3b82f6",
                "button_hover_color": "#2563eb",
                "text_color": ["#000000", "#000000"],
            },
            "light_green": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#10b981",
                "button_hover_color": "#059669",
                "text_color": ["#000000", "#000000"],
            },
            "light_purple": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#8b5cf6",
                "button_hover_color": "#7c3aed",
                "text_color": ["#000000", "#000000"],
            },
            "light_orange": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#f97316",
                "button_hover_color": "#ea580c",
                "text_color": ["#000000", "#000000"],
            },
            "light_teal": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#14b8a6",
                "button_hover_color": "#0d9488",
                "text_color": ["#000000", "#000000"],
            },
            "light_pink": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#ec4899",
                "button_hover_color": "#db2777",
                "text_color": ["#000000", "#000000"],
            },
            "light_indigo": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#6366f1",
                "button_hover_color": "#4f46e5",
                "text_color": ["#000000", "#000000"],
            },
            "light_amber": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#fbbf24",
                "button_hover_color": "#f59e0b",
                "text_color": ["#000000", "#000000"],
            },
            # Additional dark themes - with better visible borders
            "dark_red": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#4a4a4a", "#5a5a5a"],
                "button_color": "#dc2626",
                "button_hover_color": "#b91c1c",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_cyan": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#4a4a4a", "#5a5a5a"],
                "button_color": "#06b6d4",
                "button_hover_color": "#0891b2",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_emerald": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#4a4a4a", "#5a5a5a"],
                "button_color": "#10b981",
                "button_hover_color": "#059669",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_rose": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#4a4a4a", "#5a5a5a"],
                "button_color": "#f43f5e",
                "button_hover_color": "#e11d48",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_violet": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#4a4a4a", "#5a5a5a"],
                "button_color": "#8b5cf6",
                "button_hover_color": "#7c3aed",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_slate": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#4a4a4a", "#5a5a5a"],
                "button_color": "#64748b",
                "button_hover_color": "#475569",
                "text_color": ["#ffffff", "#ffffff"],
            },
            # Additional light themes - with visible borders
            "light_red": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#ef4444",
                "button_hover_color": "#dc2626",
                "text_color": ["#000000", "#000000"],
            },
            "light_cyan": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#06b6d4",
                "button_hover_color": "#0891b2",
                "text_color": ["#000000", "#000000"],
            },
            "light_emerald": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#10b981",
                "button_hover_color": "#059669",
                "text_color": ["#000000", "#000000"],
            },
            "light_rose": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#f43f5e",
                "button_hover_color": "#e11d48",
                "text_color": ["#000000", "#000000"],
            },
            "light_violet": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#8b5cf6",
                "button_hover_color": "#7c3aed",
                "text_color": ["#000000", "#000000"],
            },
            "light_slate": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#909090", "#a0a0a0"],
                "button_color": "#64748b",
                "button_hover_color": "#475569",
                "text_color": ["#000000", "#000000"],
            },
        }

    @staticmethod
    @cache
    def get_theme_json(appearance: AppearanceMode, color: ColorTheme) -> dict[str, Any]:
        """Get CTK theme JSON structure for appearance and color combination (cached)."""
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
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    instagram: InstagramConfig = Field(default_factory=InstagramConfig)
    pinterest: PinterestConfig = Field(default_factory=PinterestConfig)
    soundcloud: SoundCloudConfig = Field(default_factory=SoundCloudConfig)
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
                        if config_file.suffix == ".yaml" or config_file.suffix == ".yml":
                            return yaml.safe_load(f)
                        else:
                            return json.load(f)
                except Exception:
                    continue

        return None

    @classmethod
    def _settings_customise_sources(
        cls,
        settings_cls,
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
                    return None
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"[CONFIG] Saved configuration to {config_file}")
            return None
        except Exception as e:
            logger.error(f"[CONFIG] Failed to save configuration: {e}", exc_info=True)


# Singleton instance
_config_instance: AppConfig | None = None


@cache
def get_config() -> AppConfig:
    """Get the singleton configuration instance.

    Returns:
        The application configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance


def set_config(config: AppConfig) -> None:
    """Set the configuration instance (mainly for testing).

    Args:
        config: The configuration instance to set
    """
    global _config_instance
    _config_instance = config


def reset_config() -> None:
    """Reset the configuration instance (mainly for testing)."""
    global _config_instance
    _config_instance = None
