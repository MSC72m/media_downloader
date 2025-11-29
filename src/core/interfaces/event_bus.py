from collections.abc import Callable
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from src.core.enums.events import DownloadEvent

EventType = TypeVar("EventType", bound=Enum)


@runtime_checkable
class IEventBus(Protocol, Generic[EventType]):
    def publish(self, event: EventType, **kwargs: Any) -> None: ...

    def subscribe(self, event: EventType, callback: Callable[[Any], None]) -> None: ...

    def unsubscribe(self, event: EventType, callback: Callable[[Any], None]) -> None: ...


IDownloadEventBus = IEventBus[DownloadEvent]
