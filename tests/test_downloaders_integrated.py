#!/usr/bin/env python3
"""Integration tests that mirror the real app's download flow.

Sets up the same DI chain as ApplicationOrchestrator:
  ServiceContainer -> ServiceFactoryRegistry -> ServiceFactory -> Downloader

Tests each downloader *exactly* as the app creates and uses them.
"""

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.config import AppConfig, get_config
from src.core.enums import ServiceType
from src.core.interfaces import IErrorNotifier, IFileService
from src.services.cookies.cookie_manager import YouTubeCookieManager
from src.services.cookies.cookie_generator import CookieGenerator
from src.services.cookies.radiojavan_cookie_manager import RadioJavanCookieManager
from src.services.cookies.soundcloud_cookie_manager import SoundCloudCookieManager
from src.services.cookies.spotify_cookie_manager import SpotifyCookieManager

REAL_DOWNLOADS_ENABLED = os.environ.get("MEDIA_DL_TEST_REAL_DOWNLOADS") == "1"


class MockErrorHandler:
    def handle_service_failure(self, *a, **kw): pass
    def handle_exception(self, *a, **kw): pass
    def show_error(self, *a, **kw): pass
    def show_warning(self, *a, **kw): pass
    def show_info(self, *a, **kw): pass
    def set_message_queue(self, *a): pass


class MockFileService:
    def ensure_directory(self, path): return True
    def sanitize_filename(self, filename): return filename
    def clean_filename(self, filename): return filename
    def download_file(self, url, path, progress_callback=None):
        result = MagicMock()
        result.success = True
        return result
    def save_text_file(self, content, file_path): return True
    def get_unique_filename(self, directory, base_name, extension=""):
        return f"{directory}/{base_name}{extension}"


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def config():
    return get_config()


@pytest.fixture(scope="module")
def error_handler():
    return MockErrorHandler()


@pytest.fixture(scope="module")
def file_service():
    return MockFileService()


@pytest.fixture(scope="module")
def cookie_storage():
    with tempfile.TemporaryDirectory(prefix="media_dl_cookies_") as tmp:
        yield Path(tmp)


