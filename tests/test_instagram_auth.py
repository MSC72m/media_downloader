"""Tests for the session/cookie-based Instagram authentication path.

Instagram blocks scripted username/password logins, so auth now works by
loading a saved Instaloader session or importing cookies from the user's
logged-in browser (reusing the shared browser-cookie subsystem).
"""

import http.cookiejar
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.config import AppConfig, CookieConfig
from src.services.instagram.downloader import (
    INSTAGRAM_AUTH_REQUIRED_MESSAGE,
    InstagramDownloader,
)
from src.services.instagram.session_provider import InstagramSessionProvider


def _config(tmp_path) -> AppConfig:
    return AppConfig(cookies=CookieConfig(storage_dir=tmp_path))


def _cookie(name: str, domain: str) -> http.cookiejar.Cookie:
    return http.cookiejar.Cookie(
        version=0,
        name=name,
        value="value",
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


# ---------------------------------------------------------------------------
# InstagramSessionProvider
# ---------------------------------------------------------------------------


def test_session_dir_lives_under_cookie_storage(tmp_path):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    assert provider.session_dir == tmp_path / "instagram"


def test_load_session_returns_none_when_nothing_available(tmp_path, monkeypatch):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    monkeypatch.setattr(provider, "_import_from_browser", lambda _loader: None)

    assert provider.load_session(MagicMock()) is None


def test_load_saved_session_success(tmp_path):
    session_dir = tmp_path / "instagram"
    session_dir.mkdir(parents=True)
    (session_dir / "session-alice").write_text("session-bytes")

    provider = InstagramSessionProvider(config=_config(tmp_path))
    loader = MagicMock()
    loader.test_login.return_value = "alice"

    assert provider.load_session(loader) == "alice"
    loader.load_session_from_file.assert_called_once()
    assert loader.context.username == "alice"


def test_load_saved_session_skips_invalid_session(tmp_path, monkeypatch):
    session_dir = tmp_path / "instagram"
    session_dir.mkdir(parents=True)
    (session_dir / "session-stale").write_text("stale")

    provider = InstagramSessionProvider(config=_config(tmp_path))
    loader = MagicMock()
    loader.test_login.return_value = None  # saved session no longer valid
    monkeypatch.setattr(provider, "_import_from_browser", lambda _loader: None)

    assert provider.load_session(loader) is None


def test_load_session_prefers_saved_over_browser(tmp_path, monkeypatch):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    monkeypatch.setattr(provider, "_load_saved_session", lambda _loader: "bob")
    browser = MagicMock()
    monkeypatch.setattr(provider, "_import_from_browser", browser)

    assert provider.load_session(MagicMock()) == "bob"
    browser.assert_not_called()


def test_import_from_browser_success_persists_session(tmp_path, monkeypatch):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    candidate = SimpleNamespace(name="chrome", ytdlp_browser="chrome", profile_path=None)
    monkeypatch.setattr(provider, "_browser_candidates", lambda: [candidate])
    monkeypatch.setattr(
        provider, "_extract_instagram_cookies", lambda _c: http.cookiejar.CookieJar()
    )

    loader = MagicMock()
    loader.test_login.return_value = "carol"

    assert provider.load_session(loader) == "carol"
    assert loader.context.username == "carol"
    loader.save_session_to_file.assert_called_once()
    assert (tmp_path / "instagram" / "session-carol").parent.exists()


def test_import_from_browser_returns_none_without_cookies(tmp_path, monkeypatch):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    candidate = SimpleNamespace(name="chrome", ytdlp_browser="chrome", profile_path=None)
    monkeypatch.setattr(provider, "_browser_candidates", lambda: [candidate])
    monkeypatch.setattr(provider, "_extract_instagram_cookies", lambda _c: None)

    assert provider._import_from_browser(MagicMock()) is None


def test_extract_instagram_cookies_requires_sessionid(tmp_path, monkeypatch):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    candidate = SimpleNamespace(name="chrome", ytdlp_browser="chrome", profile_path=None)

    fake_module = ModuleType("yt_dlp.cookies")

    # Logged-out browser: instagram cookies but no sessionid -> None.
    fake_module.extract_cookies_from_browser = lambda *a, **k: [  # type: ignore[attr-defined]
        _cookie("csrftoken", ".instagram.com"),
        _cookie("VISITOR_INFO", ".youtube.com"),
    ]
    monkeypatch.setitem(sys.modules, "yt_dlp.cookies", fake_module)
    assert provider._extract_instagram_cookies(candidate) is None

    # Logged-in browser: sessionid present -> jar with only instagram cookies.
    fake_module.extract_cookies_from_browser = lambda *a, **k: [  # type: ignore[attr-defined]
        _cookie("sessionid", ".instagram.com"),
        _cookie("csrftoken", ".instagram.com"),
        _cookie("VISITOR_INFO", ".youtube.com"),
    ]
    jar = provider._extract_instagram_cookies(candidate)
    assert jar is not None
    names = {c.name for c in jar}
    assert names == {"sessionid", "csrftoken"}


def test_extract_instagram_cookies_handles_missing_yt_dlp(tmp_path, monkeypatch):
    provider = InstagramSessionProvider(config=_config(tmp_path))
    candidate = SimpleNamespace(name="chrome", ytdlp_browser="chrome", profile_path=None)
    # Ensure the lazy import fails cleanly (yt_dlp is a Mock without a real submodule).
    monkeypatch.delitem(sys.modules, "yt_dlp.cookies", raising=False)

    assert provider._extract_instagram_cookies(candidate) is None


# ---------------------------------------------------------------------------
# InstagramDownloader
# ---------------------------------------------------------------------------


def _downloader(config, provider) -> InstagramDownloader:
    return InstagramDownloader(
        error_handler=None,
        file_service=MagicMock(),
        config=config,
        session_provider=provider,
    )


def test_authenticate_uses_session_and_ignores_password(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.services.instagram.downloader.check_site_connection",
        lambda _service: (True, None),
    )
    provider = MagicMock()
    provider.load_session.return_value = "dave"
    downloader = _downloader(_config(tmp_path), provider)

    assert downloader.authenticate(username="dave", password="ignored-secret") is True
    assert downloader.authenticated is True
    provider.load_session.assert_called_once()


def test_authenticate_returns_false_without_session(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.services.instagram.downloader.check_site_connection",
        lambda _service: (True, None),
    )
    provider = MagicMock()
    provider.load_session.return_value = None
    downloader = _downloader(_config(tmp_path), provider)

    assert downloader.authenticate() is False
    assert downloader.authenticated is False


def test_authenticate_fails_when_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.services.instagram.downloader.check_site_connection",
        lambda _service: (False, "No connection"),
    )
    provider = MagicMock()
    downloader = _downloader(_config(tmp_path), provider)

    assert downloader.authenticate() is False
    provider.load_session.assert_not_called()


def test_ensure_session_creates_loader(tmp_path):
    provider = MagicMock()
    provider.load_session.return_value = None
    downloader = _downloader(_config(tmp_path), provider)

    assert downloader.loader is None
    downloader._ensure_session()
    assert downloader.loader is not None


def test_is_auth_required_error_by_type_name():
    class LoginRequiredException(Exception):
        pass

    assert InstagramDownloader._is_auth_required_error(LoginRequiredException()) is True
    assert InstagramDownloader._is_auth_required_error(ValueError("nope")) is False


def test_is_auth_required_error_by_message():
    assert (
        InstagramDownloader._is_auth_required_error(Exception("Login required to view this"))
        is True
    )


def test_auth_required_message_is_actionable():
    text = INSTAGRAM_AUTH_REQUIRED_MESSAGE.lower()
    assert "browser" in text
    assert "instaloader --login" in text
    assert "username/password" in text
