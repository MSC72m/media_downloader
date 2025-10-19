"""Repository pattern for data management."""

import threading
import logging
from typing import List, Callable
from ..core import Download, DownloadStatus

logger = logging.getLogger(__name__)


class DownloadRepository:
    """Repository for managing download data."""

    def __init__(self):
        self._items: List[Download] = []
        self._lock = threading.Lock()
        self._observers: List[Callable] = []

    def add(self, download: Download) -> None:
        """Add a download to the repository."""
        with self._lock:
            self._items.append(download)
            self._notify_observers()

    def remove(self, indices: List[int]) -> None:
        """Remove downloads by indices."""
        with self._lock:
            for index in sorted(indices, reverse=True):
                if 0 <= index < len(self._items):
                    self._items.pop(index)
            self._notify_observers()

    def clear(self) -> None:
        """Clear all downloads."""
        with self._lock:
            self._items.clear()
            self._notify_observers()

    def get_all(self) -> List[Download]:
        """Get all downloads."""
        with self._lock:
            return self._items.copy()

    def get_pending(self) -> List[Download]:
        """Get all pending downloads."""
        with self._lock:
            return [item for item in self._items if item.status == DownloadStatus.PENDING]

    def get_by_status(self, status: DownloadStatus) -> List[Download]:
        """Get downloads by status."""
        with self._lock:
            return [item for item in self._items if item.status == status]

    def update_download(self, index: int, **kwargs) -> bool:
        """Update a download by index."""
        with self._lock:
            if 0 <= index < len(self._items):
                download = self._items[index]
                for key, value in kwargs.items():
                    if hasattr(download, key):
                        setattr(download, key, value)
                self._notify_observers()
                return True
            return False

    def get_count(self) -> int:
        """Get total number of downloads."""
        with self._lock:
            return len(self._items)

    def has_items(self) -> bool:
        """Check if there are any downloads."""
        with self._lock:
            return len(self._items) > 0

    def add_observer(self, callback: Callable) -> None:
        """Add an observer for repository changes."""
        self._observers.append(callback)

    def remove_observer(self, callback: Callable) -> None:
        """Remove an observer."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notify all observers of changes."""
        for callback in self._observers:
            try:
                callback(self.get_all())
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")


class OptionsRepository:
    """Repository for managing download options."""

    def __init__(self):
        self._options = {}
        self._lock = threading.Lock()
        self._observers: List[Callable] = []

    def get(self, key: str, default=None):
        """Get an option value."""
        with self._lock:
            return self._options.get(key, default)

    def set(self, key: str, value) -> None:
        """Set an option value."""
        with self._lock:
            self._options[key] = value
            self._notify_observers(key, value)

    def get_all(self) -> dict:
        """Get all options."""
        with self._lock:
            return self._options.copy()

    def update(self, options: dict) -> None:
        """Update multiple options."""
        with self._lock:
            self._options.update(options)
            for key, value in options.items():
                self._notify_observers(key, value)

    def add_observer(self, callback: Callable) -> None:
        """Add an observer for option changes."""
        self._observers.append(callback)

    def remove_observer(self, callback: Callable) -> None:
        """Remove an observer."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, key: str, value) -> None:
        """Notify all observers of changes."""
        for callback in self._observers:
            try:
                callback(key, value)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")