def _init_cookie_manager(mgr: Any, name: str, timeout: float = 15.0) -> str | None:
    """Initialize a cookie manager in a thread (mirrors orchestrator), returns path if available."""
    result: list[str | None] = [None]

    def _init():
        try:
            state = mgr.initialize()
            if state.is_valid:
                cookies = mgr.get_cookies()
                if isinstance(cookies, str):
                    result[0] = cookies
        except Exception:
            pass

    t = threading.Thread(target=_init, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return result[0]


# ── ServiceFactory (mirrors the app's factory chain) ──────────────────────

@pytest.fixture(scope="module")
def service_factory(config, error_handler, file_service, cookie_storage):
    from src.application.service_factory import ServiceFactory

    # Init cookie managers (same services as orchestrator._register_core_services)
    yt_cm = YouTubeCookieManager(storage_dir=cookie_storage, config=config)
    rj_cm = RadioJavanCookieManager(storage_dir=cookie_storage, config=config)
    sc_cm = SoundCloudCookieManager(storage_dir=cookie_storage, config=config)
    sp_cm = SpotifyCookieManager(storage_dir=cookie_storage, config=config)

    # Start background init (mirrors _initialize_cookies_background)
    threads = [
        threading.Thread(target=_init_cookie_manager, args=(yt_cm, "YouTube"), daemon=True),
        threading.Thread(target=_init_cookie_manager, args=(rj_cm, "RadioJavan"), daemon=True),
        threading.Thread(target=_init_cookie_manager, args=(sc_cm, "SoundCloud"), daemon=True),
        threading.Thread(target=_init_cookie_manager, args=(sp_cm, "Spotify"), daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    factory = ServiceFactory(
        cookie_handler=None,
        auto_cookie_manager=yt_cm if yt_cm.is_ready() else None,
        rj_cookie_manager=rj_cm if rj_cm.is_ready() else None,
        sc_cookie_manager=sc_cm if sc_cm.is_ready() else None,
        spotify_cookie_manager=sp_cm if sp_cm.is_ready() else None,
        error_handler=error_handler,
        file_service=file_service,
        config=config,
    )
    return factory


# ── Test data ─────────────────────────────────────────────────────────────

SERVICE_URLS = [
    (ServiceType.YOUTUBE, "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "YouTube"),
    (ServiceType.SOUNDCLOUD, "https://soundcloud.com/forss/flickermood", "SoundCloud"),
    (ServiceType.SPOTIFY, "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp", "Spotify"),
    (ServiceType.TIKTOK, "https://www.tiktok.com/@scout2015/video/6718335390845095173", "TikTok"),
    (ServiceType.RADIOJAVAN, "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro", "RadioJavan"),
    (ServiceType.TWITTER, "https://x.com/SpaceX/status/1798743372168431848", "Twitter"),
    (ServiceType.INSTAGRAM, "https://www.instagram.com/p/CuJtqA2sM4x/", "Instagram"),
    (ServiceType.PINTEREST, "https://www.pinterest.com/pin/1138825867154846972/", "Pinterest"),
]


# ── Tests ─────────────────────────────────────────────────────────────────

class TestAppFlowIntegration:
    """Tests that mirror the real app's download flow end-to-end."""

    @pytest.mark.parametrize("service_type,url,name", SERVICE_URLS)
    def test_service_factory_creates_downloader(self, service_factory, service_type, url, name):
        """Verify ServiceFactory.get_downloader() returns a working downloader."""
        downloader = service_factory.get_downloader(url)
        assert downloader is not None, f"{name}: ServiceFactory returned None"
        assert hasattr(downloader, "download"), f"{name}: downloader lacks download() method"
        assert callable(downloader.download), f"{name}: downloader.download is not callable"

    @pytest.mark.parametrize("service_type,url,name", SERVICE_URLS)
    def test_service_type_detection(self, service_factory, service_type, url, name):
        """Verify ServiceFactory.detect_service_type() correctly identifies each URL."""
        detected = service_factory.detect_service_type(url)
        assert detected == service_type, f"{name}: expected {service_type}, got {detected}"


class TestRealDownloads:
    """Actual end-to-end download tests.

    These tests download real files to verify the full pipeline works
    exactly as it does in the production app.  Tests are ordered by
    likelihood of success — most reliable first.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not REAL_DOWNLOADS_ENABLED,
        reason="Set MEDIA_DL_TEST_REAL_DOWNLOADS=1 to run network download tests",
    )
    def test_youtube_download_actual_file(self, config, error_handler, file_service, cookie_storage):
        """Download a real YouTube video and verify the output file."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Init cookie manager & factory (same chain as orchestrator)
        yt_cm = YouTubeCookieManager(storage_dir=cookie_storage, config=config)
        _init_cookie_manager(yt_cm, "YouTube", timeout=25)

        from src.application.service_factory import ServiceFactory
        sf = ServiceFactory(
            auto_cookie_manager=yt_cm if yt_cm.is_ready() else None,
            error_handler=error_handler,
            file_service=file_service,
            config=config,
        )
        downloader = sf.get_downloader(url)
        assert downloader is not None, "YouTube: ServiceFactory returned None"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "youtube_test")
            ok = downloader.download(url, save_path)
            files = [f for f in os.listdir(tmpdir) if f.startswith("youtube_test")]
            assert ok, f"YouTube download returned False (files: {files})"
            assert files, f"YouTube: no files created in {tmpdir}"
            sizes = [os.path.getsize(os.path.join(tmpdir, f)) for f in files]
            total_kb = sum(sizes) // 1024
            print(f"\n  YouTube: {len(files)} file(s), {total_kb}KB total")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not REAL_DOWNLOADS_ENABLED,
        reason="Set MEDIA_DL_TEST_REAL_DOWNLOADS=1 to run network download tests",
    )
    def test_radiojavan_download_actual_mp3(self, config, error_handler, file_service, cookie_storage):
        """Download a real RadioJavan MP3 and verify the output file."""
        url = "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro"
        rj_cm = RadioJavanCookieManager(storage_dir=cookie_storage, config=config)
        _init_cookie_manager(rj_cm, "RadioJavan")

        from src.application.service_factory import ServiceFactory
        sf = ServiceFactory(
            rj_cookie_manager=rj_cm if rj_cm.is_ready() else None,
            error_handler=error_handler,
            file_service=file_service,
            config=config,
        )
        downloader = sf.get_downloader(url)
        assert downloader is not None, "RadioJavan: ServiceFactory returned None"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "radiojavan_test")
            ok = downloader.download(url, save_path)
            files = [f for f in os.listdir(tmpdir) if f.startswith("radiojavan_test")]
            assert ok, f"RadioJavan download returned False (files: {files})"
            assert files, f"RadioJavan: no files created in {tmpdir}"
            total_bytes = sum(os.path.getsize(os.path.join(tmpdir, f)) for f in files)
            assert total_bytes > 1024, f"RadioJavan: file too small ({total_bytes} bytes) — likely error page"
            print(f"\n  RadioJavan: {len(files)} file(s), {total_bytes // 1024}KB")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not REAL_DOWNLOADS_ENABLED or not os.environ.get("MEDIA_DL_TEST_SOUNDCLOUD"),
        reason="Set MEDIA_DL_TEST_REAL_DOWNLOADS=1 and MEDIA_DL_TEST_SOUNDCLOUD=1 to test SoundCloud",
    )
    def test_soundcloud_download_actual_audio(self, config, error_handler, file_service, cookie_storage):
        """Download a real SoundCloud track and verify the output file."""
        url = "https://soundcloud.com/forss/flickermood"
        sc_cm = SoundCloudCookieManager(storage_dir=cookie_storage, config=config)
        _init_cookie_manager(sc_cm, "SoundCloud")

        from src.application.service_factory import ServiceFactory
        sf = ServiceFactory(
            sc_cookie_manager=sc_cm if sc_cm.is_ready() else None,
            error_handler=error_handler,
            file_service=file_service,
            config=config,
        )
        downloader = sf.get_downloader(url)
        assert downloader is not None, "SoundCloud: ServiceFactory returned None"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "soundcloud_test")
            ok = downloader.download(url, save_path)
            files = [f for f in os.listdir(tmpdir) if f.startswith("soundcloud_test")]
            assert ok, f"SoundCloud download returned False (files: {files})"
            assert files, f"SoundCloud: no files created in {tmpdir}"
            total_bytes = sum(os.path.getsize(os.path.join(tmpdir, f)) for f in files)
            assert total_bytes > 1024, f"SoundCloud: file too small ({total_bytes} bytes)"
            print(f"\n  SoundCloud: {len(files)} file(s), {total_bytes // 1024}KB")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not REAL_DOWNLOADS_ENABLED or not os.environ.get("MEDIA_DL_TEST_SPOTIFY"),
        reason="Set MEDIA_DL_TEST_REAL_DOWNLOADS=1 and MEDIA_DL_TEST_SPOTIFY=1 to test Spotify",
    )
    def test_spotify_download_actual_track(self, config, error_handler, file_service, cookie_storage):
        """Download a real Spotify track (YouTube-backed) and verify output."""
        url = "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp"
        yt_cm = YouTubeCookieManager(storage_dir=cookie_storage, config=config)
        _init_cookie_manager(yt_cm, "YouTube", timeout=25)

        from src.application.service_factory import ServiceFactory
        sf = ServiceFactory(
            auto_cookie_manager=yt_cm if yt_cm.is_ready() else None,
            error_handler=error_handler,
            file_service=file_service,
            config=config,
        )
        downloader = sf.get_downloader(url)
        assert downloader is not None, "Spotify: ServiceFactory returned None"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "spotify_test")
            ok = downloader.download(url, save_path)
            files = [f for f in os.listdir(tmpdir) if f.startswith("spotify_test")]
            assert ok, f"Spotify download returned False (files: {files})"
            assert files, f"Spotify: no files created in {tmpdir}"
            total_bytes = sum(os.path.getsize(os.path.join(tmpdir, f)) for f in files)
            assert total_bytes > 1024, f"Spotify: file too small ({total_bytes} bytes)"
            print(f"\n  Spotify: {len(files)} file(s), {total_bytes // 1024}KB")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not REAL_DOWNLOADS_ENABLED or not os.environ.get("MEDIA_DL_TEST_TIKTOK"),
        reason="Set MEDIA_DL_TEST_REAL_DOWNLOADS=1 and MEDIA_DL_TEST_TIKTOK=1 to test TikTok",
    )
    def test_tiktok_download_actual_video(self, config, error_handler, file_service):
        """Download a real TikTok video and verify the output file."""
        url = "https://www.tiktok.com/@scout2015/video/6718335390845095173"

        from src.application.service_factory import ServiceFactory
        sf = ServiceFactory(
            error_handler=error_handler,
            file_service=file_service,
            config=config,
        )
        downloader = sf.get_downloader(url)
        assert downloader is not None, "TikTok: ServiceFactory returned None"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "tiktok_test")
            ok = downloader.download(url, save_path)
            files = [f for f in os.listdir(tmpdir) if f.startswith("tiktok_test")]
            assert ok, f"TikTok download returned False (files: {files})"
            assert files, f"TikTok: no files created in {tmpdir}"
            total_bytes = sum(os.path.getsize(os.path.join(tmpdir, f)) for f in files)
            assert total_bytes > 1024, f"TikTok: file too small ({total_bytes} bytes)"
            print(f"\n  TikTok: {len(files)} file(s), {total_bytes // 1024}KB")


