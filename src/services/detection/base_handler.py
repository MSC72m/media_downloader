from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from src.core.config import AppConfig, get_config
from src.core.interfaces import IMessageQueue, INotifier, UIContextProtocol
from src.core.type_defs import JSONDict, JSONValue
from src.services.notifications.notifier import NotifierService

from .models import DetectionResult

UICallback = Callable[[str, UIContextProtocol], None]


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

    @abstractmethod
    def get_ui_callback(self) -> UICallback: ...
