"""Core enums for the media downloader application."""
from enum import StrEnum


class DownloadStatus(StrEnum):
    """Status of a download item."""
    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    COMPLETED = "Completed"
    FAILED = "Failed"
    PAUSED = "Paused"
    CANCELLED = "Cancelled"


class InstagramAuthStatus(StrEnum):
    """Status of Instagram authentication."""
    LOGGING_IN = "Logging in"
    AUTHENTICATED = "Authenticated"
    FAILED = "Failed"


class NetworkStatus(StrEnum):
    """Network connection status."""
    CHECKING = "Checking"
    CONNECTED = "Connected"
    ERROR = "Error"
    UNKNOWN = "Unknown"


class UITheme(StrEnum):
    """Available UI themes."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class MessageLevel(StrEnum):
    """Message levels for status updates."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class VideoQuality(StrEnum):
    """Available video quality options."""
    HIGHEST = "highest"
    LOWEST = "lowest"
    UHD_4K = "2160p"
    QHD = "1440p"
    FHD = "1080p"
    HD = "720p"
    SD = "480p"
    LD = "360p"
    VERY_LOW = "240p"
    LOWEST_QUALITY = "144p"


class ServiceType(StrEnum):
    """Supported service types."""
    GOOGLE = "Google"
    YOUTUBE = "YouTube"
    INSTAGRAM = "Instagram"
    TWITTER = "Twitter"
    PINTEREST = "Pinterest"


class ButtonState(StrEnum):
    """UI button states."""
    ADD = "add"
    REMOVE = "remove"
    CLEAR = "clear"
    DOWNLOAD = "download"
    CANCEL = "cancel"
    PAUSE = "pause"
    RESUME = "resume"
    SETTINGS = "settings"
    INSTAGRAM_LOGIN = "instagram_login"
    INSTAGRAM_LOGOUT = "instagram_logout"


# For backward compatibility, re-export the old names
DownloadStatusEnum = DownloadStatus
NetworkStatusEnum = NetworkStatus
InstagramAuthStatusEnum = InstagramAuthStatus