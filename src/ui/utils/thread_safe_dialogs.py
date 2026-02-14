import threading
from collections.abc import Callable
from functools import wraps
from typing import Any, Protocol, cast

from src.utils.logger import get_logger

logger = get_logger(__name__)


class _DialogWindowProtocol(Protocol):
    def after(self, ms: int, func: Callable[[], Any]) -> Any: ...

    def destroy(self) -> None: ...

    def update(self) -> None: ...


class ThreadSafeDialogMixin:
    """Mixin class to provide thread-safe operations for dialogs."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._main_thread_id = threading.get_ident()
        self._lock = threading.Lock()

    def is_main_thread(self) -> bool:
        """Check if current thread is main thread."""
        return threading.get_ident() == self._main_thread_id

    def safe_after(self, delay_ms: int, func: Callable, *args, **kwargs):
        """Thread-safe version of after() method."""
        window = cast(_DialogWindowProtocol, self)
        if self.is_main_thread():
            return window.after(delay_ms, lambda: self._safe_execute(func, *args, **kwargs))
        window.after(
            0,
            lambda: window.after(delay_ms, lambda: self._safe_execute(func, *args, **kwargs)),
        )
        return None

    def _safe_execute(self, func: Callable, *args, **kwargs):
        """Safely execute function with error handling."""
        try:
            if callable(func):
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in safe_execute: {e}", exc_info=True)

    def safe_configure(self, widget, **kwargs) -> None:
        """Thread-safe widget configuration."""
        if self.is_main_thread():
            try:
                widget.configure(**kwargs)
            except Exception as e:
                logger.error(f"Error configuring widget: {e}", exc_info=True)
        else:
            cast(_DialogWindowProtocol, self).after(
                0, lambda: self._safe_configure(widget, **kwargs)
            )

    def _safe_configure(self, widget, **kwargs) -> None:
        """Internal safe configuration."""
        try:
            widget.configure(**kwargs)
        except Exception as e:
            logger.error(f"Error in safe configure: {e}", exc_info=True)

    def safe_destroy(self) -> None:
        """Thread-safe window destruction."""
        if self.is_main_thread():
            try:
                cast(_DialogWindowProtocol, self).destroy()
            except Exception as e:
                logger.error(f"Error destroying window: {e}", exc_info=True)
        else:
            cast(_DialogWindowProtocol, self).after(0, self._safe_destroy)

    def _safe_destroy(self) -> None:
        """Internal safe destruction."""
        try:
            cast(_DialogWindowProtocol, self).destroy()
        except Exception as e:
            logger.error(f"Error in safe destroy: {e}", exc_info=True)

    def safe_update(self) -> None:
        """Thread-safe UI update."""
        if self.is_main_thread():
            try:
                cast(_DialogWindowProtocol, self).update()
            except Exception as e:
                logger.error(f"Error updating UI: {e}", exc_info=True)
        else:
            cast(_DialogWindowProtocol, self).after(0, self._safe_update)

    def _safe_update(self) -> None:
        """Internal safe update."""
        try:
            cast(_DialogWindowProtocol, self).update()
        except Exception as e:
            logger.error(f"Error in safe update: {e}", exc_info=True)


def thread_safe_dialog(method):
    """Decorator to make dialog methods thread-safe."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, "safe_after"):
            return self.safe_after(0, lambda: method(self, *args, **kwargs))
        return method(self, *args, **kwargs)

    return wrapper


class ThreadSafeOperations:
    """Utility class for thread-safe operations."""

    @staticmethod
    def execute_in_main_thread(widget, func: Callable, *args, **kwargs) -> Any:
        """Execute function in main thread safely."""
        if widget.winfo_exists():
            try:
                return widget.after(0, lambda: func(*args, **kwargs))
            except Exception as e:
                logger.error(f"Error scheduling main thread execution: {e}", exc_info=True)
        return None

    @staticmethod
    def safe_widget_state(widget, state: str) -> None:
        """Safely change widget state."""
        try:
            if widget.winfo_exists():
                widget.configure(state=state)
        except Exception as e:
            logger.error(f"Error changing widget state: {e}", exc_info=True)

    @staticmethod
    def safe_widget_config(widget, **kwargs) -> None:
        """Safely configure widget."""
        try:
            if widget.winfo_exists():
                widget.configure(**kwargs)
        except Exception as e:
            logger.error(f"Error configuring widget: {e}", exc_info=True)
