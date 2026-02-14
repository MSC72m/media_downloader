from typing import Protocol, runtime_checkable

from src.core.type_defs import JSONValue


@runtime_checkable
class INotifier(Protocol):
    def notify_user(self, notification_type: str, **kwargs: JSONValue) -> None: ...

    def notify_error(self, error: Exception, context: str = "") -> None: ...
