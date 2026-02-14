import importlib

from . import (
    instagram_handler,
    pinterest_handler,
    radiojavan_handler,
    soundcloud_handler,
    spotify_handler,
    tiktok_handler,
    twitter_handler,
    youtube_handler,
)
from .cookie_handler import CookieHandler
from .download_handler import DownloadHandler
from .network_checker import NetworkChecker
from .service_detector import ServiceDetector


def _register_link_handlers() -> tuple[type, ...]:
    return (
        youtube_handler.YouTubeHandler,
        instagram_handler.InstagramHandler,
        twitter_handler.TwitterHandler,
        pinterest_handler.PinterestHandler,
        soundcloud_handler.SoundCloudHandler,
        spotify_handler.SpotifyHandler,
        tiktok_handler.TikTokHandler,
        radiojavan_handler.RadioJavanHandler,
    )


_HANDLER_IMPORTS = {
    "YouTubeHandler": ("youtube_handler", "YouTubeHandler"),
    "InstagramHandler": ("instagram_handler", "InstagramHandler"),
    "TwitterHandler": ("twitter_handler", "TwitterHandler"),
    "PinterestHandler": ("pinterest_handler", "PinterestHandler"),
    "SoundCloudHandler": ("soundcloud_handler", "SoundCloudHandler"),
    "SpotifyHandler": ("spotify_handler", "SpotifyHandler"),
    "TikTokHandler": ("tiktok_handler", "TikTokHandler"),
    "RadioJavanHandler": ("radiojavan_handler", "RadioJavanHandler"),
}

YouTubeHandler = youtube_handler.YouTubeHandler
InstagramHandler = instagram_handler.InstagramHandler
TwitterHandler = twitter_handler.TwitterHandler
PinterestHandler = pinterest_handler.PinterestHandler
SoundCloudHandler = soundcloud_handler.SoundCloudHandler
SpotifyHandler = spotify_handler.SpotifyHandler
TikTokHandler = tiktok_handler.TikTokHandler
RadioJavanHandler = radiojavan_handler.RadioJavanHandler


def __getattr__(name: str) -> type:
    if name in _HANDLER_IMPORTS:
        module_name, class_name = _HANDLER_IMPORTS[name]
        module = importlib.import_module(f".{module_name}", __name__)
        return getattr(module, class_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CookieHandler",
    "DownloadHandler",
    "InstagramHandler",
    "NetworkChecker",
    "PinterestHandler",
    "RadioJavanHandler",
    "ServiceDetector",
    "SoundCloudHandler",
    "SpotifyHandler",
    "TikTokHandler",
    "TwitterHandler",
    "YouTubeHandler",
    "_register_link_handlers",
]
