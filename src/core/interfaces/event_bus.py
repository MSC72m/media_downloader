from collections.abc import Callable
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from src.core.enums.events import DownloadEvent

# Type variable for event enums
EventType = TypeVar("EventType", bound=Enum)


@runtime_checkable
class IEventBus(Protocol, Generic[EventType]):
    """Generic event bus interface protocol."""

    def publish(self, event: EventType, **kwargs: Any) -> None:
        """Publish an event."""
        ...

    def subscribe(self, event: EventType, callback: Callable[[Any], None]) -> None:
        """Subscribe to an event."""
        ...

    def unsubscribe(self, event: EventType, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from an event."""
        ...


# Backward compatibility: specific interface for DownloadEvent
IDownloadEventBus = IEventBus[DownloadEvent]
