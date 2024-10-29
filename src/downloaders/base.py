from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseDownloader(ABC):
    """Base class for all downloaders."""

    @abstractmethod
    def download(
            self,
            url: str,
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """Download media from URL."""
        pass