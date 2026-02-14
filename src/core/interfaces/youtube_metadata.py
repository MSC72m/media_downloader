from typing import Protocol, runtime_checkable

from src.core.type_defs import JSONDict


class YouTubeMetadata:
    def __init__(self, **kwargs: object) -> None:
        self.title: str = str(kwargs.get("title", ""))
        self.duration: str = str(kwargs.get("duration", ""))
        self.view_count: str = str(kwargs.get("view_count", ""))
        self.upload_date: str = str(kwargs.get("upload_date", ""))
        self.channel: str = str(kwargs.get("channel", ""))
        self.description: str = str(kwargs.get("description", ""))
        self.thumbnail: str = str(kwargs.get("thumbnail", ""))

        qualities = kwargs.get("available_qualities", [])
        self.available_qualities: list[str] = (
            [str(item) for item in qualities] if isinstance(qualities, list) else []
        )
        formats = kwargs.get("available_formats", [])
        self.available_formats: list[str] = (
            [str(item) for item in formats] if isinstance(formats, list) else []
        )
        subtitles = kwargs.get("available_subtitles", [])
        self.available_subtitles: list[JSONDict] = (
            [item for item in subtitles if isinstance(item, dict)]
            if isinstance(subtitles, list)
            else []
        )

        self.is_playlist: bool = bool(kwargs.get("is_playlist", False))
        playlist_count = kwargs.get("playlist_count", 0)
        self.playlist_count: int = int(playlist_count) if isinstance(playlist_count, int) else 0

        error_value = kwargs.get("error")
        self.error: str | None = str(error_value) if isinstance(error_value, str) else None


class SubtitleInfo:
    def __init__(
        self, language_code: str, language_name: str, is_auto_generated: bool, url: str
    ) -> None:
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
