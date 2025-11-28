"""Download error type enum."""

from .compat import StrEnum


class DownloadErrorType(StrEnum):
    """Type of download error."""

    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    FORMAT = "format"
    OTHER = "other"
