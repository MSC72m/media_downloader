"""Cookie manager service for managing cookie state and lifecycle."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from src.core.config import get_config, AppConfig
from src.core.models import CookieState
from src.utils.error_helpers import extract_error_context
from src.utils.logger import get_logger

from .cookie_generator import CookieGenerator

logger = get_logger(__name__)


class CookieManager:
    """Manages cookie lifecycle, state, and automatic regeneration."""

    def __init__(self, storage_dir: Optional[Path] = None, config: AppConfig = get_config()):
        """Initialize cookie manager.

        Args:
            storage_dir: Directory to store cookies and state (uses config if not provided)
            config: AppConfig instance (defaults to get_config() if None)
        """
        self.config = config
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.storage_dir / self.config.cookies.state_file_name
        self.generator = CookieGenerator(storage_dir=self.storage_dir, config=self.config)

        self._state: Optional[CookieState] = None
        self._lock = Lock()
        self._initialization_complete = False

    def initialize(self) -> CookieState:
        """Initialize cookie manager - load or generate cookies.

        Returns:
            Current cookie state
        """
        logger.info("[COOKIE_MANAGER] Initializing cookie manager")

        with self._lock:
            # Load existing state
            self._state = self._load_state()

            # Check if we need to regenerate
            if self._state.should_regenerate():
                logger.info("[COOKIE_MANAGER] Cookies need regeneration")
                # Run async generation in sync context
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                self._state = loop.run_until_complete(self._regenerate_cookies())
            else:
                logger.info("[COOKIE_MANAGER] Using existing valid cookies")

            self._initialization_complete = True
            return self._state

    async def initialize_async(self) -> CookieState:
        """Async version of initialize for use in async contexts.

        Returns:
            Current cookie state
        """
        logger.info("[COOKIE_MANAGER] Initializing cookie manager (async)")

        # Load existing state
        self._state = self._load_state()

        # Check if we need to regenerate
        if self._state.should_regenerate():
            logger.info("[COOKIE_MANAGER] Cookies need regeneration")
            self._state = await self._regenerate_cookies()
        else:
            logger.info("[COOKIE_MANAGER] Using existing valid cookies")

        self._initialization_complete = True
        return self._state

    def get_cookies(self) -> Optional[str]:
        """Get path to cookie file for use with yt-dlp.
        
        If no valid cookies exist, triggers generation automatically.

        Returns:
            Path to Netscape format cookie file, or None if not available
        """
        if not self._initialization_complete:
            logger.info("[COOKIE_MANAGER] Manager not initialized, initializing now")
            self.initialize()

        with self._lock:
            if not self._state or not self._state.is_valid or self._state.should_regenerate():
                logger.info("[COOKIE_MANAGER] No valid cookies available, triggering generation")
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                self._state = loop.run_until_complete(self._regenerate_cookies())
                
                if not self._state or not self._state.is_valid:
                    logger.warning("[COOKIE_MANAGER] Cookie generation failed")
                    return None

            netscape_path = self.generator.convert_to_netscape_text()

            if not netscape_path or not Path(netscape_path).exists():
                logger.warning("[COOKIE_MANAGER] Cookie conversion failed")
                return None

            if self.generator.validate_netscape_file(netscape_path):
                logger.info(f"[COOKIE_MANAGER] Returning validated cookie file: {netscape_path}")
                return netscape_path

            logger.warning("[COOKIE_MANAGER] Generated cookie file is invalid")
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

    def is_ready(self) -> bool:
        """Check if cookie manager is ready with valid cookies.

        Returns:
            True if cookies are ready, False if generating or invalid
        """
        if not self._initialization_complete:
            return False

        with self._lock:
            return (
                self._state is not None
                and self._state.is_valid
                and not self._state.is_generating
            )

    def is_generating(self) -> bool:
        """Check if cookies are currently being generated.

        Returns:
            True if generation is in progress
        """
        with self._lock:
            return self._state is not None and self._state.is_generating

    async def _regenerate_cookies(self) -> CookieState:
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

        # Generate cookies
        new_state = await self.generator.generate_cookies()

        # Save new state
        self._save_state(new_state)

        logger.info(
            f"[COOKIE_MANAGER] Cookie regeneration complete. Valid: {new_state.is_valid}"
        )

        return new_state

    def _load_state(self) -> CookieState:
        """Load cookie state from file.

        Returns:
            Loaded state or new empty state
        """
        if not self.state_file.exists():
            logger.info("[COOKIE_MANAGER] No existing state file found")
            return CookieState(is_valid=False, is_generating=False)

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
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
