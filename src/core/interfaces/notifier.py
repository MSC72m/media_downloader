from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class INotifier(Protocol):
    def notify_user(self, notification_type: str, **kwargs: Any) -> None:
        ...

    def notify_error(self, error: Exception, context: str = "") -> None:
        ...
