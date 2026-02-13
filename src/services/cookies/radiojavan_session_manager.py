from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

import requests
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RadioJavanSessionManager:
    """Centralized RadioJavan browser session storage with TTL refresh."""

    CHALLENGE_MARKERS = (
        "window._cf_chl_opt",
        "/cdn-cgi/challenge-platform/h/",
        "challenge-platform/h/b/orchestrate/chl_page",
        "attention required! | cloudflare",
        "just a moment...",
    )
    TRANSPORT_BLOCK_MARKERS = (
        "err_connection_closed",
        "unexpected_eof_while_reading",
        "ssl_error_syscall",
        "tls connect error",
        "ssleoferror",
    )
    DEFAULT_RETRY_COOLDOWN_SECONDS = 180

    def __init__(
        self,
        storage_dir: Path | None = None,
        config: AppConfig = get_config(),
    ):
        self.config = config
        self.enabled = self.config.radiojavan.session_enabled
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.storage_dir / self.config.radiojavan.session_state_file_name
        self.session_file = self.storage_dir / self.config.radiojavan.session_data_file_name
        self._lock = RLock()
        self._state: dict[str, str | bool | int | None] | None = None
        self._initialized = False

    def initialize(self) -> dict[str, str | bool | int | None]:
        with self._lock:
            self._state = self._load_state()
            if self._needs_refresh(self._state):
                self._state = self._refresh_session_locked()
            self._initialized = True
            return self._state

    def get_state(self) -> dict[str, str | bool | int | None]:
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._state or self._invalid_state("Session manager not initialized")

    def get_request_context(
        self,
        force_refresh: bool = False,
    ) -> tuple[dict[str, str], dict[str, str]] | None:
        if not self.enabled:
            return None

        with self._lock:
            if not self._initialized:
                self.initialize()

            if force_refresh and self._is_retry_cooldown_active(self._state):
                logger.debug(
                    "[RADIOJAVAN_SESSION] Refresh requested during retry cooldown; "
                    "using current invalid state"
                )
                return None

            if force_refresh or self._needs_refresh(self._state):
                self._state = self._refresh_session_locked()

            if not self._is_state_valid(self._state):
                return None

            if not (session_data := self._load_session_data()):
                return None

            headers = self._session_headers(session_data)
            cookies = self._session_cookie_jar(session_data)
            if not headers or not cookies:
                return None
            return headers, cookies

    def refresh_session(self) -> bool:
        with self._lock:
            self._state = self._refresh_session_locked()
            return self._is_state_valid(self._state)

    def invalidate_and_refresh(self) -> bool:
        with self._lock:
            if self._is_retry_cooldown_active(self._state):
                return False

            self._state = self._invalid_state("Session invalidated after challenge response")
            self._save_state(self._state)
            self._state = self._run_generate_session()
            return self._is_state_valid(self._state)

    def _refresh_session_locked(self) -> dict[str, str | bool | int | None]:
        if not self.enabled:
            state = self._failure_state("RadioJavan session manager disabled")
            self._save_state(state)
            return state

        if self._is_retry_cooldown_active(self._state):
            return self._state or self._failure_state("Session refresh cooldown is active")

        return self._run_generate_session()

    def _run_generate_session(self) -> dict[str, str | bool | int | None]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._generate_session())

        def run_in_thread() -> dict[str, str | bool | int | None]:
            return asyncio.run(self._generate_session())

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(run_in_thread).result()

    async def _generate_session(self) -> dict[str, str | bool | int | None]:  # noqa: PLR0911
        generating = self._invalid_state(None)
        generating["is_generating"] = True
        self._save_state(generating)

        try:
            async with async_playwright() as playwright:
                if (browser := await self._launch_browser(playwright)) is None:
                    state = self._failure_state("Failed to launch browser")
                    self._save_state(state)
                    return state

                context, page = await self._create_context_and_page(browser)
                if not context or not page:
                    with contextlib.suppress(Exception):
                        await browser.close()
                    state = self._failure_state("Failed to create browser context")
                    self._save_state(state)
                    return state

                session_data = await self._extract_session_data(context, page)
                with contextlib.suppress(Exception):
                    await browser.close()

                if not session_data:
                    state = self._failure_state("Could not collect valid RadioJavan session")
                    self._save_state(state)
                    return state

                if not self._validate_session_data(session_data):
                    state = self._failure_state(
                        "Collected session still triggers Cloudflare challenge"
                    )
                    self._save_state(state)
                    return state

                self._save_session_data(session_data)
                state = self._valid_state(session_data)
                self._save_state(state)
                return state
        except ImportError as e:
            state = self._failure_state(
                "Playwright missing for RadioJavan session generation. "
                "Install with: pip install playwright && playwright install chromium"
            )
            logger.error("[RADIOJAVAN_SESSION] %s (%s)", state["error_message"], e)
            self._save_state(state)
            return state
        except Exception as e:
            state = self._failure_state(f"Session generation failed: {e!s}")
            logger.error("[RADIOJAVAN_SESSION] %s", state["error_message"], exc_info=True)
            self._save_state(state)
            return state

    async def _launch_browser(self, playwright: Playwright) -> Browser | None:
        try:
            return await playwright.chromium.launch(
                headless=self.config.radiojavan.session_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
        except Exception as e:
            logger.error("[RADIOJAVAN_SESSION] Browser launch failed: %s", e)
            return None

    async def _create_context_and_page(
        self,
        browser: Browser,
    ) -> tuple[BrowserContext | None, Page | None]:
        try:
            context = await browser.new_context(
                user_agent=self.config.network.user_agent,
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers=self._default_headers(),
            )
            page = await context.new_page()
            return context, page
        except Exception as e:
            logger.error("[RADIOJAVAN_SESSION] Context creation failed: %s", e)
            return None, None

    async def _extract_session_data(
        self,
        context: BrowserContext,
        page: Page,
    ) -> dict[str, object] | None:
        captured_headers: dict[str, str] = {}

        def capture_headers(request) -> None:
            url = request.url.lower()
            if "radiojavan.com" not in url and "rj.app" not in url:
                return
            if captured_headers:
                return
            captured_headers.update(self._sanitize_headers(dict(request.headers)))

        page.on("request", capture_headers)

        timeout_ms = self.config.radiojavan.session_generation_timeout_seconds * 1000
        wait_seconds = self.config.radiojavan.session_wait_after_load_seconds

        try:
            await page.goto(
                self.config.radiojavan.session_bootstrap_url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            await asyncio.sleep(wait_seconds)
            await page.goto(
                self.config.radiojavan.session_validation_url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            await asyncio.sleep(wait_seconds)
        except Exception as e:
            if self.is_transport_block_error(e):
                logger.warning(
                    "[RADIOJAVAN_SESSION] Transport-level block during browser navigation: %s",
                    e,
                )
            else:
                logger.warning(
                    "[RADIOJAVAN_SESSION] Navigation failed during session extraction: %s",
                    e,
                )

        cookies = await context.cookies()
        if not (filtered := [cookie for cookie in cookies if self._is_radiojavan_cookie(cookie)]):
            return None

        return {
            "headers": captured_headers or self._default_headers(),
            "cookies": filtered,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(hours=self.config.radiojavan.session_ttl_hours)
            ).isoformat(),
        }

    def _validate_session_data(self, session_data: dict[str, object]) -> bool:
        cookies = self._session_cookie_jar(session_data)
        headers = self._session_headers(session_data)
        if not cookies or not headers:
            return False

        check_urls = [
            self.config.radiojavan.session_validation_url,
            self.config.radiojavan.session_bootstrap_url,
        ]
        for url in check_urls:
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    timeout=self.config.radiojavan.default_timeout,
                    allow_redirects=True,
                )
            except Exception as exc:
                if self.is_transport_block_error(exc):
                    logger.warning(
                        "[RADIOJAVAN_SESSION] Transport-level block while validating session: %s",
                        exc,
                    )
                return False

            if self.is_challenge_response(
                response.text,
                response.headers.get("cf-mitigated"),
                response.status_code,
            ):
                return False
        return True

    @classmethod
    def is_challenge_response(
        cls,
        text: str,
        cf_mitigated: str | None = None,
        status_code: int | None = None,
    ) -> bool:
        if cf_mitigated == "challenge":
            return True
        if status_code == 403 and cls._looks_like_challenge_page(text):
            return True
        return cls._looks_like_challenge_page(text)

    @classmethod
    def _looks_like_challenge_page(cls, text: str) -> bool:
        if not isinstance(text, str) or not text:
            return False
        lowered = text.lower()
        if any(marker in lowered for marker in cls.CHALLENGE_MARKERS):
            return True

        # Cloudflare JSD snippets can be present on normal pages; only treat as
        # challenge when challenge-related identifiers coexist.
        if "cdn-cgi/challenge-platform/scripts/jsd/main.js" in lowered:
            required = ("_cf_chl_opt", "orchestrate/chl_page", "challenge-form")
            return any(marker in lowered for marker in required)

        return False

    @classmethod
    def is_transport_block_error(cls, error: Exception | str) -> bool:
        """Detect low-level TLS/transport blocking before HTTP challenge pages."""
        message = str(error).lower()
        return any(marker in message for marker in cls.TRANSPORT_BLOCK_MARKERS)

    def _session_headers(self, session_data: dict[str, object]) -> dict[str, str]:
        raw_headers = session_data.get("headers")
        if not isinstance(raw_headers, dict):
            return {}
        headers = {
            key: value
            for key, value in raw_headers.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        if "User-Agent" not in headers and "user-agent" not in headers:
            headers["User-Agent"] = self.config.network.user_agent
        return headers

    def _session_cookie_jar(
        self,
        session_data: dict[str, object],
    ) -> dict[str, str] | None:
        raw_cookies = session_data.get("cookies")
        if not isinstance(raw_cookies, list):
            return None

        jar: dict[str, str] = {}
        for item in raw_cookies:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if not isinstance(name, str) or not isinstance(value, str):
                continue
            jar[name] = value

        if not jar:
            return None
        return jar

    def _is_radiojavan_cookie(self, cookie: Mapping[str, Any]) -> bool:
        domain = cookie.get("domain")
        if not isinstance(domain, str):
            return False
        lowered = domain.lower()
        return "radiojavan.com" in lowered or "rj.app" in lowered

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        blocked = {"cookie", "host", "content-length", "content-type", "connection"}
        safe_headers: dict[str, str] = {}
        for key, value in headers.items():
            if (lowered := key.lower()) in blocked or lowered.startswith(":"):
                continue
            safe_headers[key] = value

        if "User-Agent" not in safe_headers and "user-agent" not in safe_headers:
            safe_headers["User-Agent"] = self.config.network.user_agent
        return safe_headers

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.config.network.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }

    def _invalid_state(self, error_message: str | None) -> dict[str, str | bool | int | None]:
        return {
            "is_valid": False,
            "is_generating": False,
            "generated_at": None,
            "expires_at": None,
            "next_retry_at": None,
            "cookie_count": 0,
            "error_message": error_message,
        }

    def _failure_state(self, error_message: str) -> dict[str, str | bool | int | None]:
        state = self._invalid_state(error_message)
        state["next_retry_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=self._retry_cooldown_seconds())
        ).isoformat()
        return state

    def _valid_state(self, session_data: dict[str, object]) -> dict[str, str | bool | int | None]:
        cookies_value = session_data.get("cookies")
        cookie_count = len(cookies_value) if isinstance(cookies_value, list) else 0
        generated_at = session_data.get("generated_at")
        expires_at = session_data.get("expires_at")
        return {
            "is_valid": True,
            "is_generating": False,
            "generated_at": generated_at if isinstance(generated_at, str) else None,
            "expires_at": expires_at if isinstance(expires_at, str) else None,
            "next_retry_at": None,
            "cookie_count": cookie_count,
            "error_message": None,
        }

    def _needs_refresh(
        self,
        state: dict[str, str | bool | int | None] | None,
    ) -> bool:
        if not self.enabled:
            return False

        if not state:
            return True

        if not bool(state.get("is_valid")):
            return not self._is_retry_cooldown_active(state)

        if not self.session_file.exists():
            return True

        expires_at = state.get("expires_at")
        if (
            expires_dt := self._parse_datetime(expires_at) if isinstance(expires_at, str) else None
        ) is None:
            return True

        refresh_margin = timedelta(minutes=self.config.radiojavan.session_refresh_margin_minutes)
        return datetime.now(timezone.utc) >= (expires_dt - refresh_margin)

    def _is_retry_cooldown_active(
        self,
        state: dict[str, str | bool | int | None] | None,
    ) -> bool:
        if not state:
            return False
        next_retry_at = state.get("next_retry_at")
        if not isinstance(next_retry_at, str):
            return False
        if (retry_dt := self._parse_datetime(next_retry_at)) is None:
            return False
        return datetime.now(timezone.utc) < retry_dt

    def _retry_cooldown_seconds(self) -> int:
        configured = getattr(
            self.config.radiojavan,
            "session_retry_cooldown_seconds",
            self.DEFAULT_RETRY_COOLDOWN_SECONDS,
        )
        if not isinstance(configured, int) or configured < 0:
            return self.DEFAULT_RETRY_COOLDOWN_SECONDS
        return configured

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
        except Exception:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _is_state_valid(self, state: dict[str, str | bool | int | None] | None) -> bool:
        return bool(state and state.get("is_valid") and self.session_file.exists())

    def _load_state(self) -> dict[str, str | bool | int | None]:
        if not self.state_file.exists():
            return self._invalid_state("Session state missing")
        try:
            with open(self.state_file, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return self._invalid_state("Failed to load session state")
        if not isinstance(raw, dict):
            return self._invalid_state("Session state file is not a JSON object")
        return {
            "is_valid": bool(raw.get("is_valid", False)),
            "is_generating": bool(raw.get("is_generating", False)),
            "generated_at": raw.get("generated_at")
            if isinstance(raw.get("generated_at"), str)
            else None,
            "expires_at": raw.get("expires_at") if isinstance(raw.get("expires_at"), str) else None,
            "next_retry_at": raw.get("next_retry_at")
            if isinstance(raw.get("next_retry_at"), str)
            else None,
            "cookie_count": int(raw.get("cookie_count", 0)),
            "error_message": raw.get("error_message")
            if isinstance(raw.get("error_message"), str)
            else None,
        }

    def _save_state(self, state: dict[str, str | bool | int | None]) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=True)
        except Exception as e:
            logger.warning("[RADIOJAVAN_SESSION] Failed to save state: %s", e)

    def _save_session_data(self, session_data: dict[str, object]) -> None:
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=True)

    def _load_session_data(self) -> dict[str, object] | None:
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
        return data if isinstance(data, dict) else None
