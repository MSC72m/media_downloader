"""Service type enum."""

from enum import StrEnum


class ServiceType(StrEnum):
    """Supported service types."""
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    GOOGLE = "google"