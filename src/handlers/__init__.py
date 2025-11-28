"""Handler implementations for the media downloader application."""

# Application handlers - imported first to avoid circular imports
from .cookie_handler import CookieHandler
from .download_handler import DownloadHandler
from .network_checker import NetworkChecker
from .service_detector import ServiceDetector


def _register_link_handlers():
    """Lazy registration of link handlers to avoid circular imports."""
    # Import link handlers here to trigger auto-registration
    # This is called after application initialization
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


# For explicit imports, we can still provide the classes
# but they won't be imported until explicitly requested
def __getattr__(name):
    """Lazy import for link handlers."""
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
    # Application handlers
    "DownloadHandler",
    "InstagramHandler",
    "NetworkChecker",
    "PinterestHandler",
    "ServiceDetector",
    "SoundCloudHandler",
    "TwitterHandler",
    # Link handlers (lazy loaded)
    "YouTubeHandler",
    # Registration function
    "_register_link_handlers",
]
