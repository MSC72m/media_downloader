"""Interface for YouTube metadata service."""

from typing import Any, Protocol, runtime_checkable


class YouTubeMetadata:
    def __init__(self, **kwargs):
        self.title: str = kwargs.get("title", "")
        self.duration: str = kwargs.get("duration", "")
        self.view_count: str = kwargs.get("view_count", "")
        self.upload_date: str = kwargs.get("upload_date", "")
        self.channel: str = kwargs.get("channel", "")
        self.description: str = kwargs.get("description", "")
        self.thumbnail: str = kwargs.get("thumbnail", "")
        self.available_qualities: list[str] = kwargs.get("available_qualities", [])
        self.available_formats: list[str] = kwargs.get("available_formats", [])
        self.available_subtitles: list[dict[str, Any]] = kwargs.get("available_subtitles", [])
        self.is_playlist: bool = kwargs.get("is_playlist", False)
        self.playlist_count: int = kwargs.get("playlist_count", 0)
        self.error: str | None = kwargs.get("error")


class SubtitleInfo:
    def __init__(self, language_code: str, language_name: str, is_auto_generated: bool, url: str):
        self.language_code = language_code
        self.language_name = language_name
        self.is_auto_generated = is_auto_generated
        self.url = url


@runtime_checkable
class IYouTubeMetadataService(Protocol):
    def fetch_metadata(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> YouTubeMetadata | None: ...

    def get_available_qualities(self, url: str) -> list[str]: ...

    def get_available_formats(self, url: str) -> list[str]: ...

    def get_available_subtitles(self, url: str) -> list[SubtitleInfo]: ...

    def validate_url(self, url: str) -> bool: ...

    def extract_video_id(self, url: str) -> str | None: ...
