from .compat import StrEnum


class ErrorType(StrEnum):
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    SERVICE = "service"
    VALIDATION = "validation"
    UNKNOWN = "unknown"
