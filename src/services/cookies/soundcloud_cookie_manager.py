from __future__ import annotations

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

from .site_cookie_manager import SiteCookieManager

logger = get_logger(__name__)


class SoundCloudCookieManager(SiteCookieManager):
    """SoundCloud cookie manager using Playwright browser automation."""

    SITE_URL = "https://soundcloud.com"
    SITE_NAME = "SoundCloud"
    COOKIE_DIR = "soundcloud"
    STATE_FILE = "soundcloud_cookie_state.json"

    def __init__(self, storage_dir=None, config: AppConfig | None = None) -> None:
        super().__init__(storage_dir, config or get_config())

    @staticmethod
    def _tag() -> str:
        return "SOUNDCLOUD_COOKIE_MANAGER"
