import contextlib
import hashlib
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass

CACHE_LOCK = threading.Lock()


class ThumbnailCache:
    """Cache service for thumbnail images with configurable size limit."""

    CACHE_DIR = Path.home() / ".media_downloader" / "thumbnails"
    DEFAULT_MAX_CACHE_SIZE = 100 * 1024 * 1024
    DEFAULT_MAX_AGE_DAYS = 30

    def __init__(self, config: AppConfig | None = None):
        if config is None:
            config = get_config()
        self.config = config

    @classmethod
    def _get_cache_dir(cls) -> Path:
        """Get cache directory, creating if needed."""
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return cls.CACHE_DIR

    def _get_max_cache_size(self) -> int:
        """Get maximum cache size from config or default."""
        max_size_mb = getattr(self.config.ui, "thumbnail_cache_max_mb", None)
        if max_size_mb is None:
            return self.DEFAULT_MAX_CACHE_SIZE
        return int(max_size_mb * 1024 * 1024)

    def _get_max_age_days(self) -> int:
        """Get maximum cache age from config or default."""
        return getattr(self.config.ui, "thumbnail_cache_max_age_days", self.DEFAULT_MAX_AGE_DAYS)

    def _get_cache_size(self) -> int:
        """Calculate current cache size in bytes."""
        total_size = 0
        try:
            for file_path in self.CACHE_DIR.iterdir():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size

    def _cleanup_old_files(self) -> None:
        """Remove files older than max age."""
        max_age_seconds = self._get_max_age_days() * 86400
        current_time = os.path.getmtime(self.CACHE_DIR) if self.CACHE_DIR.exists() else 0

        try:
            for file_path in self.CACHE_DIR.iterdir():
                if file_path.is_file():
                    try:
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            file_path.unlink()
                    except Exception:
                        pass
        except Exception:
            pass

    def _cleanup_if_needed(self) -> None:
        """Clean up cache if size exceeds limit."""
        current_size = self._get_cache_size()
        max_size = self._get_max_cache_size()

        if current_size <= max_size:
            return

        target_size = int(max_size * 0.8)
        files_with_size = []

        try:
            for file_path in self.CACHE_DIR.iterdir():
                if file_path.is_file():
                    with contextlib.suppress(Exception):
                        files_with_size.append(
                            (file_path, file_path.stat().st_mtime, file_path.stat().st_size)
                        )
        except Exception:
            pass

        files_with_size.sort(key=lambda x: x[1])
        accumulated_size = 0

        for file_path, mtime, size in files_with_size:
            if accumulated_size >= target_size:
                break
            try:
                file_path.unlink()
                accumulated_size += size
            except Exception:
                pass

    def _get_cache_path(self, url: str) -> Path:
        """Generate cache path from URL hash."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        return self.CACHE_DIR / f"{url_hash}.png"

    def get_or_fetch(self, url: str) -> Path | None:
        """Get thumbnail from cache or download and cache it.

        Args:
            url: Thumbnail URL

        Returns:
            Path to cached thumbnail or None if failed
        """
        if not url:
            return None

        cache_path = self._get_cache_path(url)
        cache_dir = self._get_cache_dir()

        if cache_path.exists():
            try:
                if cache_path.stat().st_size > 0:
                    logger.debug(f"[THUMBNAIL_CACHE] Cache hit for: {url[:50]}...")
                    return cache_path
            except Exception:
                pass

        try:
            logger.debug(f"[THUMBNAIL_CACHE] Downloading thumbnail: {url[:50]}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with CACHE_LOCK:
                self._cleanup_old_files()
                self._cleanup_if_needed()

            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(response.content)

            logger.info(f"[THUMBNAIL_CACHE] Cached thumbnail: {cache_path}")
            return cache_path
        except requests.RequestException as e:
            logger.error(f"[THUMBNAIL_CACHE] Failed to download thumbnail: {e}")
            return None
        except Exception as e:
            logger.error(f"[THUMBNAIL_CACHE] Error caching thumbnail: {e}", exc_info=True)
            return None

    def clear_cache(self) -> None:
        """Clear all cached thumbnails."""
        with CACHE_LOCK:
            try:
                for file_path in self.CACHE_DIR.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                logger.info("[THUMBNAIL_CACHE] Cleared cache")
            except Exception as e:
                logger.error(f"[THUMBNAIL_CACHE] Failed to clear cache: {e}")

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache_size, file_count, cache_dir
        """
        try:
            file_count = sum(1 for _ in self.CACHE_DIR.iterdir() if self.CACHE_DIR.exists())
            cache_size = self._get_cache_size()
            cache_size_mb = cache_size / (1024 * 1024)

            return {
                "cache_size_bytes": cache_size,
                "cache_size_mb": round(cache_size_mb, 2),
                "file_count": file_count,
                "cache_dir": str(self.CACHE_DIR),
            }
        except Exception as e:
            logger.error(f"[THUMBNAIL_CACHE] Failed to get cache info: {e}")
            return {
                "cache_size_bytes": 0,
                "cache_size_mb": 0.0,
                "file_count": 0,
                "cache_dir": str(self.CACHE_DIR),
            }
