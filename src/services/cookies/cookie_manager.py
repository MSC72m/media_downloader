import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, cast

from src.core.config import AppConfig, get_config
from src.core.interfaces import IAutoCookieManager
from src.core.models import CookieState
from src.utils.logger import get_logger

from .cookie_generator import CookieGenerator
from .youtube_cookie_sources import (
    YOUTUBE_STRICT_PROBE_URLS,
    YouTubeCookieSourceCoordinator,
    probe_youtube_cookie_file,
)

logger = get_logger(__name__)


class YouTubeCookieManager:
    def __init__(self, storage_dir: Path | None = None, config: AppConfig = get_config()) -> None:
        self.config = config
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.storage_dir / self.config.cookies.state_file_name
        self.generator = CookieGenerator(storage_dir=self.storage_dir, config=self.config)

        self._state: CookieState | None = None
        self._lock = Lock()
        self._initialization_complete = False
        self._strict_probe_retry_count = 2
        self._strict_probe_backoff_seconds = 1.5
        self._strict_probe_bg_thread: threading.Thread | None = None

    def initialize(self) -> CookieState:
        """Initialize cookie manager - load or generate cookies.

        Returns:
            Current cookie state
        """
        logger.info("[COOKIE_MANAGER] Initializing cookie manager")

        with self._lock:
            self._state = self._load_state()
            if self._needs_regeneration(self._state):
                logger.info("[COOKIE_MANAGER] Cookies need regeneration")
                loop = self._get_event_loop()
                self._state = loop.run_until_complete(self._regenerate_cookies(fast_mode=True))
                if self._state and self._state.is_valid:
                    self._start_background_strict_validation()
            elif not self.state_file.exists():
                logger.info("[COOKIE_MANAGER] Using existing valid cookies")
                self._save_state(self._state)
                self._start_background_strict_validation()
            else:
                logger.info("[COOKIE_MANAGER] Using existing valid cookies")
                self._start_background_strict_validation()

            self._initialization_complete = True
            return self._state

    async def initialize_async(self) -> CookieState:
        """Async version of initialize for use in async contexts.

        Returns:
            Current cookie state
        """
        logger.info("[COOKIE_MANAGER] Initializing cookie manager (async)")

        self._state = self._load_state()
        if self._needs_regeneration(self._state):
            logger.info("[COOKIE_MANAGER] Cookies need regeneration")
            self._state = await self._regenerate_cookies(fast_mode=True)
            if self._state and self._state.is_valid:
                self._start_background_strict_validation()
        else:
            logger.info("[COOKIE_MANAGER] Using existing valid cookies")
            self._start_background_strict_validation()

        self._initialization_complete = True
        return self._state

    def _needs_regeneration(self, state: CookieState) -> bool:
        """Determine whether cookies must be regenerated."""
        if not state.is_valid:
            return True

        if state.is_expired() or state.should_regenerate():
            return True

        if not state.cookie_path:
            return True

        cookie_path = Path(state.cookie_path)
        if not cookie_path.exists():
            return True

        if not self.generator.validate_netscape_file(str(cookie_path)):
            logger.warning("[COOKIE_MANAGER] Existing cookie file is invalid, forcing regeneration")
            return True

        return False

    def _try_regenerate_in_lock(self) -> str | None:
        """Attempt synchronous cookie regeneration while holding the lock.

        Returns:
            Valid cookie file path if regeneration succeeds, None otherwise
        """
        if self._state:
            self._state.is_generating = True
        try:
            loop = self._get_event_loop()
            self._state = loop.run_until_complete(self._regenerate_cookies())
        except Exception as exc:
            logger.error("[COOKIE_MANAGER] Regeneration failed: %s", exc)
        if self._state:
            self._state.is_generating = False
        if self._state and self._state.is_valid and self._state.cookie_path:
            cookie_path = self._state.cookie_path
            if Path(cookie_path).exists() and self.generator.validate_netscape_file(cookie_path):
                logger.info("[COOKIE_MANAGER] Returning regenerated cookie file: %s", cookie_path)
                return cookie_path
        return None

    def get_cookies(self) -> str | None:
        """Get path to cookie file for use with yt-dlp.

        If not initialized, returns None immediately (background init handles it).
        If cookies need regeneration, triggers it synchronously.

        Returns:
            Path to Netscape format cookie file, or None if not available
        """
        if not self._initialization_complete:
            logger.info("[COOKIE_MANAGER] Manager still initializing, returning None")
            return None

        with self._lock:
            if not self._state or not self._state.is_valid:
                logger.warning(
                    "[COOKIE_MANAGER] No valid cookies available, triggering regeneration"
                )
                return self._try_regenerate_in_lock()

            if self._state.is_expired():
                logger.info(
                    "[COOKIE_MANAGER] Cookies expired (TTL reached), triggering regeneration"
                )
                self._state.is_valid = False
                return self._try_regenerate_in_lock()

            if not (cookie_path := self._ensure_cookie_file_exists()):
                return None

            if self.generator.validate_netscape_file(cookie_path):
                return cookie_path

        return None

    def get_state(self) -> CookieState:
        """Get current cookie state.

        Returns:
            Current cookie state
        """
        if not self._initialization_complete:
            logger.warning("[COOKIE_MANAGER] Manager not initialized")
            return CookieState(is_valid=False, is_generating=False)

        with self._lock:
            if self._state:
                return self._state
            return CookieState(is_valid=False, is_generating=False)

    def get_cookie_file_path(self, domain: str | None = None) -> str | None:
        """Compatibility helper for callers expecting domain-based cookie path."""
        _ = domain
        return self.get_cookies()

    def refresh_if_needed(self) -> bool:
        """Check if cookies need refresh and regenerate if necessary.

        Returns:
            True if cookies were refreshed, False otherwise
        """
        logger.info("[COOKIE_MANAGER] Checking if cookies need refresh")

        with self._lock:
            if not self._state or self._state.should_regenerate():
                logger.info("[COOKIE_MANAGER] Refreshing cookies")

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                self._state = loop.run_until_complete(self._regenerate_cookies())
                return True

            logger.info("[COOKIE_MANAGER] Cookies are still valid")
            return False

    async def refresh_if_needed_async(self) -> bool:
        """Async version of refresh_if_needed.

        Returns:
            True if cookies were refreshed, False otherwise
        """
        logger.info("[COOKIE_MANAGER] Checking if cookies need refresh (async)")

        if not self._state or self._state.should_regenerate():
            logger.info("[COOKIE_MANAGER] Refreshing cookies")
            self._state = await self._regenerate_cookies()
            return True

        logger.info("[COOKIE_MANAGER] Cookies are still valid")
        return False

    def invalidate_and_regenerate(self, *, fast: bool = False) -> bool:
        """Invalidate current cookies and trigger regeneration.

        Args:
            fast: If True, use fast mode (no strict probe) for quick regeneration.

        Returns:
            True if regeneration was triggered, False otherwise
        """
        mode_label = "fast" if fast else "full"
        logger.info(
            "[COOKIE_MANAGER] Invalidating cookies and triggering %s regeneration", mode_label
        )

        with self._lock:
            # Invalidate current state
            if self._state:
                self._state.is_valid = False
                self._state.error_message = "Cookies invalidated due to failure"

            # Trigger regeneration
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._state = loop.run_until_complete(self._regenerate_cookies(fast_mode=fast))

            if self._state and self._state.is_valid:
                logger.info("[COOKIE_MANAGER] Cookies regenerated successfully after invalidation")
                return True
            logger.warning("[COOKIE_MANAGER] Cookie regeneration failed after invalidation")
        return False

    def is_ready(self) -> bool:
        """Check if cookie manager is ready with valid cookies.

        Returns:
            True if cookies are ready, False if generating or invalid
        """
        if not self._initialization_complete:
            return False

        with self._lock:
            return (
                self._state is not None and self._state.is_valid and not self._state.is_generating
            )

    def is_generating(self) -> bool:
        """Check if cookies are currently being generated.

        Returns:
            True if generation is in progress
        """
        # Check generator state first for real-time updates
        if (generator_state := self.generator.get_state()) and generator_state.is_generating:
            return True

        with self._lock:
            return self._state is not None and self._state.is_generating

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop.

        Returns:
            Event loop instance
        """
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _delete_old_cookie_files(self) -> None:
        """Delete old cookie files before regeneration."""
        if (
            self._state
            and self._state.cookie_path
            and (old_cookie_path := Path(self._state.cookie_path)).exists()
        ):
            try:
                old_cookie_path.unlink()
                logger.info(f"[COOKIE_MANAGER] Deleted expired cookie file: {old_cookie_path}")
            except Exception as e:
                logger.warning(f"[COOKIE_MANAGER] Failed to delete old cookie file: {e}")

        if (json_cookie_file := self.storage_dir / self.config.cookies.cookie_file_name).exists():
            try:
                json_cookie_file.unlink()
                logger.info(
                    f"[COOKIE_MANAGER] Deleted expired JSON cookie file: {json_cookie_file}"
                )
            except Exception as e:
                logger.warning(f"[COOKIE_MANAGER] Failed to delete JSON cookie file: {e}")

    def _try_convert_netscape(self) -> str | None:
        """Try to convert JSON cookies to Netscape format.

        Returns:
            Netscape file path if conversion succeeds, None otherwise
        """
        if (netscape_path := self.generator.convert_to_netscape_text()) and Path(
            netscape_path
        ).exists():
            return netscape_path
        return None

    def _regenerate_and_retry(self) -> str | None:
        """Regenerate cookies and retry getting file path.

        Returns:
            Cookie file path if regeneration succeeds, None otherwise
        """
        if self._state:
            self._state.is_valid = False
            self._state.error_message = "Cookie file does not exist"
        loop = self._get_event_loop()
        self._state = loop.run_until_complete(self._regenerate_cookies())
        if self._state and self._state.is_valid and self._state.cookie_path:
            cookie_path = self._state.cookie_path
            if Path(cookie_path).exists() and self.generator.validate_netscape_file(cookie_path):
                logger.info(f"[COOKIE_MANAGER] Returning regenerated cookie file: {cookie_path}")
                return cookie_path
        return None

    def _ensure_cookie_file_exists(self) -> str | None:
        """Ensure cookie file exists, regenerating if needed.

        Returns:
            Cookie file path if exists, None otherwise
        """
        cookie_path = self._state.cookie_path if self._state else None
        if not cookie_path or not Path(cookie_path).exists():
            logger.warning(f"[COOKIE_MANAGER] Cookie file does not exist: {cookie_path}")
            if netscape_path := self._try_convert_netscape():
                return netscape_path

            logger.warning(
                "[COOKIE_MANAGER] Cookie file missing, invalidating state and triggering regeneration"
            )
            return self._regenerate_and_retry()
        return cookie_path

    def _validate_and_regenerate_if_needed(self, cookie_path: str) -> str | None:
        """Validate cookie file and regenerate if invalid.

        Args:
            cookie_path: Path to cookie file

        Returns:
            Valid cookie file path, or None if validation fails
        """
        if self.generator.validate_netscape_file(cookie_path):
            return cookie_path

        logger.warning(
            "[COOKIE_MANAGER] Generated cookie file is invalid, invalidating state and triggering regeneration"
        )
        if self._state:
            self._state.is_valid = False
            self._state.error_message = "Cookie file validation failed"
        return self._regenerate_and_retry()

    async def _regenerate_cookies(self, fast_mode: bool = False) -> CookieState:
        """Regenerate cookies using the generator.

        Returns:
            New cookie state
        """
        logger.info("[COOKIE_MANAGER] Starting cookie regeneration")

        # Mark as generating
        generating_state = CookieState(
            is_generating=True,
            is_valid=False,
        )
        self._save_state(generating_state)

        max_attempts = self._strict_probe_retry_count + 1
        last_state = CookieState(is_valid=False, is_generating=False)

        for attempt in range(1, max_attempts + 1):
            new_state = await self.generator.generate_cookies(fast_mode=fast_mode)
            last_state = new_state

            if not new_state.is_valid or not new_state.cookie_path:
                logger.warning(
                    "[COOKIE_MANAGER] Cookie generation attempt "
                    f"{attempt}/{max_attempts} returned invalid state"
                )
                if attempt < max_attempts:
                    await self._sleep_before_retry(attempt)
                    continue
                self._save_state(new_state)
                return new_state

            if fast_mode:
                new_state.error_message = "Generated in fast mode; strict validation pending"
                self._save_state(new_state)
                logger.info(
                    "[COOKIE_MANAGER] Fast cookie regeneration complete. Strict validation deferred"
                )
                return new_state

            strict_valid, reason = self._probe_generated_cookie_strict(new_state.cookie_path)
            if strict_valid:
                new_state.error_message = None
                self._save_state(new_state)
                logger.info(
                    "[COOKIE_MANAGER] Cookie regeneration complete. "
                    f"Valid: {new_state.is_valid}, strict_probe=True"
                )
                return new_state

            logger.warning(
                "[COOKIE_MANAGER] Strict probe failed for generated cookies "
                f"(attempt {attempt}/{max_attempts}): {reason}"
            )
            if attempt < max_attempts:
                await self._sleep_before_retry(attempt)
                continue

            fallback_state = self._mark_generated_fallback_only(new_state, reason)
            self._save_state(fallback_state)
            return fallback_state

        self._save_state(last_state)
        return last_state

    def _probe_generated_cookie_strict(self, cookie_path: str) -> tuple[bool, str | None]:
        """Run strict YouTube probe validation on a generated cookie file."""
        if not self.generator.validate_netscape_file(cookie_path):
            return False, "Generated file failed Netscape validation"

        try:
            return probe_youtube_cookie_file(
                cookie_path=cookie_path,
                probe_urls=list(YOUTUBE_STRICT_PROBE_URLS),
                config=self.config,
            )
        except Exception as exc:
            return False, str(exc)

    def _start_background_strict_validation(self) -> None:
        """Run strict probe validation in background to avoid startup blocking."""
        if self._strict_probe_bg_thread and self._strict_probe_bg_thread.is_alive():
            return

        def run() -> None:
            try:
                self._background_strict_validation()
            except Exception as exc:
                logger.debug(
                    "[COOKIE_MANAGER] Background strict validation error: %s",
                    exc,
                    exc_info=True,
                )

        self._strict_probe_bg_thread = threading.Thread(
            target=run,
            daemon=True,
            name="YTStrictProbe",
        )
        self._strict_probe_bg_thread.start()

    def _background_strict_validation(self) -> None:
        with self._lock:
            state = self._state
            if not state or not state.is_valid or not state.cookie_path:
                return
            cookie_path = state.cookie_path

        strict_valid, reason = self._probe_generated_cookie_strict(cookie_path)
        if strict_valid:
            with self._lock:
                if self._state and self._state.cookie_path == cookie_path:
                    self._state.error_message = None
                    self._save_state(self._state)
            logger.info("[COOKIE_MANAGER] Background strict probe passed")
            return

        logger.warning("[COOKIE_MANAGER] Background strict probe failed: %s", reason)
        with self._lock:
            if self._state and self._state.cookie_path == cookie_path:
                self._state.is_valid = False
                self._state.error_message = f"Strict probe failed, cookies invalidated: {reason}"
                self._save_state(self._state)
        logger.info(
            "[COOKIE_MANAGER] Cookies invalidated after strict probe failure — "
            "will regenerate on next request"
        )

    async def _sleep_before_retry(self, attempt: int) -> None:
        """Bounded backoff before retrying cookie regeneration."""
        wait_seconds = self._strict_probe_backoff_seconds * attempt
        logger.info(
            f"[COOKIE_MANAGER] Waiting {wait_seconds:.1f}s before cookie regeneration retry"
        )
        await asyncio.sleep(wait_seconds)

    def _mark_generated_fallback_only(
        self,
        state: CookieState,
        reason: str | None,
    ) -> CookieState:
        """Mark generated cookies as fallback-only when strict probes keep failing."""
        state.is_generating = False
        state.is_valid = True
        details = reason or "Strict YouTube probe validation failed"
        state.error_message = (
            "Generated cookies are fallback-only; browser source should be preferred. "
            f"Reason: {details}"
        )
        return state

    def force_youtube_reprobe(self) -> list[dict[str, Any]]:
        """Force a browser reprobe and return resolved strategy metadata."""
        auto_cookie_manager = cast(IAutoCookieManager, self)
        coordinator = YouTubeCookieSourceCoordinator(
            auto_cookie_manager=auto_cookie_manager,
            storage_dir=self.storage_dir,
            config=self.config,
        )
        strategies = coordinator.force_reprobe()
        return [
            {
                "label": strategy.label,
                "source": strategy.source,
                "browser": strategy.browser,
            }
            for strategy in strategies
        ]

    def reset_youtube_probe_state(self) -> None:
        """Reset persisted YouTube browser probe state."""
        auto_cookie_manager = cast(IAutoCookieManager, self)
        coordinator = YouTubeCookieSourceCoordinator(
            auto_cookie_manager=auto_cookie_manager,
            storage_dir=self.storage_dir,
            config=self.config,
        )
        coordinator.reset_probe_state()

    def _load_state(self) -> CookieState:
        """Load cookie state from file.

        Returns:
            Loaded state or new empty state
        """
        if not self.state_file.exists():
            logger.info("[COOKIE_MANAGER] No existing state file found")
            # Check if cookies file exists - if so, create state with valid cookies
            if (cookie_file := self.storage_dir / self.config.cookies.netscape_file_name).exists():
                logger.info(f"[COOKIE_MANAGER] Found existing cookie file: {cookie_file}")
                # Create a state that reflects the existing cookie file
                return CookieState(
                    is_valid=True,
                    is_generating=False,
                    cookie_path=str(cookie_file),
                    generated_at=datetime.fromtimestamp(
                        cookie_file.stat().st_mtime, tz=timezone.utc
                    ),
                    expires_at=datetime.fromtimestamp(cookie_file.stat().st_mtime, tz=timezone.utc)
                    + timedelta(hours=self.config.cookies.cookie_expiry_hours),
                )
            return CookieState(is_valid=False, is_generating=False)

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)

            state = CookieState(**data)
            logger.info(
                f"[COOKIE_MANAGER] Loaded state. Valid: {state.is_valid}, "
                f"Expired: {state.is_expired()}"
            )
            return state

        except Exception as e:
            logger.error(f"[COOKIE_MANAGER] Failed to load state: {e}", exc_info=True)
            return CookieState(is_valid=False, is_generating=False)

    def _save_state(self, state: CookieState) -> None:
        """Save cookie state to file.

        Args:
            state: State to save
        """
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state.model_dump(), f, indent=2, default=str)

            logger.info("[COOKIE_MANAGER] State saved successfully")

        except Exception as e:
            logger.error(f"[COOKIE_MANAGER] Failed to save state: {e}", exc_info=True)

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("[COOKIE_MANAGER] Cleaning up cookie manager")
        self.generator.cleanup()
