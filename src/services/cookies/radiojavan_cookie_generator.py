from __future__ import annotations

import asyncio
import contextlib
import json
import random
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright

from src.core.config import AppConfig, get_config
from src.core.models import CookieState
from src.utils.logger import get_logger
from src.utils.user_agent_rotator import get_random_user_agent

logger = get_logger(__name__)

_RADIOJAVAN_WARMUP_PAGES = [
    "https://www.radiojavan.com/",
    "https://www.radiojavan.com/mp3s",
    "https://www.radiojavan.com/videos",
]


class RadioJavanCookieGenerator:
    """Playwright-based cookie generator for Radio Javan.

    Navigates to Radio Javan in a headless Chromium browser, allows Cloudflare
    challenges to complete, and extracts cookies for use with the ``requests``
    library.  Cookies are persisted as a JSON file on disk (not Netscape .txt,
    since Radio Javan downloads use ``requests`` rather than yt-dlp).
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
        self.cookie_file = self.storage_dir / rj.cookie_data_file_name

        self._state: CookieState | None = None
        self._state_lock = Lock()

    # ------------------------------------------------------------------
    # State helpers (thread-safe)
    # ------------------------------------------------------------------

    def get_state(self) -> CookieState | None:
        with self._state_lock:
            return self._state

    def _update_state(self, state: CookieState) -> None:
        with self._state_lock:
            self._state = state

    def _create_error_state(self, error_msg: str) -> CookieState:
        state = CookieState(
            is_generating=False,
            is_valid=False,
            error_message=error_msg,
        )
        self._update_state(state)
        return state

    # ------------------------------------------------------------------
    # Browser helpers
    # ------------------------------------------------------------------

    async def _launch_browser(self, playwright: Playwright) -> Browser | None:
        from src.services.cookies.playwright_bootstrap import wait_for_chromium

        if not wait_for_chromium(timeout=120):
            logger.error("[RJ_COOKIE_GENERATOR] Chromium not available after waiting")
            return None

        rj = self.config.radiojavan
        try:
            return await playwright.chromium.launch(
                headless=rj.cookie_headless,
                args=[
                    "--incognito",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
        except Exception as exc:
            logger.error("[RJ_COOKIE_GENERATOR] Failed to launch browser: %s", exc)
            return None

    async def _create_browser_context(self, browser: Browser) -> tuple[BrowserContext, Page] | None:
        try:
            user_agent = get_random_user_agent()
            logger.info("[RJ_COOKIE_GENERATOR] Using random user agent: %s...", user_agent[:50])

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=user_agent,
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers={
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                },
            )
            page = await context.new_page()
            return context, page
        except Exception as exc:
            logger.error("[RJ_COOKIE_GENERATOR] Failed to create browser context: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Page interaction helpers
    # ------------------------------------------------------------------

    async def _wait_for_network_idle(self, page: Page, timeout: float = 5.0) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=int(timeout * 1000))
        except Exception:
            logger.debug("[RJ_COOKIE_GENERATOR] Network idle timeout, continuing")

    async def _scroll_page(self, page: Page) -> None:
        try:
            await page.evaluate("() => window.scrollTo(0, 400)")
            await asyncio.sleep(0.5)
            await page.evaluate("() => window.scrollTo(0, 900)")
            await asyncio.sleep(0.5)
            await page.evaluate("() => window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)
        except Exception:
            logger.debug("[RJ_COOKIE_GENERATOR] Scroll interaction failed, continuing")

    async def _handle_cloudflare_challenge(self, page: Page) -> None:
        """Wait for Cloudflare challenge to resolve (if present)."""
        rj = self.config.radiojavan
        wait_seconds = rj.cookie_wait_after_load_seconds

        # First wait: let challenge scripts load
        await asyncio.sleep(wait_seconds)

        # Check for Cloudflare challenge markers
        try:
            page_text = await page.inner_text("body")
        except Exception:
            page_text = ""

        cf_markers = ("cf_chl", "cloudflare", "attention required", "just a moment")
        if any(marker in page_text.lower() for marker in cf_markers):
            logger.info("[RJ_COOKIE_GENERATOR] Cloudflare challenge detected, waiting...")
            # Give extra time for challenge to complete
            await asyncio.sleep(wait_seconds * 2)

        await self._wait_for_network_idle(page)

    # ------------------------------------------------------------------
    # Navigation / warm-up
    # ------------------------------------------------------------------

    async def _navigate_and_interact(self, page: Page, fast_mode: bool = False) -> bool:
        """Navigate to Radio Javan, complete Cloudflare challenge, browse pages."""
        rj = self.config.radiojavan
        timeout_ms = rj.cookie_generation_timeout_seconds * 1000

        # 1. Load homepage (bootstrap URL)
        try:
            await page.goto(
                rj.cookie_bootstrap_url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            logger.info("[RJ_COOKIE_GENERATOR] Radio Javan homepage loaded")
        except Exception as exc:
            logger.error("[RJ_COOKIE_GENERATOR] Failed to load homepage: %s", exc)
            return False

        await self._handle_cloudflare_challenge(page)
        await self._scroll_page(page)

        if fast_mode:
            logger.info("[RJ_COOKIE_GENERATOR] Fast mode enabled - skipping warm-up flow")
            return True

        # 2. Visit 1-2 additional pages to look like a real user
        warmup_pages = random.sample(
            _RADIOJAVAN_WARMUP_PAGES,
            k=min(2, len(_RADIOJAVAN_WARMUP_PAGES)),
        )
        for warmup_url in warmup_pages:
            try:
                await page.goto(
                    warmup_url,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )
                logger.info("[RJ_COOKIE_GENERATOR] Visited warmup page: %s", warmup_url)
            except Exception as exc:
                logger.debug("[RJ_COOKIE_GENERATOR] Warmup page failed (%s): %s", warmup_url, exc)
                continue
            await asyncio.sleep(rj.cookie_wait_after_load_seconds)
            await self._wait_for_network_idle(page)
            await self._scroll_page(page)

        # 3. Validate session by hitting the validation endpoint
        try:
            await page.goto(
                rj.cookie_validation_url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            logger.info("[RJ_COOKIE_GENERATOR] Validation endpoint loaded")
        except Exception as exc:
            logger.warning("[RJ_COOKIE_GENERATOR] Validation page failed: %s", exc)
            # Not fatal — we may still have valid cookies from the homepage visit

        await asyncio.sleep(rj.cookie_wait_after_load_seconds)
        return True

    # ------------------------------------------------------------------
    # Cookie extraction / validation
    # ------------------------------------------------------------------

    def _validate_cookies(self, cookies: Sequence[Mapping[str, Any]]) -> str | None:
        """Return an error message if cookies are insufficient, else None."""
        rj_cookies = [
            c
            for c in cookies
            if any(domain in c.get("domain", "") for domain in ("radiojavan.com", "rj.app"))
        ]
        if not rj_cookies:
            return "No Radio Javan cookies retrieved from browser"

        cookie_names = [c.get("name", "") for c in rj_cookies]
        logger.info("[RJ_COOKIE_GENERATOR] Radio Javan cookies found: %s", cookie_names)

        # cf_clearance is the key Cloudflare bypass cookie
        has_cf_clearance = any(c.get("name") == "cf_clearance" for c in rj_cookies)
        if not has_cf_clearance:
            logger.warning(
                "[RJ_COOKIE_GENERATOR] Missing cf_clearance cookie — "
                "Cloudflare challenge may not have been solved"
            )
            # Not fatal: some requests may still work without it

        return None

    def _save_cookies(self, cookies: Sequence[Mapping[str, Any]]) -> None:
        """Save cookies as a JSON dict suitable for ``requests`` cookies param."""
        rj_cookies: dict[str, str] = {}
        for cookie in cookies:
            domain = cookie.get("domain", "")
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if not name or not domain:
                continue
            if any(d in domain for d in ("radiojavan.com", "rj.app")):
                rj_cookies[name] = value

        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(rj_cookies, f, indent=2)

        if not self.cookie_file.exists() or self.cookie_file.stat().st_size == 0:
            raise OSError(f"Cookie file was not created or is empty: {self.cookie_file}")

        logger.info(
            "[RJ_COOKIE_GENERATOR] Saved %d cookies to %s",
            len(rj_cookies),
            self.cookie_file,
        )

    async def _process_cookies(
        self,
        context: BrowserContext,
        browser: Browser,
        state: CookieState,
    ) -> CookieState:
        """Extract cookies from the browser context, validate, and persist."""
        cookies = await context.cookies()
        logger.info("[RJ_COOKIE_GENERATOR] Retrieved %d total cookies", len(cookies))

        if error_msg := self._validate_cookies(cookies):
            await browser.close()
            return self._create_error_state(error_msg)

        try:
            self._save_cookies(cookies)
        except Exception as exc:
            logger.error("[RJ_COOKIE_GENERATOR] Failed to save cookies: %s", exc)
            await browser.close()
            return self._create_error_state(f"Failed to save cookies: {exc!s}")

        await browser.close()

        rj = self.config.radiojavan
        state.generated_at = datetime.now(timezone.utc)
        state.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=rj.cookie_ttl_hours,
        )
        state.is_valid = True
        state.is_generating = False
        state.cookie_path = str(self.cookie_file)
        state.error_message = None
        self._update_state(state)

        logger.info("[RJ_COOKIE_GENERATOR] Cookie generation successful: %s", self.cookie_file)
        return state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_cookies(self, fast_mode: bool = False) -> CookieState:
        """Generate cookies by visiting Radio Javan in a headless browser.

        Returns:
            CookieState with generation results.
        """
        mode = "fast" if fast_mode else "full"
        logger.info(f"[RJ_COOKIE_GENERATOR] Starting cookie generation (mode={mode})")

        state = CookieState(is_generating=True, is_valid=False)
        self._update_state(state)

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                if (browser := await self._launch_browser(p)) is None:
                    return self._create_error_state("Failed to launch browser")

                if (ctx_result := await self._create_browser_context(browser)) is None:
                    with contextlib.suppress(Exception):
                        await browser.close()
                    return self._create_error_state("Failed to create browser context")

                context, page = ctx_result

                if not await self._navigate_and_interact(page, fast_mode=fast_mode):
                    with contextlib.suppress(Exception):
                        await browser.close()
                    return self._create_error_state("Failed to navigate to Radio Javan")

                return await self._process_cookies(context, browser, state)

        except ImportError as exc:
            error_msg = (
                "Playwright is not installed. Please run: "
                "pip install playwright && playwright install chromium"
            )
            logger.error("[RJ_COOKIE_GENERATOR] %s: %s", error_msg, exc)
            return self._create_error_state(error_msg)

        except Exception as exc:
            error_msg = f"Failed to generate cookies: {exc!s}"
            logger.error("[RJ_COOKIE_GENERATOR] %s", error_msg, exc_info=True)
            return self._create_error_state(error_msg)

    def load_cookies(self) -> dict[str, str] | None:
        """Load previously saved cookies from disk.

        Returns:
            Dict of cookie name→value suitable for ``requests`` cookies kwarg,
            or None if no valid cookie file exists.
        """
        if not self.cookie_file.exists():
            return None
        try:
            with open(self.cookie_file, encoding="utf-8") as f:
                cookies = json.load(f)
            if isinstance(cookies, dict) and cookies:
                return cookies
            return None
        except Exception as exc:
            logger.warning("[RJ_COOKIE_GENERATOR] Failed to load cookies: %s", exc)
            return None

    def validate_cookie_file(self) -> bool:
        """Check whether the on-disk cookie file contains valid data."""
        cookies = self.load_cookies()
        return cookies is not None and len(cookies) > 0

    def cleanup(self) -> None:
        logger.info("[RJ_COOKIE_GENERATOR] Cleanup completed")
