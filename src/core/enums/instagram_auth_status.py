from .compat import StrEnum


class InstagramAuthStatus(StrEnum):
    FAILED = "failed"
    LOGGING_IN = "logging_in"
    AUTHENTICATED = "authenticated"
