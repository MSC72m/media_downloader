"""Cookie generator service using Playwright for automatic cookie generation."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.core.config import get_config, AppConfig
from src.core.models import CookieState
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CookieGenerator:
    """Generates YouTube cookies using Playwright headless browser."""

    def __init__(self, storage_dir: Optional[Path] = None, config: AppConfig = get_config()):
        """Initialize cookie generator.

        Args:
            storage_dir: Directory to store cookies (uses config if not provided)
            config: AppConfig instance (defaults to get_config() if None)
        """
        self.config = config
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.storage_dir / self.config.cookies.cookie_file_name
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
                    viewport={"width": self.config.cookies.viewport_width, "height": self.config.cookies.viewport_height},
                    user_agent=self.config.network.cookie_user_agent,
                )

                page = await context.new_page()
                logger.info("[COOKIE_GENERATOR] Navigating to YouTube")

                cookie_config = self.config.cookies

                try:
                    await page.goto(
                        "https://www.youtube.com",
                        wait_until="domcontentloaded",
                        timeout=cookie_config.generation_timeout * 1000
                    )
                    logger.info("[COOKIE_GENERATOR] YouTube loaded successfully")

                    await asyncio.sleep(cookie_config.wait_after_load)

                    try:
                        await page.wait_for_load_state(
                            "networkidle",
                            timeout=int(cookie_config.wait_for_network_idle * 1000)
                        )
                    except Exception:
                        logger.debug("[COOKIE_GENERATOR] Network idle timeout, continuing")

                    await asyncio.sleep(cookie_config.wait_after_load)

                    try:
                        await page.evaluate("() => window.scrollTo(0, 100)")
                        await asyncio.sleep(cookie_config.scroll_delay)
                    except Exception:
                        logger.debug("[COOKIE_GENERATOR] Scroll interaction failed, continuing")

                except Exception as e:
                    logger.error(f"[COOKIE_GENERATOR] Failed to navigate to YouTube: {e}")
                    try:
                        await asyncio.sleep(cookie_config.wait_after_load)
                        await page.goto(
                            "https://www.youtube.com",
                            wait_until="domcontentloaded",
                            timeout=cookie_config.generation_timeout * 1000
                        )
                        await asyncio.sleep(cookie_config.wait_after_load)
                        logger.info("[COOKIE_GENERATOR] YouTube loaded successfully on retry")
                    except Exception as retry_e:
                        logger.error(f"[COOKIE_GENERATOR] Retry also failed: {retry_e}")
                        raise retry_e

                cookies = await context.cookies()
                youtube_cookies = [c for c in cookies if "youtube.com" in c.get("domain", "")]
                google_cookies = [c for c in cookies if "google.com" in c.get("domain", "")]
                logger.info(f"[COOKIE_GENERATOR] Retrieved {len(cookies)} total cookies ({len(youtube_cookies)} YouTube, {len(google_cookies)} Google)")

                # Save cookies to file
                self._save_cookies(cookies)

                # Close browser
                await browser.close()

                # Update state
                state.generated_at = datetime.now()
                state.expires_at = datetime.now() + timedelta(hours=self.config.cookies.cookie_expiry_hours)
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
        from datetime import datetime

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
                if expires < 0:
                    expires = 0
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

        logger.info(f"[COOKIE_GENERATOR] Saved {valid_count} valid cookies to {self.cookie_file}")

    def convert_to_netscape_text(self) -> Optional[str]:
        """Convert JSON cookies to Netscape text format for yt-dlp.

        Returns:
            Path to Netscape format cookie file, or None if conversion fails
        """
        if not self.cookie_file.exists():
            logger.warning("[COOKIE_GENERATOR] No cookie file found to convert")
            return None

        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
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

                    if expiration == -1 or expiration is None:
                        expiration = 0
                    elif expiration < 0:
                        expiration = 0
                    else:
                        expiration = int(expiration)

                    if expiration >= 0 and domain and name:
                        f.write(
                            f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
                        )
                        valid_cookies += 1
                    else:
                        skipped_cookies += 1
                        logger.debug(f"[COOKIE_GENERATOR] Skipping invalid cookie: {name}")

            if skipped_cookies > 0:
                logger.warning(f"[COOKIE_GENERATOR] Skipped {skipped_cookies} invalid cookies during conversion")

            if valid_cookies == 0:
                logger.error("[COOKIE_GENERATOR] No valid cookies to write")
                return None

            logger.info(f"[COOKIE_GENERATOR] Converted {valid_cookies} cookies to Netscape format: {netscape_file}")
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
            from pathlib import Path

            if not Path(file_path).exists():
                return False

            valid_lines = 0
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split("\t")
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
            from playwright.async_api import async_playwright

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
