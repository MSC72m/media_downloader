"""Protocol definitions for structural typing."""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class UIContextProtocol(Protocol):
    """Protocol for UI context objects."""

    container: Any
    root: Any

    def youtube_download(self, url: str, **kwargs) -> None: ...

    def twitter_download(self, url: str, **kwargs) -> None: ...

    def instagram_download(self, url: str, **kwargs) -> None: ...

    def pinterest_download(self, url: str, **kwargs) -> None: ...

    def generic_download(self, url: str, name: str | None = None) -> None: ...


@runtime_checkable
class HasEventCoordinatorProtocol(Protocol):
    """Protocol for objects with event_coordinator attribute."""

    event_coordinator: UIContextProtocol


@runtime_checkable
class HandlerWithPatternsProtocol(Protocol):
    """Protocol for link handlers with URL patterns."""

    @classmethod
    def get_patterns(cls) -> list[str]: ...


@runtime_checkable
class HasCleanupProtocol(Protocol):
    """Protocol for objects with cleanup method."""

    def cleanup(self) -> None: ...


@runtime_checkable
class HasClearProtocol(Protocol):
    """Protocol for UI components that can be cleared."""

    def clear(self) -> None: ...


@runtime_checkable
class HasCompletedDownloadsProtocol(Protocol):
    """Protocol for download lists tracking completed downloads."""

    def has_completed_downloads(self) -> bool: ...

    def remove_completed_downloads(self) -> int: ...


@runtime_checkable
class TkRootProtocol(Protocol):
    """Protocol for Tk root window."""

    def after(self, ms: int, func: Callable[[], Any]) -> str: ...

    def winfo_exists(self) -> bool: ...


@runtime_checkable
class DownloadAttributesProtocol(Protocol):
    """Protocol for download objects with optional attributes."""

    cookie_path: str | None
    quality: str
    download_playlist: bool
    audio_only: bool
