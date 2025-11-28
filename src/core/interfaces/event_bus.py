from typing import Any, Callable, Protocol, runtime_checkable

from src.core.enums.events import DownloadEvent


@runtime_checkable
class IEventBus(Protocol):
    def publish(self, event: DownloadEvent, **kwargs: Any) -> None:
        ...

    def subscribe(self, event: DownloadEvent, callback: Callable[[Any], None]) -> None:
        ...

    def unsubscribe(self, event: DownloadEvent, callback: Callable[[Any], None]) -> None:
        ...
