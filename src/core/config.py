"""Application configuration using Pydantic Settings with YAML/JSON file support."""

import json
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CookieConfig(BaseModel):
    """Cookie-related configuration."""

    storage_dir: Path = Field(
        default_factory=lambda: Path.home() / ".media_downloader",
        description="Directory to store cookies and state files"
    )
    cookie_file_name: str = Field(default="cookies.json", description="Cookie JSON file name")
    netscape_file_name: str = Field(default="cookies.txt", description="Netscape format cookie file name")
    state_file_name: str = Field(default="cookie_state.json", description="Cookie state file name")
    cookie_expiry_hours: int = Field(default=8, description="Cookie expiry time in hours")
    generation_timeout: int = Field(default=20, description="Cookie generation timeout in seconds")
    wait_after_load: float = Field(default=1.0, description="Wait time after page load in seconds")
    wait_for_network_idle: float = Field(default=5.0, description="Wait time for network idle in seconds")
    scroll_delay: float = Field(default=0.5, description="Delay after scroll interaction in seconds")


class PathConfig(BaseModel):
    """Path-related configuration."""

    downloads_dir: Path = Field(
        default_factory=lambda: Path.home() / "Downloads",
        description="Default downloads directory"
    )
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".media_downloader",
        description="Application configuration directory"
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
    thread_sleep_interval: float = Field(default=0.1, description="Thread sleep interval in seconds")


class NetworkConfig(BaseModel):
    """Network-related configuration."""

    default_timeout: int = Field(default=10, description="Default network timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="Default user agent string"
    )


class YouTubeConfig(BaseModel):
    """YouTube-specific configuration."""

    player_client: str = Field(default="web", description="Default YouTube player client")
    metadata_timeout: int = Field(default=30, description="Metadata fetch timeout in seconds")
    fallback_timeout: int = Field(default=20, description="Fallback command timeout in seconds")
    subtitle_timeout: int = Field(default=5, description="Subtitle fetch timeout in seconds")
    retry_sleep_multiplier: int = Field(default=3, description="Retry sleep multiplier for fragment retries")
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
            "mk": "Macedonian",
        },
        description="Language code to name mapping"
    )


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
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)

    @classmethod
    def _load_config_file(cls) -> Optional[dict]:
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
                    with open(config_file, "r", encoding="utf-8") as f:
                        if config_file.suffix == ".yaml" or config_file.suffix == ".yml":
                            return yaml.safe_load(f)
                        else:
                            return json.load(f)
                except Exception as e:
                    print(f"Warning: Failed to load config file {config_file}: {e}")
                    # Continue to next file instead of returning None
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


# Singleton instance
_config_instance: Optional[AppConfig] = None


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
