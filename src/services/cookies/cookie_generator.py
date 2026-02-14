import asyncio
import contextlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from urllib.parse import quote_plus

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from src.core.config import AppConfig, get_config
from src.core.models import CookieState
from src.utils.logger import get_logger
from src.utils.user_agent_rotator import get_random_user_agent

logger = get_logger(__name__)

_YOUTUBE_WARMUP_SEARCH_TOPICS = [
    "coding tutorial",
    "lofi music",
    "travel vlog",
    "productivity tips",
    "python async",
    "science documentary",
]
_YOUTUBE_WARMUP_FALLBACK_VIDEOS = [
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
]


class CookieGenerator:
    def __init__(self, storage_dir: Path | None = None, config: AppConfig = get_config()) -> None:
        self.config = config
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.storage_dir / self.config.cookies.cookie_file_name
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

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
        )
        self._update_state(state)
        return state

    async def _launch_browser(self, playwright: Playwright) -> Browser | None:
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

    async def _create_browser_context(self, browser: Browser) -> tuple[BrowserContext, Page] | None:
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

    async def _wait_for_network_idle(self, page: Page) -> None:
        """Best-effort wait for network idle."""
        try:
            await page.wait_for_load_state(
                "networkidle",
                timeout=int(self.config.cookies.wait_for_network_idle * 1000),
            )
        except Exception:
            logger.debug("[COOKIE_GENERATOR] Network idle timeout, continuing")

    async def _scroll_page(self, page: Page) -> None:
        """Best-effort scroll interactions to emulate user activity."""
        try:
            await page.evaluate("() => window.scrollTo(0, 350)")
            await asyncio.sleep(self.config.cookies.scroll_delay)
            await page.evaluate("() => window.scrollTo(0, 900)")
            await asyncio.sleep(self.config.cookies.scroll_delay)
            await page.evaluate("() => window.scrollTo(0, 0)")
            await asyncio.sleep(self.config.cookies.scroll_delay)
        except Exception:
            logger.debug("[COOKIE_GENERATOR] Scroll interaction failed, continuing")

    async def _accept_consent_if_present(self, page: Page) -> None:
        """Attempt to accept YouTube/Google consent dialogs when visible."""
        selectors = [
            "button:has-text('Accept all')",
            "button:has-text('I agree')",
            "button:has-text('Reject all')",
            "form button",
        ]
        for selector in selectors:
            with contextlib.suppress(Exception):
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click(timeout=1500)
                    await asyncio.sleep(self.config.cookies.wait_after_load)
                    logger.info("[COOKIE_GENERATOR] Consent dialog handled")
                    return

    async def _collect_search_video_urls(self, page: Page, limit: int = 6) -> list[str]:
        """Collect up to `limit` watch URLs from a YouTube search page."""
        try:
            hrefs = await page.eval_on_selector_all(
                "a#video-title",
                f"""(els) => els
                    .slice(0, {limit * 2})
                    .map((e) => e.getAttribute('href'))
                    .filter((href) => typeof href === 'string' && href.startsWith('/watch'))""",
            )
        except Exception:
            return []

        urls: list[str] = []
        for href in hrefs:
            if not isinstance(href, str):
                continue
            if (full_url := f"https://www.youtube.com{href}") not in urls:
                urls.append(full_url)
            if len(urls) >= limit:
                break
        return urls

    async def _watch_video_page(self, page: Page, video_url: str) -> bool:
        """Open a video page and simulate short viewing behavior."""
        cookie_config = self.config.cookies
        try:
            await page.goto(
                video_url,
                wait_until="domcontentloaded",
                timeout=cookie_config.generation_timeout * 1000,
            )
        except Exception as video_error:
            logger.warning(
                f"[COOKIE_GENERATOR] Failed to load video page {video_url}: {video_error}"
            )
            return False

        logger.info(f"[COOKIE_GENERATOR] Watching video page: {video_url}")
        await asyncio.sleep(cookie_config.wait_after_load * 1.5)
        await self._wait_for_network_idle(page)
        await self._scroll_page(page)

        watch_seconds = random.uniform(4.0, 8.0)
        await asyncio.sleep(watch_seconds)
        return True

    async def _navigate_and_interact(self, page: Page) -> bool:
        """Navigate to YouTube, warm up session state, then persist cookies."""
        cookie_config = self.config.cookies

        try:
            await page.goto(
                "https://www.youtube.com",
                wait_until="domcontentloaded",
                timeout=cookie_config.generation_timeout * 1000,
            )
            logger.info("[COOKIE_GENERATOR] YouTube homepage loaded")

            await asyncio.sleep(cookie_config.wait_after_load)
            await self._wait_for_network_idle(page)
            await self._accept_consent_if_present(page)
            await self._scroll_page(page)

            topics = random.sample(
                _YOUTUBE_WARMUP_SEARCH_TOPICS,
                k=min(3, len(_YOUTUBE_WARMUP_SEARCH_TOPICS)),
            )
            discovered_videos: list[str] = []

            for topic in topics:
                search_url = (
                    "https://www.youtube.com/results?"
                    f"search_query={quote_plus(topic)}&sp=EgIQAQ%253D%253D"
                )
                logger.info(f"[COOKIE_GENERATOR] Performing warm-up search: {topic}")
                try:
                    await page.goto(
                        search_url,
                        wait_until="domcontentloaded",
                        timeout=cookie_config.generation_timeout * 1000,
                    )
                except Exception as search_error:
                    logger.debug(
                        f"[COOKIE_GENERATOR] Search navigation failed for '{topic}': {search_error}"
                    )
                    continue

                await asyncio.sleep(cookie_config.wait_after_load)
                await self._wait_for_network_idle(page)
                await self._scroll_page(page)
                for video_url in await self._collect_search_video_urls(page):
                    if video_url not in discovered_videos:
                        discovered_videos.append(video_url)

            watched_count = 0
            candidate_videos = discovered_videos[:3] + _YOUTUBE_WARMUP_FALLBACK_VIDEOS
            for video_url in candidate_videos:
                if watched_count >= 3:
                    break
                if not await self._watch_video_page(page, video_url):
                    continue
                watched_count += 1

            logger.info(f"[COOKIE_GENERATOR] Warm-up complete. Videos watched: {watched_count}")
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

    async def _process_cookies(
        self, context: BrowserContext, browser: Browser, state: CookieState
    ) -> CookieState:
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

        if error_msg := self._validate_cookies(cookies, youtube_cookies, google_cookies):
            await browser.close()
            return self._create_error_state(error_msg)

        try:
            self._save_cookies(cookies)
        except Exception as save_error:
            logger.error(f"[COOKIE_GENERATOR] Failed to save cookies: {save_error}")
            await browser.close()
            return self._create_error_state(f"Failed to save cookies: {save_error!s}")

        if not (netscape_path := self.convert_to_netscape_text()):
            logger.warning("[COOKIE_GENERATOR] Failed to convert cookies to Netscape format")
            return self._create_error_state("Failed to convert cookies to Netscape format")

        await browser.close()

        state.generated_at = datetime.now(timezone.utc)
        state.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=self.config.cookies.cookie_expiry_hours
        )
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
        )
        self._update_state(state)

        try:
            async with async_playwright() as p:
                logger.info("[COOKIE_GENERATOR] Launching Chromium browser")

                if (browser := await self._launch_browser(p)) is None:
                    return self._create_error_state("Failed to launch browser")

                if (context_result := await self._create_browser_context(browser)) is None:
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

            if (expires := cookie.get("expires", -1)) == -1 or expires is None:
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

        if (file_size := self.cookie_file.stat().st_size) == 0:
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
            if (file_size := netscape_file.stat().st_size) == 0:
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
                        if int(expiration) >= 0:
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
                if p.chromium:
                    logger.info("[COOKIE_GENERATOR] Chromium is available")
                    return True

            return False

        except Exception as e:
            logger.error(f"[COOKIE_GENERATOR] Failed to check Chromium: {e}", exc_info=True)
            return False

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("[COOKIE_GENERATOR] Cleanup completed")
