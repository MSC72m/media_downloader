from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    runtime_checkable,
)

from src.core.config import AppConfig, get_config

if TYPE_CHECKING:
    from src.core.enums import ServiceType
    from src.core.models import CookieState, Download


@runtime_checkable
class IDownloadHandler(Protocol):
    def process_url(self, url: str, options: dict | None = None) -> bool: ...

    def handle_download_error(self, error: Exception) -> None: ...

    def is_available(self) -> bool: ...

    def add_download(self, download: Download) -> None: ...

    def remove_downloads(self, indices: list[int]) -> None: ...

    def clear_downloads(self) -> None: ...

    def get_downloads(self) -> list[Download]: ...

    def has_items(self) -> bool: ...

    def start_downloads(
        self,
        downloads: list[Download],
        download_dir: str | None = None,
        progress_callback: Callable | None = None,
        completion_callback: Callable | None = None,
    ) -> None: ...

    def cancel_download(self, download: Download) -> None: ...

    def has_active_downloads(self) -> bool: ...


@runtime_checkable
class ICookieHandler(Protocol):
    def set_cookie_file(self, cookie_path: str) -> bool: ...

    def has_valid_cookies(self) -> bool: ...

    def get_cookie_info_for_ytdlp(self) -> dict | None: ...


@runtime_checkable
class IMetadataService(Protocol):
    def get_metadata(self, url: str) -> dict: ...

    def is_available(self) -> bool: ...

    def fetch_metadata(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> Any: ...

    def validate_url(self, url: str) -> bool: ...


@runtime_checkable
class INetworkChecker(Protocol):
    def check_connectivity(self) -> tuple[bool, str]: ...

    def check_internet_connection(self) -> tuple[bool, str]: ...

    def check_service_connection(self, service: ServiceType) -> tuple[bool, str]: ...

    def get_problem_services(self) -> list[ServiceType]: ...


@runtime_checkable
class IFileService(Protocol):
    def ensure_directory(self, path: str) -> bool: ...

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str: ...

    def clean_filename(self, filename: str) -> str: ...

    def sanitize_filename(self, filename: str) -> str: ...


@runtime_checkable
class IMessageQueue(Protocol):
    def add_message(self, message: Any) -> None: ...

    def send_message(self, message: dict) -> None: ...

    def register_handler(self, message_type: str, handler: Callable) -> None: ...


@runtime_checkable
class IErrorNotifier(Protocol):
    def show_error(self, title: str, message: str) -> None: ...

    def show_warning(self, title: str, message: str) -> None: ...

    def show_info(self, title: str, message: str) -> None: ...

    def set_message_queue(self, message_queue: IMessageQueue) -> None: ...

    def handle_exception(
        self, exception: Exception, context: str = "", service: str = ""
    ) -> None: ...

    def handle_service_failure(
        self, service: str, operation: str, error_message: str, url: str = ""
    ) -> None: ...


@runtime_checkable
class IServiceFactory(Protocol):
    def get_downloader(self, url: str) -> Any: ...

    def detect_service_type(self, url: str) -> Any: ...


@runtime_checkable
class ICookieGenerator(Protocol):
    def get_state(self) -> CookieState | None: ...


@runtime_checkable
class IAutoCookieManager(Protocol):
    """Protocol for the auto cookie manager.

    Manages cookie TTL, triggers new cookie extraction,
    cleans up and replaces stale cookies automatically.
    """

    @property
    def generator(self) -> ICookieGenerator: ...

    def initialize(self) -> CookieState: ...

    def is_ready(self) -> bool: ...

    def is_generating(self) -> bool: ...

    def get_cookies(self) -> str | None: ...

    def get_state(self) -> CookieState: ...

    def refresh_if_needed(self) -> bool: ...

    def invalidate_and_regenerate(self) -> bool: ...

    def cleanup(self) -> None: ...


@runtime_checkable
class IUIState(Protocol):
    download_directory: str
    show_options_panel: bool
    selected_indices: list


class BaseDownloader(ABC):
    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config: AppConfig = get_config(),
    ):
        self.config = config
        self.error_handler = error_handler
        self.file_service = file_service

    @abstractmethod
    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool: ...


class NetworkError(Exception):
    def __init__(self, message: str, is_temporary: bool = False):
        self.message = message
        self.is_temporary = is_temporary
        super().__init__(self.message)


class AuthenticationError(Exception):
    def __init__(self, message: str, service: str = ""):
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)


class ServiceError(Exception):
    def __init__(self, message: str, service: str = ""):
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)
