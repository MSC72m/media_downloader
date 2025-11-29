from .cookie_handler import CookieHandler
from .download_handler import DownloadHandler
from .network_checker import NetworkChecker
from .service_detector import ServiceDetector


def _register_link_handlers():
    from . import (
        instagram_handler,
        pinterest_handler,
        soundcloud_handler,
        twitter_handler,
        youtube_handler,
    )

    return (
        youtube_handler.YouTubeHandler,
        instagram_handler.InstagramHandler,
        twitter_handler.TwitterHandler,
        pinterest_handler.PinterestHandler,
        soundcloud_handler.SoundCloudHandler,
    )


def __getattr__(name):
    if name == "YouTubeHandler":
        from .youtube_handler import YouTubeHandler

        return YouTubeHandler
    if name == "InstagramHandler":
        from .instagram_handler import InstagramHandler

        return InstagramHandler
    if name == "TwitterHandler":
        from .twitter_handler import TwitterHandler

        return TwitterHandler
    if name == "PinterestHandler":
        from .pinterest_handler import PinterestHandler

        return PinterestHandler
    if name == "SoundCloudHandler":
        from .soundcloud_handler import SoundCloudHandler

        return SoundCloudHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CookieHandler",
    "DownloadHandler",
    "InstagramHandler",
    "NetworkChecker",
    "PinterestHandler",
    "ServiceDetector",
    "SoundCloudHandler",
    "TwitterHandler",
    "YouTubeHandler",
    "_register_link_handlers",
]
