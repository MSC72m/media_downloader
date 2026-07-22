from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from src.core.config import AppConfig, get_config
from src.core.interfaces import IMessageQueue, INotifier, UIContextProtocol
from src.core.type_defs import JSONDict, JSONValue
from src.services.notifications.notifier import NotifierService
from src.utils.logger import get_logger

from .models import DetectionResult

UICallback = Callable[[str, UIContextProtocol], None]

logger = get_logger(__name__)


class BaseHandler(ABC):
    def __init__(
        self,
        message_queue: IMessageQueue | None,
        config: AppConfig | None = None,
        service_name: str = "",
    ) -> None:
        self.config = config or get_config()
        self.message_queue = message_queue
        self.service_name = service_name

        templates = self._get_service_templates(service_name)
        self.notifier: INotifier = NotifierService(message_queue, custom_templates=templates)

    def _get_service_templates(self, service_name: str) -> dict[str, JSONDict]:
        if not service_name:
            return {}

        templates_attr = getattr(self.config.notifications, service_name, None)
        if isinstance(templates_attr, dict):
            return templates_attr
        return {}

    def _callback_service_name(self) -> str:
        """Service name used for platform callback lookup."""
        return self.service_name

    def _handler_label(self) -> str:
        """Human-readable handler label for log messages."""
        return self.service_name.title() if self.service_name else "Unknown"

    @classmethod
    @abstractmethod
    def get_patterns(cls) -> list[str]: ...

    def can_handle(self, url: str) -> DetectionResult:
        for pattern in self.get_patterns():
            if re.match(pattern, url):
                metadata = self._extract_metadata(url)
                return DetectionResult(
                    service_type=self.service_name,
                    confidence=1.0,
                    metadata=metadata,
                )

        return DetectionResult(service_type="unknown", confidence=0.0)

    def _extract_metadata(self, url: str) -> JSONDict:
        return {}

    @abstractmethod
    def get_metadata(self, url: str) -> JSONDict: ...

    @abstractmethod
    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool: ...

    def get_ui_callback(self) -> UICallback:
        """Default UI callback that schedules a download via platform callback.

        Uses ``_callback_service_name()`` to look up the platform callback,
        falling back to ``"generic"``. Subclasses that need dialog creation
        (e.g. YouTube, Spotify) or custom download-creation logic (e.g.
        Instagram) override this method.
        """
        from src.utils.type_helpers import (
            get_platform_callback,
            get_root,
            schedule_on_main_thread,
        )

        service_name = self._callback_service_name()
        label = self._handler_label()
        error_handler = getattr(self, "error_handler", None)

        def default_callback(url: str, ui_context: UIContextProtocol) -> None:
            nonlocal service_name, label, error_handler

            root = get_root(ui_context)

            download_callback = get_platform_callback(ui_context, service_name)
            if not download_callback:
                download_callback = get_platform_callback(ui_context, "generic")

            if not download_callback:
                error_msg = "No download callback found"
                logger.error(f"[{service_name.upper()}_HANDLER] {error_msg}")
                if error_handler:
                    error_handler.handle_service_failure(
                        f"{label} Handler", "callback", error_msg, url
                    )
                return

            def process() -> None:
                try:
                    logger.info(
                        f"[{service_name.upper()}_HANDLER] Calling download callback for: {url}"
                    )
                    download_callback(url)
                    logger.info(f"[{service_name.upper()}_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[{service_name.upper()}_HANDLER] Error processing {label} download: {e}",
                        exc_info=True,
                    )
                    if error_handler:
                        error_handler.handle_exception(e, f"Processing {label} download", label)
                    else:
                        self.notifier.notify_user(
                            "error",
                            title=f"{label} Download Error",
                            message=f"Failed to process {label} download: {e!s}",
                        )

            schedule_on_main_thread(root, process, immediate=True)

        return default_callback
