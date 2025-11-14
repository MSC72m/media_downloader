"""Service type enum."""

from .compat import StrEnum


class ServiceType(StrEnum):
    """Supported service types."""

    YOUTUBE = "youtube"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    SOUNDCLOUD = "soundcloud"
    GOOGLE = "google"
