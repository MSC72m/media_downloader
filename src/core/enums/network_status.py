from .compat import StrEnum


class NetworkStatus(StrEnum):
    UNKNOWN = "unknown"
    CHECKING = "checking"
    CONNECTED = "connected"
    ERROR = "error"
