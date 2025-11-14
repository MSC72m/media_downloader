"""Handler implementations for the media downloader application."""

# Application handlers - imported first to avoid circular imports
from .auth_handler import AuthenticationHandler
from .cookie_handler import CookieHandler
from .download_handler import DownloadHandler
from .network_checker import NetworkChecker
from .service_detector import ServiceDetector


def _register_link_handlers():
    """Lazy registration of link handlers to avoid circular imports."""
    # Import link handlers here to trigger auto-registration
    # This is called after application initialization
    from . import instagram_handler, pinterest_handler, twitter_handler, youtube_handler

    return (
        youtube_handler.YouTubeHandler,
        instagram_handler.InstagramHandler,
        twitter_handler.TwitterHandler,
        pinterest_handler.PinterestHandler,
    )


# For explicit imports, we can still provide the classes
# but they won't be imported until explicitly requested
def __getattr__(name):
    """Lazy import for link handlers."""
    if name == "YouTubeHandler":
        from .youtube_handler import YouTubeHandler

        return YouTubeHandler
    elif name == "InstagramHandler":
        from .instagram_handler import InstagramHandler

        return InstagramHandler
    elif name == "TwitterHandler":
        from .twitter_handler import TwitterHandler

        return TwitterHandler
    elif name == "PinterestHandler":
        from .pinterest_handler import PinterestHandler

        return PinterestHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Application handlers
    "DownloadHandler",
    "AuthenticationHandler",
    "ServiceDetector",
    "NetworkChecker",
    "CookieHandler",
    # Link handlers (lazy loaded)
    "YouTubeHandler",
    "InstagramHandler",
    "TwitterHandler",
    "PinterestHandler",
    # Registration function
    "_register_link_handlers",
]
