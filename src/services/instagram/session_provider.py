from __future__ import annotations

import http.cookiejar
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

if TYPE_CHECKING:
    import instaloader

logger = get_logger(__name__)

_SESSION_PREFIX = "session-"
_INSTAGRAM_COOKIE_DOMAIN = "instagram.com"
_INSTAGRAM_SESSION_COOKIE = "sessionid"


class InstagramSessionProvider:
    """Establish an authenticated Instaloader session without a password.

    Instagram blocks scripted username/password logins (HTTP 401 / checkpoint),
    so this provider reuses an *existing* logged-in session instead of trying to
    log in with credentials:

    1. A saved Instaloader session file in the config dir. These are persisted
       automatically after a successful browser import and can also be dropped
       in manually (e.g. ``instaloader --login=USERNAME``).
    2. Cookies imported from the user's already-logged-in browser. Browser
       discovery reuses the same cookie subsystem that powers YouTube auth
       (:meth:`YouTubeCookieSourceCoordinator.get_browser_candidates`), so no
       parallel browser-detection logic is introduced (DRY).

    No credentials are ever collected, requested, or stored.
    """

    def __init__(self, config: AppConfig = get_config()) -> None:
        self.config = config
        # Store alongside the other per-site cookie data (SiteCookieManager
        # subclasses use the same storage_dir root).
        self.session_dir = self.config.cookies.storage_dir / "instagram"

    def load_session(self, loader: instaloader.Instaloader) -> str | None:
        """Attach an authenticated session to ``loader``.

        Tries a saved session file first, then falls back to importing cookies
        from the user's browser (persisting a session file for next time).

        Args:
            loader: The Instaloader instance to authenticate.

        Returns:
            The resolved Instagram username on success, or ``None`` when no
            session/cookies are available. ``None`` is not an error: anonymous
            (public) access still works for many posts.
        """
        if username := self._load_saved_session(loader):
            logger.info("[INSTAGRAM_SESSION] Loaded saved session for %s***", username[:3])
            return username

        if username := self._import_from_browser(loader):
            logger.info("[INSTAGRAM_SESSION] Imported browser cookies for %s***", username[:3])
            self._persist_session(loader, username)
            return username

        logger.info(
            "[INSTAGRAM_SESSION] No saved session or browser cookies found; "
            "continuing with anonymous access"
        )
        return None

    def _saved_session_files(self) -> list[Path]:
        """Return saved Instaloader session files, if any."""
        if not self.session_dir.is_dir():
            return []
        return sorted(p for p in self.session_dir.glob(f"{_SESSION_PREFIX}*") if p.is_file())

    def _load_saved_session(self, loader: instaloader.Instaloader) -> str | None:
        """Load the first valid saved Instaloader session file."""
        for session_file in self._saved_session_files():
            username = session_file.name[len(_SESSION_PREFIX) :]
            if not username:
                continue
            try:
                loader.load_session_from_file(username, str(session_file))
                if verified := loader.test_login():
                    loader.context.username = verified
                    return verified
                logger.info(
                    "[INSTAGRAM_SESSION] Saved session for %s*** is no longer valid",
                    username[:3],
                )
            except Exception as exc:
                logger.info("[INSTAGRAM_SESSION] Failed to load saved session: %s", exc)
        return None

    def _import_from_browser(self, loader: instaloader.Instaloader) -> str | None:
        """Import Instagram cookies from an installed, logged-in browser."""
        for candidate in self._browser_candidates():
            if (jar := self._extract_instagram_cookies(candidate)) is None:
                continue
            try:
                loader.context._session.cookies.update(jar)
                if username := loader.test_login():
                    loader.context.username = username
                    return username
            except Exception as exc:
                logger.info(
                    "[INSTAGRAM_SESSION] Cookie import from %s failed: %s",
                    getattr(candidate, "name", "?"),
                    exc,
                )
        return None

    def _browser_candidates(self) -> list:
        """Reuse the YouTube cookie subsystem's browser discovery (DRY)."""
        try:
            from src.services.cookies.youtube_cookie_sources import (
                YouTubeCookieSourceCoordinator,
            )

            coordinator = YouTubeCookieSourceCoordinator(config=self.config)
            return coordinator.get_browser_candidates()
        except Exception as exc:
            logger.info("[INSTAGRAM_SESSION] Browser discovery unavailable: %s", exc)
            return []

    def _extract_instagram_cookies(self, candidate: object) -> http.cookiejar.CookieJar | None:
        """Extract Instagram cookies for one browser candidate.

        Returns a cookie jar containing the Instagram cookies (only when a
        ``sessionid`` is present, i.e. the browser is actually logged in), or
        ``None`` when extraction is unavailable or the browser is not logged in.
        """
        browser = getattr(candidate, "ytdlp_browser", None)
        if not browser:
            return None
        profile = getattr(candidate, "profile_path", None)

        try:
            from yt_dlp.cookies import extract_cookies_from_browser
        except Exception as exc:
            logger.info("[INSTAGRAM_SESSION] Browser cookie extraction unavailable: %s", exc)
            return None

        try:
            source_jar = extract_cookies_from_browser(browser, profile=profile)
        except Exception as exc:
            logger.info("[INSTAGRAM_SESSION] Failed to read cookies from %s: %s", browser, exc)
            return None

        jar = http.cookiejar.CookieJar()
        has_session = False
        for cookie in source_jar:
            if _INSTAGRAM_COOKIE_DOMAIN not in (cookie.domain or ""):
                continue
            jar.set_cookie(cookie)
            if cookie.name == _INSTAGRAM_SESSION_COOKIE:
                has_session = True

        if not has_session:
            logger.info("[INSTAGRAM_SESSION] %s has no logged-in Instagram session cookie", browser)
            return None
        return jar

    def _persist_session(self, loader: instaloader.Instaloader, username: str) -> None:
        """Save the authenticated session so future runs skip browser import."""
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            session_file = self.session_dir / f"{_SESSION_PREFIX}{username}"
            loader.save_session_to_file(str(session_file))
            logger.info("[INSTAGRAM_SESSION] Persisted session for %s***", username[:3])
        except Exception as exc:
            logger.info("[INSTAGRAM_SESSION] Could not persist session: %s", exc)
