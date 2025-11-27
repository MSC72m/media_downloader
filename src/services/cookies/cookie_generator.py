"""Cookie generator service using Playwright for automatic cookie generation."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.core.models import CookieState
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CookieGenerator:
    """Generates YouTube cookies using Playwright headless browser."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize cookie generator.

        Args:
            storage_dir: Directory to store cookies (default: ~/.media_downloader)
        """
        self.storage_dir = storage_dir or Path.home() / ".media_downloader"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.storage_dir / "cookies.json"
        self._playwright = None
        self._browser = None

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

        try:
            # Import playwright
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                logger.info("[COOKIE_GENERATOR] Launching Chromium browser")

                # Launch browser in headless mode
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--incognito",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )

                # Create incognito context
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                # Create page and visit YouTube
                page = await context.new_page()
                logger.info("[COOKIE_GENERATOR] Navigating to YouTube")

                try:
                    await page.goto("https://www.youtube.com", wait_until="networkidle", timeout=30000)
                    logger.info("[COOKIE_GENERATOR] YouTube loaded successfully")
                except Exception as e:
                    logger.error(f"[COOKIE_GENERATOR] Failed to navigate to YouTube: {e}")
                    # Retry once more time
                    try:
                        await asyncio.sleep(2)
                        await page.goto("https://www.youtube.com", wait_until="networkidle", timeout=30000)
                        logger.info("[COOKIE_GENERATOR] YouTube loaded successfully on retry")
                    except Exception as retry_e:
                        logger.error(f"[COOKIE_GENERATOR] Retry also failed: {retry_e}")
                        raise retry_e

                # Wait a bit for any dynamic content
                await asyncio.sleep(2)

                # Get cookies
                cookies = await context.cookies()
                logger.info(f"[COOKIE_GENERATOR] Retrieved {len(cookies)} cookies")

                # Save cookies to file
                self._save_cookies(cookies)

                # Close browser
                await browser.close()

                # Update state
                state.generated_at = datetime.now()
                state.expires_at = datetime.now() + timedelta(hours=8)
                state.is_valid = True
                state.is_generating = False
                state.cookie_path = str(self.cookie_file)
                state.error_message = None

                logger.info(
                    f"[COOKIE_GENERATOR] Cookie generation successful: {state.cookie_path}"
                )

                return state

        except ImportError as e:
            error_msg = (
                "Playwright is not installed. Please run: "
                "pip install playwright && playwright install chromium"
            )
            logger.error(f"[COOKIE_GENERATOR] {error_msg}: {e}")
            state.is_generating = False
            state.is_valid = False
            state.error_message = error_msg
            return state

        except Exception as e:
            error_msg = f"Failed to generate cookies: {str(e)}"
            logger.error(f"[COOKIE_GENERATOR] {error_msg}", exc_info=True)
            state.is_generating = False
            state.is_valid = False
            state.error_message = error_msg
            return state

    def _save_cookies(self, cookies: list) -> None:
        """Save cookies to JSON file in Netscape format.

        Args:
            cookies: List of cookie dicts from Playwright
        """
        # Convert Playwright cookies to Netscape format
        netscape_cookies = []

        for cookie in cookies:
            # Netscape format: domain, flag, path, secure, expiration, name, value
            netscape_cookie = {
                "domain": cookie.get("domain", ""),
                "flag": "TRUE" if cookie.get("domain", "").startswith(".") else "FALSE",
                "path": cookie.get("path", "/"),
                "secure": "TRUE" if cookie.get("secure", False) else "FALSE",
                "expiration": int(cookie.get("expires", -1)),
                "name": cookie.get("name", ""),
                "value": cookie.get("value", ""),
            }
            netscape_cookies.append(netscape_cookie)

        # Save to JSON
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(netscape_cookies, f, indent=2)

        logger.info(
            f"[COOKIE_GENERATOR] Saved {len(netscape_cookies)} cookies to {self.cookie_file}"
        )

    def convert_to_netscape_text(self) -> Optional[str]:
        """Convert JSON cookies to Netscape text format for yt-dlp.

        Returns:
            Path to Netscape format cookie file, or None if conversion fails
        """
        if not self.cookie_file.exists():
            logger.warning("[COOKIE_GENERATOR] No cookie file found to convert")
            return None

        try:
            # Load JSON cookies
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # Create Netscape format file
            netscape_file = self.storage_dir / "cookies.txt"

            with open(netscape_file, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file was generated by Cookie Generator\n")
                f.write("# Edit at your own risk.\n\n")

                for cookie in cookies:
                    domain = cookie.get("domain", "")
                    flag = cookie.get("flag", "FALSE")
                    path = cookie.get("path", "/")
                    secure = cookie.get("secure", "FALSE")
                    expiration = cookie.get("expiration", -1)
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")

                    # Write in Netscape format
                    f.write(
                        f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
                    )

            logger.info(
                f"[COOKIE_GENERATOR] Converted cookies to Netscape format: {netscape_file}"
            )
            return str(netscape_file)

        except Exception as e:
            logger.error(
                f"[COOKIE_GENERATOR] Failed to convert cookies: {e}", exc_info=True
            )
            return None

    async def ensure_chromium_installed(self) -> bool:
        """Ensure Chromium browser is installed for Playwright.

        Returns:
            True if Chromium is installed, False otherwise
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Try to get browser
                browser_type = p.chromium
                if browser_type:
                    logger.info("[COOKIE_GENERATOR] Chromium is available")
                    return True

            return False

        except Exception as e:
            logger.error(f"[COOKIE_GENERATOR] Failed to check Chromium: {e}")
            return False

    def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("[COOKIE_GENERATOR] Cleanup completed")
