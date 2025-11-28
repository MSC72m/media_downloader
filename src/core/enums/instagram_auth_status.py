"""Instagram authentication status enum."""

from .compat import StrEnum


class InstagramAuthStatus(StrEnum):
    """Instagram authentication statuses."""

    FAILED = "failed"
    LOGGING_IN = "logging_in"
    AUTHENTICATED = "authenticated"
