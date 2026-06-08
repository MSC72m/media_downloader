from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from src.core.config import AppConfig, get_config
from src.core.models import CookieState
from src.utils.logger import get_logger

from .cookie_generator import CookieGenerator

logger = get_logger(__name__)


class SiteCookieManager:
    """Generic cookie manager for any site using Playwright browser automation.

    Subclass and override SITE_URL, SITE_NAME, COOKIE_DIR, STATE_FILE to
    create site-specific managers.
    """

    SITE_URL: str = ""
    SITE_NAME: str = ""
    COOKIE_DIR: str = ""
    STATE_FILE: str = ""

    def __init__(self, storage_dir: Path | None = None, config: AppConfig = get_config()) -> None:
        self.config = config
        base_dir = storage_dir or self.config.cookies.storage_dir
        self.cookie_dir = base_dir / self.COOKIE_DIR
        self.cookie_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.cookie_dir / self.STATE_FILE
        self.generator = CookieGenerator(storage_dir=self.cookie_dir, config=self.config)

        self._state: CookieState | None = None
        self._lock = Lock()
        self._initialization_complete = False

    def initialize(self) -> CookieState:
        """Load or generate site cookies (blocking, creates event loop).

        Returns:
            Current cookie state
        """
        tag = self._tag()
        logger.info(f"[{tag}] Initializing {self.SITE_NAME} cookie manager")

        with self._lock:
            self._state = self._load_state()
            if self._needs_regeneration(self._state):
                logger.info(f"[{tag}] Cookies need regeneration")
                loop = self._get_event_loop()
                self._state = loop.run_until_complete(
                    self.generator.generate_site_cookies(
                        site_url=self.SITE_URL,
                        site_name=self.SITE_NAME,
                        fast_mode=True,
                    )
                )
                if self._state and self._state.is_valid:
                    self._save_state(self._state)
            elif self._state and self._state.is_valid:
                logger.info(f"[{tag}] Using existing valid cookies")

            self._initialization_complete = True
            return self._state or CookieState(is_valid=False, is_generating=False)

    async def initialize_async(self) -> CookieState:
        """Async version of initialize.

        Returns:
            Current cookie state
        """
        tag = self._tag()
        logger.info(f"[{tag}] Initializing {self.SITE_NAME} cookie manager (async)")

        self._state = self._load_state()
        if self._needs_regeneration(self._state):
            logger.info(f"[{tag}] Cookies need regeneration (async)")
            self._state = await self.generator.generate_site_cookies(
                site_url=self.SITE_URL,
                site_name=self.SITE_NAME,
                fast_mode=True,
            )
            if self._state and self._state.is_valid:
                self._save_state(self._state)

        self._initialization_complete = True
        return self._state or CookieState(is_valid=False, is_generating=False)

    def get_cookies(self) -> str | None:
        """Get path to site cookie file.

        Returns:
            Path to Netscape cookie file or None if not available
        """
        if not self._initialization_complete:
            return None

        with self._lock:
            if not self._state or not self._state.is_valid:
                return None
            if not (cookie_path := self._state.cookie_path):
                return None
            if Path(cookie_path).exists():
                return cookie_path
        return None

    def is_ready(self) -> bool:
        return self._initialization_complete and self._state is not None and self._state.is_valid

    def is_generating(self) -> bool:
        return bool(self._state and self._state.is_generating)

    def get_state(self) -> CookieState:
        return self._state or CookieState(is_valid=False, is_generating=False)

    def refresh_if_needed(self) -> bool:
        with self._lock:
            if not self._needs_regeneration(self._state):
                return False
        self.invalidate_and_regenerate()
        return True

    def invalidate_and_regenerate(self) -> bool:
        with self._lock:
            self._state = CookieState(is_valid=False, is_generating=False)
            self._save_state(self._state)
        thread = threading.Thread(target=self._background_regenerate, daemon=True)
        thread.start()
        return True

    def cleanup(self) -> None:
        tag = self._tag()
        logger.info(f"[{tag}] Cleanup completed")

    def _background_regenerate(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_state = loop.run_until_complete(
            self.generator.generate_site_cookies(
                site_url=self.SITE_URL,
                site_name=self.SITE_NAME,
                fast_mode=True,
            )
        )
        with self._lock:
            if new_state and new_state.is_valid:
                self._state = new_state
                self._save_state(self._state)

    def _load_state(self) -> CookieState | None:
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file) as f:
                data = json.load(f)
            return CookieState(
                is_valid=data.get("is_valid", False),
                is_generating=data.get("is_generating", False),
                cookie_path=data.get("cookie_path"),
                error_message=data.get("error_message"),
            )
        except Exception:
            return None

    def _save_state(self, state: CookieState) -> None:
        data = {
            "is_valid": state.is_valid,
            "is_generating": state.is_generating,
            "cookie_path": state.cookie_path,
            "error_message": state.error_message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def _needs_regeneration(self, state: CookieState | None) -> bool:
        if state is None:
            return True
        if state.is_generating:
            return False
        return not state.is_valid

    @staticmethod
    def _get_event_loop() -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    @staticmethod
    def _tag() -> str:
        return "SITE_COOKIE_MANAGER"