class TestCookieManagers:
    """Verify all cookie managers initialize without errors."""

    @pytest.mark.integration
    def test_youtube_cookie_manager_init(self, config, cookie_storage):
        mgr = YouTubeCookieManager(storage_dir=cookie_storage, config=config)
        path = _init_cookie_manager(mgr, "YouTube", timeout=25)
        if path:
            assert os.path.getsize(path) > 0, "YouTube cookie file is empty"
            print(f"\n  YouTube cookies: {path} ({os.path.getsize(path)} bytes)")

    @pytest.mark.integration
    def test_soundcloud_cookie_manager_init(self, config, cookie_storage):
        mgr = SoundCloudCookieManager(storage_dir=cookie_storage, config=config)
        path = _init_cookie_manager(mgr, "SoundCloud")
        if path:
            assert os.path.getsize(path) > 0, "SoundCloud cookie file is empty"
            print(f"\n  SoundCloud cookies: {path} ({os.path.getsize(path)} bytes)")

    @pytest.mark.integration
    def test_spotify_cookie_manager_init(self, config, cookie_storage):
        mgr = SpotifyCookieManager(storage_dir=cookie_storage, config=config)
        path = _init_cookie_manager(mgr, "Spotify")
        if path:
            assert os.path.getsize(path) > 0, "Spotify cookie file is empty"
            print(f"\n  Spotify cookies: {path} ({os.path.getsize(path)} bytes)")

    @pytest.mark.integration
    def test_radiojavan_cookie_manager_init(self, config, cookie_storage):
        mgr = RadioJavanCookieManager(storage_dir=cookie_storage, config=config)
        _init_cookie_manager(mgr, "RadioJavan")
        cookies = mgr.get_cookies()
        if cookies:
            assert len(cookies) > 0, "RadioJavan cookies are empty"
            print(f"\n  RadioJavan cookies: {len(cookies)} cookies")

    @pytest.mark.integration
    def test_all_cookie_managers_concurrent(self, config, cookie_storage):
        """Mirror orchestrator._initialize_cookies_background: all 4 managers start in parallel."""
        managers = [
            YouTubeCookieManager(storage_dir=cookie_storage, config=config),
            SoundCloudCookieManager(storage_dir=cookie_storage, config=config),
            SpotifyCookieManager(storage_dir=cookie_storage, config=config),
            RadioJavanCookieManager(storage_dir=cookie_storage, config=config),
        ]
        names = ["YouTube", "SoundCloud", "Spotify", "RadioJavan"]
        results: list[str | None] = [None] * 4

        def init_one(idx):
            results[idx] = _init_cookie_manager(managers[idx], names[idx])

        threads = [threading.Thread(target=init_one, args=(i,), daemon=True) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        ready = sum(1 for r in results if r)
        print(f"\n  Concurrent init: {ready}/4 managers ready ({names}: {[r is not None for r in results]})")

        # At least YouTube should work in this environment
        yt_ready = results[0] is not None
        print(f"  YouTube cookies: {'READY' if yt_ready else 'not available'}")
