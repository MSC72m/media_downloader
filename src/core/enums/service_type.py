from .compat import StrEnum


class ServiceType(StrEnum):
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    SOUNDCLOUD = "soundcloud"
    GOOGLE = "google"
    GENERIC = "generic"
