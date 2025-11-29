import asyncio
import contextlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from playwright.async_api import async_playwright

from src.core.config import AppConfig, get_config
from src.core.models import CookieState
from src.utils.logger import get_logger
from src.utils.user_agent_rotator import get_random_user_agent

logger = get_logger(__name__)


class CookieGenerator:
    def __init__(self, storage_dir: Path | None = None, config: AppConfig = get_config()):
        self.config = config
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.storage_dir / self.config.cookies.cookie_file_name
        self._playwright = None
        self._browser = None

        # Thread-safe state management for real-time access
        self._state: CookieState | None = None
        self._state_lock = Lock()

    def get_state(self) -> CookieState | None:
        """Get current cookie generation state (thread-safe).

        Returns:
            Current CookieState or None if not initialized
        """
        with self._state_lock:
            return self._state

    def _update_state(self, state: CookieState) -> None:
        """Update internal state (thread-safe).

        Args:
            state: New state to set
        """
        with self._state_lock:
            self._state = state

    def _create_error_state(self, error_msg: str) -> CookieState:
        """Create an error state with the given message.

        Args:
            error_msg: Error message

        Returns:
            CookieState with error information
        """
        state = CookieState(
            is_generating=False,
            is_valid=False,
            error_message=error_msg,
            _generator=self,
        )
        self._update_state(state)
        return state

    async def _launch_browser(self, playwright: Any) -> Any | None:
        """Launch Chromium browser.

        Args:
            playwright: Playwright instance

        Returns:
            Browser instance or None if launch fails
        """
        try:
            return await playwright.chromium.launch(
                headless=True,
                args=[
                    "--incognito",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
        except Exception as browser_error:
            error_msg = f"Failed to launch browser: {browser_error!s}"
            logger.error(f"[COOKIE_GENERATOR] {error_msg}")
            return None

    async def _create_browser_context(self, browser: Any) -> tuple[Any, Any] | None:
        """Create browser context and page.

        Args:
            browser: Browser instance

        Returns:
            Tuple of (context, page) or None if creation fails
        """
        try:
            user_agent = get_random_user_agent()
            logger.info(f"[COOKIE_GENERATOR] Using random user agent: {user_agent[:50]}...")

            context = await browser.new_context(
                viewport={
                    "width": self.config.cookies.viewport_width,
                    "height": self.config.cookies.viewport_height,
                },
                user_agent=user_agent,
                device_scale_factor=3.0,
                is_mobile=True,
                has_touch=True,
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
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
            logger.info(
                f"[COOKIE_GENERATOR] Created Android mobile context "
                f"(viewport: {self.config.cookies.viewport_width}x{self.config.cookies.viewport_height})"
            )
            return context, page
        except Exception as context_error:
            error_msg = f"Failed to create browser context: {context_error!s}"
            logger.error(f"[COOKIE_GENERATOR] {error_msg}")
            return None

    async def _navigate_and_interact(self, page: Any) -> bool:
        """Navigate to YouTube and perform interactions.

        Args:
            page: Page instance

        Returns:
            True if navigation succeeded, False otherwise
        """
        cookie_config = self.config.cookies

        try:
            await page.goto(
                "https://www.youtube.com",
                wait_until="domcontentloaded",
                timeout=cookie_config.generation_timeout * 1000,
            )
            logger.info("[COOKIE_GENERATOR] YouTube homepage loaded")

            await asyncio.sleep(cookie_config.wait_after_load)

            try:
                await page.wait_for_load_state(
                    "networkidle",
                    timeout=int(cookie_config.wait_for_network_idle * 1000),
                )
            except Exception:
                logger.debug("[COOKIE_GENERATOR] Network idle timeout, continuing")

            await asyncio.sleep(cookie_config.wait_after_load)

            try:
                await page.evaluate("() => window.scrollTo(0, 300)")
                await asyncio.sleep(cookie_config.scroll_delay)
                await page.evaluate("() => window.scrollTo(0, 0)")
                await asyncio.sleep(cookie_config.scroll_delay)
            except Exception:
                logger.debug("[COOKIE_GENERATOR] Scroll interaction failed, continuing")

            test_video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
            logger.info(f"[COOKIE_GENERATOR] Navigating to video page: {test_video_url}")

            try:
                await page.goto(
                    test_video_url,
                    wait_until="domcontentloaded",
                    timeout=cookie_config.generation_timeout * 1000,
                )
                logger.info("[COOKIE_GENERATOR] Video page loaded successfully")

                await asyncio.sleep(cookie_config.wait_after_load * 2)

                try:
                    await page.wait_for_load_state(
                        "networkidle",
                        timeout=int(cookie_config.wait_for_network_idle * 1000),
                    )
                except Exception:
                    logger.debug("[COOKIE_GENERATOR] Video page network idle timeout, continuing")

                await page.evaluate("() => window.scrollTo(0, 200)")
                await asyncio.sleep(cookie_config.scroll_delay)
                await page.evaluate("() => window.scrollTo(0, 0)")
                await asyncio.sleep(cookie_config.scroll_delay)

                logger.info("[COOKIE_GENERATOR] Video page interactions completed")
            except Exception as video_error:
                logger.warning(
                    f"[COOKIE_GENERATOR] Failed to navigate to video page: {video_error}, "
                    "continuing with homepage cookies"
                )

            await asyncio.sleep(cookie_config.wait_after_load)
            return True

        except Exception as e:
            logger.error(f"[COOKIE_GENERATOR] Failed to navigate to YouTube: {e}")
            try:
                await asyncio.sleep(cookie_config.wait_after_load)
                await page.goto(
                    "https://www.youtube.com",
                    wait_until="domcontentloaded",
                    timeout=cookie_config.generation_timeout * 1000,
                )
                await asyncio.sleep(cookie_config.wait_after_load)
                logger.info("[COOKIE_GENERATOR] YouTube loaded successfully on retry")
                return True
            except Exception as retry_e:
                logger.error(f"[COOKIE_GENERATOR] Retry also failed: {retry_e}")
                return False

    def _validate_cookies(
        self, cookies: list, youtube_cookies: list, google_cookies: list
    ) -> str | None:
        """Validate retrieved cookies.

        Args:
            cookies: All cookies
            youtube_cookies: YouTube domain cookies
            google_cookies: Google domain cookies

        Returns:
            Error message if validation fails, None otherwise
        """
        if not cookies or (not youtube_cookies and not google_cookies):
            logger.warning("[COOKIE_GENERATOR] No valid cookies retrieved")
            return "No valid cookies retrieved from browser"

        important_cookies = [
            "VISITOR_INFO1_LIVE",
            "YSC",
            "PREF",
            "__Secure-YSC",
            "__Secure-3PSID",
            "__Secure-3PAPISID",
        ]
        found_important = [
            c.get("name") for c in youtube_cookies if c.get("name") in important_cookies
        ]
        logger.info(f"[COOKIE_GENERATOR] Important cookies found: {found_important}")

        has_visitor_info = any(c.get("name") == "VISITOR_INFO1_LIVE" for c in youtube_cookies)
        has_ysc = any(c.get("name") == "YSC" for c in youtube_cookies)

        if not has_visitor_info and not has_ysc:
            logger.warning(
                "[COOKIE_GENERATOR] Missing critical cookies (VISITOR_INFO1_LIVE or YSC)"
            )

        return None

    async def _process_cookies(self, context: Any, browser: Any, state: CookieState) -> CookieState:
        """Process and save cookies from browser context.

        Args:
            context: Browser context
            browser: Browser instance
            state: Current state

        Returns:
            Updated state (success or error)
        """
        cookies = await context.cookies()
        youtube_cookies = [c for c in cookies if "youtube.com" in c.get("domain", "")]
        google_cookies = [c for c in cookies if "google.com" in c.get("domain", "")]
        logger.info(
            f"[COOKIE_GENERATOR] Retrieved {len(cookies)} total cookies ({len(youtube_cookies)} YouTube, {len(google_cookies)} Google)"
        )

        error_msg = self._validate_cookies(cookies, youtube_cookies, google_cookies)
        if error_msg:
            await browser.close()
            return self._create_error_state(error_msg)

        try:
            self._save_cookies(cookies)
        except Exception as save_error:
            logger.error(f"[COOKIE_GENERATOR] Failed to save cookies: {save_error}")
            await browser.close()
            return self._create_error_state(f"Failed to save cookies: {save_error!s}")

        netscape_path = self.convert_to_netscape_text()
        if not netscape_path:
            logger.warning("[COOKIE_GENERATOR] Failed to convert cookies to Netscape format")
            return self._create_error_state("Failed to convert cookies to Netscape format")

        await browser.close()

        state.generated_at = datetime.now()
        state.expires_at = datetime.now() + timedelta(hours=self.config.cookies.cookie_expiry_hours)
        state.is_valid = True
        state.is_generating = False
        state.cookie_path = netscape_path
        state.error_message = None
        self._update_state(state)

        logger.info(
            f"[COOKIE_GENERATOR] Cookie generation successful: {state.cookie_path} "
            f"(JSON: {self.cookie_file})"
        )

        return state

    async def generate_cookies(self) -> CookieState:
        """Generate cookies by visiting YouTube in headless browser.

        Returns:
            CookieState with generation results
        """
        logger.info("[COOKIE_GENERATOR] Starting cookie generation")

        state = CookieState(
            is_generating=True,
            is_valid=False,
            _generator=self,
        )
        self._update_state(state)

        try:
            async with async_playwright() as p:
                logger.info("[COOKIE_GENERATOR] Launching Chromium browser")

                browser = await self._launch_browser(p)
                if browser is None:
                    return self._create_error_state("Failed to launch browser")

                context_result = await self._create_browser_context(browser)
                if context_result is None:
                    with contextlib.suppress(Exception):
                        await browser.close()
                    return self._create_error_state("Failed to create browser context")

                context, page = context_result
                logger.info("[COOKIE_GENERATOR] Navigating to YouTube")

                if not await self._navigate_and_interact(page):
                    with contextlib.suppress(Exception):
                        await browser.close()
                    return self._create_error_state("Failed to navigate to YouTube")

                return await self._process_cookies(context, browser, state)

        except ImportError as e:
            error_msg = (
                "Playwright is not installed. Please run: "
                "pip install playwright && playwright install chromium"
            )
            logger.error(f"[COOKIE_GENERATOR] {error_msg}: {e}")
            return self._create_error_state(error_msg)

        except Exception as e:
            error_msg = f"Failed to generate cookies: {e!s}"
            logger.error(f"[COOKIE_GENERATOR] {error_msg}", exc_info=True)
            return self._create_error_state(error_msg)

    def _save_cookies(self, cookies: list) -> None:
        """Save cookies to JSON file in Netscape format.

        Args:
            cookies: List of cookie dicts from Playwright
        """
        netscape_cookies = []
        valid_count = 0
        skipped_count = 0

        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            domain = cookie.get("domain", "")

            if not name or not domain:
                skipped_count += 1
                continue

            expires = cookie.get("expires", -1)
            if expires == -1 or expires is None:
                expires = 0
            elif expires > 0:
                expires = int(expires)
                expires = max(expires, 0)
            else:
                expires = 0

            netscape_cookie = {
                "domain": domain,
                "flag": "TRUE" if domain.startswith(".") else "FALSE",
                "path": cookie.get("path", "/"),
                "secure": "TRUE" if cookie.get("secure", False) else "FALSE",
                "expiration": expires,
                "name": name,
                "value": value,
            }
            netscape_cookies.append(netscape_cookie)
            valid_count += 1

        if skipped_count > 0:
            logger.warning(f"[COOKIE_GENERATOR] Skipped {skipped_count} invalid cookies")

        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(netscape_cookies, f, indent=2)

        # Verify file was written
        if not self.cookie_file.exists():
            raise OSError(f"Cookie file was not created: {self.cookie_file}")

        file_size = self.cookie_file.stat().st_size
        if file_size == 0:
            raise OSError(f"Cookie file is empty: {self.cookie_file}")

        logger.info(
            f"[COOKIE_GENERATOR] Saved {valid_count} valid cookies to {self.cookie_file} (size: {file_size} bytes)"
        )

    def convert_to_netscape_text(self) -> str | None:
        """Convert JSON cookies to Netscape text format for yt-dlp.

        Returns:
            Path to Netscape format cookie file, or None if conversion fails
        """
        if not self.cookie_file.exists():
            logger.warning("[COOKIE_GENERATOR] No cookie file found to convert")
            return None

        try:
            with open(self.cookie_file, encoding="utf-8") as f:
                cookies = json.load(f)

            netscape_file = self.storage_dir / self.config.cookies.netscape_file_name
            valid_cookies = 0
            skipped_cookies = 0

            with open(netscape_file, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file was generated by Cookie Generator\n")
                f.write("# Edit at your own risk.\n\n")

                for cookie in cookies:
                    domain = cookie.get("domain", "")
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")

                    if not domain or not name:
                        skipped_cookies += 1
                        continue

                    flag = cookie.get("flag", "FALSE")
                    path = cookie.get("path", "/")
                    secure = cookie.get("secure", "FALSE")
                    expiration = cookie.get("expiration", -1)

                    if expiration == -1 or expiration is None or expiration < 0:
                        expiration = 0
                    else:
                        expiration = int(expiration)

                    if expiration >= 0 and domain and name:
                        f.write(
                            f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
                        )
                        valid_cookies += 1

            if skipped_cookies > 0:
                logger.warning(
                    f"[COOKIE_GENERATOR] Skipped {skipped_cookies} invalid cookies during conversion"
                )

            if valid_cookies == 0:
                logger.error("[COOKIE_GENERATOR] No valid cookies to write to Netscape format")
                return None

            # Verify file was written successfully
            if not netscape_file.exists():
                logger.error(f"[COOKIE_GENERATOR] Netscape file was not created: {netscape_file}")
                return None

            # Verify file has content
            file_size = netscape_file.stat().st_size
            if file_size == 0:
                logger.error(f"[COOKIE_GENERATOR] Netscape file is empty: {netscape_file}")
                return None

            logger.info(
                f"[COOKIE_GENERATOR] Converted {valid_cookies} cookies to Netscape format: {netscape_file} (size: {file_size} bytes)"
            )
            return str(netscape_file)

        except Exception as e:
            logger.error(f"[COOKIE_GENERATOR] Failed to convert cookies: {e}", exc_info=True)
            return None

    def validate_netscape_file(self, file_path: str) -> bool:
        """Validate that a Netscape cookie file is valid and contains valid cookies.

        Args:
            file_path: Path to Netscape format cookie file

        Returns:
            True if file is valid, False otherwise
        """
        try:
            if not Path(file_path).exists():
                return False

            valid_lines = 0
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    stripped_line = line.strip()
                    if not stripped_line or stripped_line.startswith("#"):
                        continue

                    parts = stripped_line.split("\t")
                    if len(parts) < 7:
                        continue

                    expiration = parts[4]
                    try:
                        exp_int = int(expiration)
                        if exp_int >= 0:
                            valid_lines += 1
                    except ValueError:
                        continue

            return valid_lines > 0

        except Exception as e:
            logger.error(f"[COOKIE_GENERATOR] Error validating cookie file: {e}", exc_info=True)
            return False

    async def ensure_chromium_installed(self) -> bool:
        """Ensure Chromium browser is installed for Playwright.

        Returns:
            True if Chromium is installed, False otherwise
        """
        try:
            async with async_playwright() as p:
                browser_type = p.chromium
                if browser_type:
                    logger.info("[COOKIE_GENERATOR] Chromium is available")
                    return True

            return False

        except Exception as e:
            logger.error(f"[COOKIE_GENERATOR] Failed to check Chromium: {e}", exc_info=True)
            return False

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("[COOKIE_GENERATOR] Cleanup completed")
