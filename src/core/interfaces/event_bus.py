from collections.abc import Callable
from enum import Enum
from typing import Generic, Protocol, TypeVar, runtime_checkable

from src.core.enums.events import DownloadEvent

EventType_contra = TypeVar("EventType_contra", bound=Enum, contravariant=True)


@runtime_checkable
class IEventBus(Protocol, Generic[EventType_contra]):
    def publish(self, event: EventType_contra, **kwargs: object) -> None: ...

    def subscribe(
        self,
        event: EventType_contra,
        callback: Callable[..., None],
    ) -> None: ...

    def unsubscribe(
        self,
        event: EventType_contra,
        callback: Callable[..., None],
    ) -> None: ...


IDownloadEventBus = IEventBus[DownloadEvent]
