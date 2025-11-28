"""Service interfaces for dependency injection."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Any, Protocol, runtime_checkable, TYPE_CHECKING

from src.core.config import get_config, AppConfig
from src.core.models import Download, DownloadOptions

if TYPE_CHECKING:
    from src.core.enums import ServiceType


@runtime_checkable
class IDownloadService(Protocol):
    def add_download(self, download: Download) -> None:
        ...

    def remove_downloads(self, indices: List[int]) -> None:
        ...

    def clear_downloads(self) -> None:
        ...

    def get_downloads(self) -> List[Download]:
        ...

    def start_download(self, download: Download, options: DownloadOptions) -> None:
        ...

    def pause_download(self, download: Download) -> None:
        ...

    def cancel_download(self, download: Download) -> None:
        ...


@runtime_checkable
class IDownloadHandler(Protocol):
    def process_url(self, url: str, options: Optional[dict] = None) -> bool:
        ...

    def handle_download_error(self, error: Exception) -> None:
        ...

    def is_available(self) -> bool:
        ...


@runtime_checkable
class ICookieHandler(Protocol):
    def set_cookie_file(self, cookie_path: str) -> bool:
        ...

    def has_valid_cookies(self) -> bool:
        ...

    def get_cookie_info_for_ytdlp(self) -> Optional[dict]:
        ...


@runtime_checkable
class IMetadataService(Protocol):
    def get_metadata(self, url: str) -> dict:
        ...

    def is_available(self) -> bool:
        ...


@runtime_checkable
class INetworkChecker(Protocol):
    def check_connectivity(self) -> tuple[bool, str]:
        ...

    def check_internet_connection(self) -> tuple[bool, str]:
        ...

    def check_service_connection(self, service: "ServiceType") -> tuple[bool, str]:
        ...

    def get_problem_services(self) -> list[str]:
        ...


@runtime_checkable
class IFileService(Protocol):
    def ensure_directory(self, path: str) -> bool:
        ...

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        ...

    def clean_filename(self, filename: str) -> str:
        ...

    def sanitize_filename(self, filename: str) -> str:
        ...


@runtime_checkable
class IMessageQueue(Protocol):
    def add_message(self, message: Any) -> None:
        ...

    def send_message(self, message: dict) -> None:
        ...

    def register_handler(self, message_type: str, handler: Callable) -> None:
        ...


@runtime_checkable
class IErrorNotifier(Protocol):
    def show_error(self, title: str, message: str) -> None:
        ...

    def show_warning(self, title: str, message: str) -> None:
        ...

    def show_info(self, title: str, message: str) -> None:
        ...

    def set_message_queue(self, message_queue: IMessageQueue) -> None:
        ...

    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None:
        ...

    def handle_service_failure(self, service: str, operation: str, error_message: str, url: str = "") -> None:
        ...


@runtime_checkable
class IServiceFactory(Protocol):
    def get_downloader(self, url: str) -> Any:
        ...

    def detect_service_type(self, url: str) -> Any:
        ...


@runtime_checkable
class IAutoCookieManager(Protocol):
    def initialize(self) -> Any:
        ...

    def is_ready(self) -> bool:
        ...

    def is_generating(self) -> bool:
        ...

    def get_cookies(self) -> Optional[str]:
        ...


@runtime_checkable
class IUIState(Protocol):
    download_directory: str
    show_options_panel: bool
    selected_indices: list


class BaseDownloader(ABC):
    def __init__(self, config: AppConfig = get_config()):
        self.config = config

    @abstractmethod
    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        ...


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
