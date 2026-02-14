from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar, runtime_checkable

from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.models import Download
from src.core.type_defs import JSONValue

TService = TypeVar("TService")


@runtime_checkable
class ServiceResolverProtocol(Protocol):
    def get(self, service_type: type[TService]) -> TService: ...


@runtime_checkable
class DownloadsCoordinatorProtocol(Protocol):
    def add_download(self, download: Download) -> None: ...
    def remove_downloads(self, indices: list[int]) -> None: ...
    def get_downloads(self) -> list[Download]: ...


@runtime_checkable
class PlatformDialogsProtocol(Protocol):
    def authenticate_instagram(
        self,
        parent_window: TkRootProtocol,
        callback: Callable[[InstagramAuthStatus], None] | None = None,
    ) -> None: ...


@runtime_checkable
class UIContextProtocol(Protocol):
    root: TkRootProtocol
    downloads: DownloadsCoordinatorProtocol
    platform_dialogs: PlatformDialogsProtocol

    def youtube_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def twitter_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def instagram_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def pinterest_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def spotify_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def tiktok_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def radiojavan_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def soundcloud_download(self, url: str, **kwargs: JSONValue) -> None: ...
    def generic_download(self, url: str, name: str | None = None) -> None: ...


@runtime_checkable
class HasEventCoordinatorProtocol(Protocol):
    event_coordinator: UIContextProtocol


@runtime_checkable
class DynamicUIContextProtocol(Protocol):
    root: TkRootProtocol
    downloads: DownloadsCoordinatorProtocol
    platform_dialogs: PlatformDialogsProtocol

    def platform_download(self, platform: str, url: str, name: str | None = None) -> None: ...


@runtime_checkable
class HandlerWithPatternsProtocol(Protocol):
    @classmethod
    def get_patterns(cls) -> list[str]: ...


@runtime_checkable
class HasCleanupProtocol(Protocol):
    def cleanup(self) -> None: ...


@runtime_checkable
class HasClearProtocol(Protocol):
    def clear(self) -> None: ...


@runtime_checkable
class HasCompletedDownloadsProtocol(Protocol):
    def has_completed_downloads(self) -> bool: ...
    def remove_completed_downloads(self) -> int: ...


@runtime_checkable
class TkRootProtocol(Protocol):
    def after(self, ms: int | str, func: Callable[..., None], *args: JSONValue) -> str: ...
    def winfo_exists(self) -> bool: ...
    def run_on_main_thread(self, func: Callable[[], None]) -> None: ...


@runtime_checkable
class DownloadAttributesProtocol(Protocol):
    cookie_path: str | None
    quality: str
    download_playlist: bool
    audio_only: bool
