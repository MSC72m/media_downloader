from .compat import StrEnum


class DownloadErrorType(StrEnum):
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    FORMAT = "format"
    OTHER = "other"
