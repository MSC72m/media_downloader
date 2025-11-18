from typing import Any, Callable, Optional, Protocol, runtime_checkable

from src.core.application.container import ServiceContainer


@runtime_checkable
class UIContextProtocol(Protocol):
    """Protocol for UI context objects (orchestrator or event coordinator)."""

    container: ServiceContainer
    root: Any  # Tk root window

    def youtube_download(self, url: str, **kwargs) -> None:
        """Handle YouTube download."""
        ...

    def twitter_download(self, url: str, **kwargs) -> None:
        """Handle Twitter download."""
        ...

    def instagram_download(self, url: str, **kwargs) -> None:
        """Handle Instagram download."""
        ...

    def pinterest_download(self, url: str, **kwargs) -> None:
        """Handle Pinterest download."""
        ...

    def generic_download(self, url: str, name: Optional[str] = None) -> None:
        """Handle generic download."""
        ...


@runtime_checkable
class HasEventCoordinatorProtocol(Protocol):
    """Protocol for objects that have an event_coordinator attribute."""

    event_coordinator: UIContextProtocol


@runtime_checkable
class HandlerWithPatternsProtocol(Protocol):
    """Protocol for link handlers that provide URL patterns."""

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        ...


@runtime_checkable
class HasCleanupProtocol(Protocol):
    """Protocol for objects that have a cleanup method."""

    def cleanup(self) -> None:
        """Clean up resources."""
        ...


@runtime_checkable
class HasClearProtocol(Protocol):
    """Protocol for UI components that can be cleared."""

    def clear(self) -> None:
        """Clear the component."""
        ...


@runtime_checkable
class HasCompletedDownloadsProtocol(Protocol):
    """Protocol for download lists that track completed downloads."""

    def has_completed_downloads(self) -> bool:
        """Check if there are completed downloads."""
        ...

    def remove_completed_downloads(self) -> int:
        """Remove completed downloads and return count."""
        ...


@runtime_checkable
class TkRootProtocol(Protocol):
    """Protocol for Tk root window with after method."""

    def after(self, ms: int, func: Callable[[], Any]) -> str:
        """Schedule a function to be called after a delay."""
        ...

    def winfo_exists(self) -> bool:
        """Check if window still exists."""
        ...


@runtime_checkable
class DownloadAttributesProtocol(Protocol):
    """Protocol for download objects with optional attributes."""

    cookie_path: Optional[str]
    selected_browser: Optional[str]
    quality: str
    download_playlist: bool
    audio_only: bool
