import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

import requests

from src.core.config import AppConfig, get_config
from src.core.models import CookieState
from src.utils.logger import get_logger

from .radiojavan_cookie_generator import RadioJavanCookieGenerator

logger = get_logger(__name__)


class RadioJavanCookieManager:
    """Lifecycle manager for Radio Javan browser-generated cookies.

    Mirrors the YouTube ``CookieManager`` pattern but tailored for Radio Javan:
    * Cookies are stored as a JSON dict (name→value) rather than Netscape .txt
      because RJ downloads use ``requests`` instead of yt-dlp.
    * Validation probes the RJ host-lookup endpoint rather than YouTube.
    * No ``YouTubeCookieSourceCoordinator`` equivalent — Radio Javan only has
      generated guest cookies (no browser-import or manual-file sources).
    """

    def __init__(
        self,
        storage_dir: Path | None = None,
        config: AppConfig = get_config(),
    ) -> None:
        self.config = config
        rj = self.config.radiojavan
        self.storage_dir = storage_dir or rj.cookie_storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.storage_dir / rj.cookie_state_file_name
        self.generator = RadioJavanCookieGenerator(storage_dir=self.storage_dir, config=self.config)

        self._state: CookieState | None = None
        self._lock = Lock()
        self._initialization_complete = False
        self._retry_count = 2
        self._backoff_seconds = 2.0

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> CookieState:
        """Load or generate cookies.  Blocks until complete."""
        logger.info("[RJ_COOKIE_MANAGER] Initializing")

        with self._lock:
            self._state = self._load_state()

            if self._needs_regeneration(self._state):
                logger.info("[RJ_COOKIE_MANAGER] Cookies need regeneration")
                loop = self._get_event_loop()
                self._state = loop.run_until_complete(self._regenerate_cookies())
            else:
                logger.info("[RJ_COOKIE_MANAGER] Using existing valid cookies")
                if not self.state_file.exists():
                    self._save_state(self._state)

            self._initialization_complete = True
            return self._state

    async def initialize_async(self) -> CookieState:
        """Async variant of :meth:`initialize`."""
        logger.info("[RJ_COOKIE_MANAGER] Initializing (async)")

        self._state = self._load_state()
        if self._needs_regeneration(self._state):
            logger.info("[RJ_COOKIE_MANAGER] Cookies need regeneration")
            self._state = await self._regenerate_cookies()
        else:
            logger.info("[RJ_COOKIE_MANAGER] Using existing valid cookies")

        self._initialization_complete = True
        return self._state

    # ------------------------------------------------------------------
    # Public query / mutation API
    # ------------------------------------------------------------------

    def get_cookies(self) -> dict[str, str] | None:
        """Return cookie dict for use with ``requests``, or None."""
        if not self._initialization_complete:
            self.initialize()

        with self._lock:
            self._ensure_cookies_regenerated()

            if not self._state or not self._state.is_valid:
                logger.warning("[RJ_COOKIE_MANAGER] No valid cookies available")
                return None

            cookies = self.generator.load_cookies()
            if cookies:
                return cookies

            # Cookie file missing/corrupt — regenerate
            logger.warning("[RJ_COOKIE_MANAGER] Cookie file unreadable, regenerating")
            loop = self._get_event_loop()
            self._state = loop.run_until_complete(self._regenerate_cookies())
            return self.generator.load_cookies()

    def get_state(self) -> CookieState:
        if not self._initialization_complete:
            return CookieState(is_valid=False, is_generating=False)
        with self._lock:
            return self._state or CookieState(is_valid=False, is_generating=False)

    def refresh_if_needed(self) -> bool:
        """Regenerate cookies if expired or nearing expiry."""
        with self._lock:
            if not self._state or self._state.should_regenerate():
                logger.info("[RJ_COOKIE_MANAGER] Refreshing cookies")
                loop = self._get_event_loop()
                self._state = loop.run_until_complete(self._regenerate_cookies())
                return True
            logger.info("[RJ_COOKIE_MANAGER] Cookies still valid")
            return False

    def invalidate_and_regenerate(self) -> bool:
        """Force-invalidate and regenerate (e.g. after a Cloudflare block)."""
        logger.info("[RJ_COOKIE_MANAGER] Invalidating and regenerating")
        with self._lock:
            if self._state:
                self._state.is_valid = False
                self._state.error_message = "Cookies invalidated due to failure"

            loop = self._get_event_loop()
            self._state = loop.run_until_complete(self._regenerate_cookies())
            if self._state and self._state.is_valid:
                logger.info("[RJ_COOKIE_MANAGER] Regeneration after invalidation succeeded")
                return True
            logger.warning("[RJ_COOKIE_MANAGER] Regeneration after invalidation failed")
            return False

    def is_ready(self) -> bool:
        if not self._initialization_complete:
            return False
        with self._lock:
            return (
                self._state is not None and self._state.is_valid and not self._state.is_generating
            )

    def is_generating(self) -> bool:
        if (gen_state := self.generator.get_state()) and gen_state.is_generating:
            return True
        with self._lock:
            return self._state is not None and self._state.is_generating

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _needs_regeneration(self, state: CookieState) -> bool:
        if not state.is_valid:
            return True
        if state.is_expired() or state.should_regenerate():
            return True
        if not state.cookie_path or not Path(state.cookie_path).exists():
            return True
        if not self.generator.validate_cookie_file():
            logger.warning("[RJ_COOKIE_MANAGER] Cookie file invalid, forcing regeneration")
            return True
        return False

    def _ensure_cookies_regenerated(self) -> None:
        if not self._state or not self._state.is_valid or self._state.should_regenerate():
            self._delete_old_cookie_files()
            logger.info("[RJ_COOKIE_MANAGER] Triggering cookie generation")
            loop = self._get_event_loop()
            self._state = loop.run_until_complete(self._regenerate_cookies())

    def _delete_old_cookie_files(self) -> None:
        if (
            self._state
            and self._state.cookie_path
            and (old := Path(self._state.cookie_path)).exists()
        ):
            try:
                old.unlink()
                logger.info("[RJ_COOKIE_MANAGER] Deleted old cookie file: %s", old)
            except Exception as exc:
                logger.warning("[RJ_COOKIE_MANAGER] Failed to delete old cookie file: %s", exc)

    async def _regenerate_cookies(self) -> CookieState:
        """Generate cookies with retry + validation probe."""
        logger.info("[RJ_COOKIE_MANAGER] Starting regeneration")
        generating_state = CookieState(is_generating=True, is_valid=False)
        self._save_state(generating_state)

        max_attempts = self._retry_count + 1
        last_state = CookieState(is_valid=False, is_generating=False)

        for attempt in range(1, max_attempts + 1):
            new_state = await self.generator.generate_cookies()
            last_state = new_state

            if not new_state.is_valid or not new_state.cookie_path:
                logger.warning(
                    "[RJ_COOKIE_MANAGER] Generation attempt %d/%d failed",
                    attempt,
                    max_attempts,
                )
                if attempt < max_attempts:
                    await asyncio.sleep(self._backoff_seconds * attempt)
                    continue
                self._save_state(new_state)
                return new_state

            # Validate the generated cookies by probing RJ
            probe_ok, reason = self._probe_cookies(new_state.cookie_path)
            if probe_ok:
                new_state.error_message = None
                self._save_state(new_state)
                logger.info("[RJ_COOKIE_MANAGER] Regeneration complete (probe passed)")
                return new_state

            logger.warning(
                "[RJ_COOKIE_MANAGER] Probe failed attempt %d/%d: %s",
                attempt,
                max_attempts,
                reason,
            )
            if attempt < max_attempts:
                await asyncio.sleep(self._backoff_seconds * attempt)
                continue

            # Accept cookies as fallback-only
            new_state.error_message = f"Generated cookies are fallback-only; probe failed: {reason}"
            self._save_state(new_state)
            return new_state

        self._save_state(last_state)
        return last_state

    def _probe_cookies(self, cookie_path: str) -> tuple[bool, str | None]:
        """Probe Radio Javan with the generated cookies to check validity."""
        cookies = self.generator.load_cookies()
        if not cookies:
            return False, "Could not load cookies from file"

        rj = self.config.radiojavan
        probe_url = rj.cookie_validation_url
        try:
            response = requests.get(
                probe_url,
                cookies=cookies,
                headers={"User-Agent": self.config.network.user_agent},
                timeout=rj.default_timeout,
                allow_redirects=True,
            )
            # A successful probe means we didn't get a Cloudflare challenge
            if response.status_code == 200:
                text = response.text.lower()
                cf_markers = ("cf_chl", "cloudflare", "attention required", "just a moment")
                if any(m in text for m in cf_markers):
                    return False, "Probe response contains Cloudflare challenge markers"
                logger.info("[RJ_COOKIE_MANAGER] Probe succeeded (HTTP 200)")
                return True, None

            if response.status_code in {403, 429, 503}:
                return False, f"Probe returned HTTP {response.status_code}"

            # Other status codes — accept cautiously
            logger.info(
                "[RJ_COOKIE_MANAGER] Probe returned HTTP %d, accepting cautiously",
                response.status_code,
            )
            return True, None

        except Exception as exc:
            return False, f"Probe request failed: {exc!s}"

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> CookieState:
        if not self.state_file.exists():
            logger.info("[RJ_COOKIE_MANAGER] No state file found")
            # Check for existing cookie file
            rj = self.config.radiojavan
            cookie_file = self.storage_dir / rj.cookie_data_file_name
            if cookie_file.exists():
                logger.info("[RJ_COOKIE_MANAGER] Found existing cookie file: %s", cookie_file)
                mtime = datetime.fromtimestamp(cookie_file.stat().st_mtime, tz=timezone.utc)
                return CookieState(
                    is_valid=True,
                    is_generating=False,
                    cookie_path=str(cookie_file),
                    generated_at=mtime,
                    expires_at=mtime + timedelta(hours=rj.cookie_ttl_hours),
                )
            return CookieState(is_valid=False, is_generating=False)

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
            state = CookieState(**data)
            logger.info(
                "[RJ_COOKIE_MANAGER] Loaded state (valid=%s, expired=%s)",
                state.is_valid,
                state.is_expired(),
            )
            return state
        except Exception as exc:
            logger.error("[RJ_COOKIE_MANAGER] Failed to load state: %s", exc, exc_info=True)
            return CookieState(is_valid=False, is_generating=False)

    def _save_state(self, state: CookieState) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state.model_dump(), f, indent=2, default=str)
            logger.info("[RJ_COOKIE_MANAGER] State saved")
        except Exception as exc:
            logger.error("[RJ_COOKIE_MANAGER] Failed to save state: %s", exc, exc_info=True)

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def cleanup(self) -> None:
        logger.info("[RJ_COOKIE_MANAGER] Cleaning up")
        self.generator.cleanup()
