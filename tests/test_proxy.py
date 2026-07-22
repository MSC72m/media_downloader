"""Focused unit tests for the shared proxy plumbing (issue #15)."""

from unittest.mock import MagicMock

import pytest

from src.core.config import AppConfig, NetworkConfig, get_config, reset_config, set_config
from src.utils.proxy import get_proxy, get_request_proxies


def _config_with_proxy(proxy: str | None) -> AppConfig:
    return AppConfig(network=NetworkConfig(proxy=proxy))


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """Keep the global config singleton clean around each test.

    ``get_config`` is ``@cache``-decorated, so the cache must also be cleared
    for ``set_config``/``reset_config`` to take effect within a test run.
    """
    get_config.cache_clear()
    reset_config()
    yield
    get_config.cache_clear()
    reset_config()


def test_proxy_defaults_to_none():
    assert NetworkConfig().proxy is None
    assert get_proxy(_config_with_proxy(None)) is None
    assert get_request_proxies(_config_with_proxy(None)) is None


@pytest.mark.parametrize(
    "proxy",
    [
        "socks5://127.0.0.1:1080",
        "socks5h://127.0.0.1:1080",
        "http://proxy.local:8080",
        "https://proxy.local:8443",
    ],
)
def test_supported_schemes_pass_through(proxy: str):
    assert get_proxy(_config_with_proxy(proxy)) == proxy
    assert get_request_proxies(_config_with_proxy(proxy)) == {
        "http": proxy,
        "https": proxy,
    }


def test_whitespace_is_stripped():
    assert get_proxy(_config_with_proxy("  socks5://127.0.0.1:1080  ")) == (
        "socks5://127.0.0.1:1080"
    )


@pytest.mark.parametrize("proxy", ["", "   ", "ftp://nope:21", "127.0.0.1:1080"])
def test_unsupported_or_empty_values_return_none(proxy: str):
    assert get_proxy(_config_with_proxy(proxy)) is None
    assert get_request_proxies(_config_with_proxy(proxy)) is None


def test_helpers_fall_back_to_singleton_config():
    set_config(_config_with_proxy("socks5://10.0.0.1:9050"))
    assert get_proxy() == "socks5://10.0.0.1:9050"
    assert get_request_proxies() == {
        "http": "socks5://10.0.0.1:9050",
        "https": "socks5://10.0.0.1:9050",
    }


def test_youtube_ytdl_options_include_proxy():
    """YouTube yt-dlp option dict must carry the configured proxy."""
    from src.services.youtube.downloader import YouTubeDownloader

    config = _config_with_proxy("socks5://127.0.0.1:1080")
    downloader = YouTubeDownloader(
        cookie_handler=MagicMock(),
        auto_cookie_manager=MagicMock(),
        config=config,
    )
    options = downloader._get_simple_ytdl_options()
    assert options["proxy"] == "socks5://127.0.0.1:1080"


def test_youtube_ytdl_options_omit_proxy_when_unset():
    from src.services.youtube.downloader import YouTubeDownloader

    downloader = YouTubeDownloader(
        cookie_handler=MagicMock(),
        auto_cookie_manager=MagicMock(),
        config=_config_with_proxy(None),
    )
    options = downloader._get_simple_ytdl_options()
    assert "proxy" not in options
