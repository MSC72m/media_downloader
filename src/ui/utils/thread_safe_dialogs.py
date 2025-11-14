"""Thread-safe utilities for GUI operations."""

import threading
from functools import wraps
from typing import Any
from collections.abc import Callable


class ThreadSafeDialogMixin:
    """Mixin class to provide thread-safe operations for dialogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._main_thread_id = threading.get_ident()
        self._lock = threading.Lock()

    def is_main_thread(self) -> bool:
        """Check if current thread is main thread."""
        return threading.get_ident() == self._main_thread_id

    def safe_after(self, delay_ms: int, func: Callable, *args, **kwargs):
        """Thread-safe version of after() method."""
        if self.is_main_thread():
            return self.after(delay_ms, lambda: self._safe_execute(func, *args, **kwargs))
        else:
            # Schedule on main thread
            self.after(0, lambda: self.after(delay_ms, lambda: self._safe_execute(func, *args, **kwargs)))

    def _safe_execute(self, func: Callable, *args, **kwargs):
        """Safely execute function with error handling."""
        try:
            if callable(func):
                return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in safe_execute: {e}")
            import traceback
            traceback.print_exc()

    def safe_configure(self, widget, **kwargs):
        """Thread-safe widget configuration."""
        if self.is_main_thread():
            try:
                widget.configure(**kwargs)
            except Exception as e:
                print(f"Error configuring widget: {e}")
        else:
            self.after(0, lambda: self._safe_configure(widget, **kwargs))

    def _safe_configure(self, widget, **kwargs):
        """Internal safe configuration."""
        try:
            widget.configure(**kwargs)
        except Exception as e:
            print(f"Error in safe configure: {e}")

    def safe_destroy(self):
        """Thread-safe window destruction."""
        if self.is_main_thread():
            try:
                self.destroy()
            except Exception as e:
                print(f"Error destroying window: {e}")
        else:
            self.after(0, self._safe_destroy)

    def _safe_destroy(self):
        """Internal safe destruction."""
        try:
            self.destroy()
        except Exception as e:
            print(f"Error in safe destroy: {e}")

    def safe_update(self):
        """Thread-safe UI update."""
        if self.is_main_thread():
            try:
                self.update()
            except Exception as e:
                print(f"Error updating UI: {e}")
        else:
            self.after(0, self._safe_update)

    def _safe_update(self):
        """Internal safe update."""
        try:
            self.update()
        except Exception as e:
            print(f"Error in safe update: {e}")


def thread_safe_dialog(method):
    """Decorator to make dialog methods thread-safe."""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'safe_after'):
            # Use safe_after for thread-safe execution
            return self.safe_after(0, lambda: method(self, *args, **kwargs))
        else:
            # Fallback to direct execution
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
                print(f"Error scheduling main thread execution: {e}")
        return None

    @staticmethod
    def safe_widget_state(widget, state: str):
        """Safely change widget state."""
        try:
            if widget.winfo_exists():
                widget.configure(state=state)
        except Exception as e:
            print(f"Error changing widget state: {e}")

    @staticmethod
    def safe_widget_config(widget, **kwargs):
        """Safely configure widget."""
        try:
            if widget.winfo_exists():
                widget.configure(**kwargs)
        except Exception as e:
            print(f"Error configuring widget: {e}")
