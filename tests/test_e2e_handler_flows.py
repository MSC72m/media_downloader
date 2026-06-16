"""E2E-style tests for all platform handler flows.

These tests exercise the same code paths the UI uses, without requiring
actual UI interaction. They verify that after code fixes, the full app
will work end-to-end via UI without issues.

Each test:
1. Creates a handler with mocked dependencies
2. Calls the handler's callback with a URL and mocked UI context
3. Verifies the correct Download object is created with valid URL
4. Verifies the callback receives the Download

Expanded tests cover:
- ServiceFactory URL detection for all platforms
- ServiceFactory downloader creation for all platforms
- DownloadHandler.process_url() full flow
- DownloadHandler._download_worker() with mocked downloaders
- EventCoordinator dynamic dispatch for all platforms
- SoundCloud premium track rejection
- SpotifyDialogHandler metadata fetch flow
- Edge cases (invalid URLs, empty URLs)
"""

import time
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.config import get_config
from src.core.enums.download_status import DownloadStatus
from src.core.enums.service_type import ServiceType
from src.core.models import Download
from src.services.detection.base_handler import BaseHandler
from src.services.detection.link_detector import LinkDetectionRegistry, LinkDetector
from src.services.spotify.downloader import SpotifyDownloader

# ============================================================================
# Mock Infrastructure
# ============================================================================


class MockMessageQueue:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    def add_message(self, message: Any) -> None:
        self.messages.append(message)


class MockErrorNotifier:
    def __init__(self) -> None:
        self.errors: list[Any] = []

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None:
        self.errors.append((context, str(exception)))

    def handle_service_failure(
        self, service: str, operation: str, error_message: str, url: str = ""
    ) -> None:
        self.errors.append((service, operation, error_message))

    def notify_user(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockCookieHandler:
    def set_cookie_file(self, path: str) -> bool:
        return True

    def has_valid_cookies(self) -> bool:
        return True

    def get_cookie_info_for_ytdlp(self) -> dict | None:
        return None


class MockAutoCookieManager:
    def is_ready(self) -> bool:
        return True

    def is_generating(self) -> bool:
        return False

    def get_state(self) -> Any:
        return None

    def get_cookies(self) -> str | None:
        return None

    @property
    def generator(self) -> Any:
        return Mock(get_state=lambda: None)


class MockIMetadataService:
    def fetch_metadata(self, url: str, **kwargs: Any) -> Any:
        return Mock(title="Mock Video", duration=180)


class MockInstagramAuthManager:
    def is_authenticating(self) -> bool:
        return False

    def is_authenticated(self) -> bool:
        return True


class MockDownloadsCoordinator:
    def __init__(self) -> None:
        self.downloads: list[Download] = []

    def add_download(self, download: Download) -> None:
        self.downloads.append(download)

    def get_downloads(self) -> list[Download]:
        return self.downloads.copy()


class MockUIContext:
    def __init__(self) -> None:
        self.root = MagicMock()
        self.root.after = MagicMock(side_effect=lambda ms, fn: fn() if ms == 0 else None)
        self.downloads = MockDownloadsCoordinator()

        def _make_platform_download(platform: str):
            def _download(url: str, **kwargs: Any) -> None:
                dl = Download(
                    url=url,
                    name=kwargs.get("name") or url.rsplit("/", maxsplit=1)[-1] or f"{platform}_download",
                    service_type=platform if platform != "generic" else None,
                )
                self.downloads.add_download(dl)
            return _download

        self.youtube_download = _make_platform_download("youtube")
        self.twitter_download = _make_platform_download("twitter")
        self.instagram_download = _make_platform_download("instagram")
        self.pinterest_download = _make_platform_download("pinterest")
        self.spotify_download = _make_platform_download("spotify")
        self.tiktok_download = _make_platform_download("tiktok")
        self.radiojavan_download = _make_platform_download("radiojavan")
        self.soundcloud_download = _make_platform_download("soundcloud")
        self.generic_download = _make_platform_download("generic")
        self.platform_dialogs = MagicMock()


def _create_handler_factory() -> Any:
    """Create a handler factory that provides mocked dependencies."""

    def factory(handler_class: type[BaseHandler]) -> BaseHandler:
        msg_queue = MockMessageQueue()
        err_handler = MockErrorNotifier()

        from src.handlers.instagram_handler import InstagramHandler
        from src.handlers.youtube_handler import YouTubeHandler

        if handler_class is InstagramHandler:
            return handler_class(
                instagram_auth_manager=MockInstagramAuthManager(),
                error_handler=err_handler,
                message_queue=msg_queue,
                config=get_config(),
            )
        if handler_class is YouTubeHandler:
            return handler_class(
                cookie_handler=MockCookieHandler(),
                metadata_service=MockIMetadataService(),
                auto_cookie_manager=MockAutoCookieManager(),
                message_queue=msg_queue,
                error_handler=err_handler,
                config=get_config(),
            )

        try:
            return handler_class(
                message_queue=msg_queue,
                error_handler=err_handler,
                config=get_config(),
            )
        except TypeError:
            return handler_class(
                error_handler=err_handler,
                message_queue=msg_queue,
                config=get_config(),
            )

    return factory


# ============================================================================
# E2E Tests: URL Detection → Handler → Download
# ============================================================================


class TestE2EDetection:
    """Test URL detection correctly routes to the right handler."""

    def setup_method(self) -> None:
        from src.handlers import _register_link_handlers

        _register_link_handlers()
        LinkDetectionRegistry.set_handler_factory(_create_handler_factory())

    def teardown_method(self) -> None:
        LinkDetectionRegistry._handler_factory = None

    def test_spotify_detection(self) -> None:
        url = "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "SpotifyHandler"

    def test_youtube_detection(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "YouTubeHandler"

    def test_soundcloud_detection(self) -> None:
        url = "https://soundcloud.com/forss/flickermood"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "SoundCloudHandler"

    def test_tiktok_detection(self) -> None:
        url = "https://www.tiktok.com/@scout2015/video/6718335390845095173"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "TikTokHandler"

    def test_radiojavan_detection(self) -> None:
        url = "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "RadioJavanHandler"

    def test_twitter_detection(self) -> None:
        url = "https://x.com/SpaceX/status/1798743372168431848"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "TwitterHandler"

    def test_youtube_short_detection(self) -> None:
        url = "https://youtu.be/dQw4w9WgXcQ"
        handler = LinkDetectionRegistry.detect_handler(url)
        assert handler is not None
        assert handler.__class__.__name__ == "YouTubeHandler"


# ============================================================================
# E2E Tests: Handler Callback → Download Creation
# ============================================================================


class TestE2EHandlerCallbacks:
    """Test that handler callbacks create correct Download objects."""

    def _make_ui_context(self) -> MockUIContext:
        return MockUIContext()

    def test_soundcloud_callback_creates_download(self) -> None:
        from src.handlers.soundcloud_handler import SoundCloudHandler

        handler = SoundCloudHandler(
            message_queue=MockMessageQueue(),
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )

        ui_ctx = self._make_ui_context()
        callback = handler.get_ui_callback()
        callback("https://soundcloud.com/forss/flickermood", ui_ctx)

        assert len(ui_ctx.downloads.downloads) == 1
        dl = ui_ctx.downloads.downloads[0]
        assert dl.url == "https://soundcloud.com/forss/flickermood"
        assert dl.service_type == ServiceType.SOUNDCLOUD

    def test_tiktok_callback_creates_download(self) -> None:
        from src.handlers.tiktok_handler import TikTokHandler

        handler = TikTokHandler(
            message_queue=MockMessageQueue(),
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )

        ui_ctx = self._make_ui_context()
        callback = handler.get_ui_callback()
        callback(
            "https://www.tiktok.com/@scout2015/video/6718335390845095173", ui_ctx
        )

        assert len(ui_ctx.downloads.downloads) == 1
        dl = ui_ctx.downloads.downloads[0]
        assert dl.url == "https://www.tiktok.com/@scout2015/video/6718335390845095173"
        assert dl.service_type == ServiceType.TIKTOK

    def test_twitter_callback_creates_download(self) -> None:
        from src.handlers.twitter_handler import TwitterHandler

        handler = TwitterHandler(
            error_handler=MockErrorNotifier(),
            message_queue=MockMessageQueue(),
            config=get_config(),
        )

        ui_ctx = self._make_ui_context()
        callback = handler.get_ui_callback()
        callback("https://x.com/SpaceX/status/1798743372168431848", ui_ctx)

        assert len(ui_ctx.downloads.downloads) == 1
        dl = ui_ctx.downloads.downloads[0]
        assert dl.url == "https://x.com/SpaceX/status/1798743372168431848"
        assert dl.service_type == ServiceType.TWITTER

    def test_radiojavan_callback_creates_download(self) -> None:
        from src.handlers.radiojavan_handler import RadioJavanHandler

        handler = RadioJavanHandler(
            message_queue=MockMessageQueue(),
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )

        ui_ctx = self._make_ui_context()
        callback = handler.get_ui_callback()
        callback(
            "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro", ui_ctx
        )

        assert len(ui_ctx.downloads.downloads) == 1
        dl = ui_ctx.downloads.downloads[0]
        assert dl.url == "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro"
        assert dl.service_type == ServiceType.RADIOJAVAN

    def test_pinterest_callback_creates_download(self) -> None:
        from src.handlers.pinterest_handler import PinterestHandler

        handler = PinterestHandler(
            error_handler=MockErrorNotifier(),
            message_queue=MockMessageQueue(),
            config=get_config(),
        )

        ui_ctx = self._make_ui_context()
        callback = handler.get_ui_callback()
        callback("https://www.pinterest.com/pin/123456789/", ui_ctx)

        assert len(ui_ctx.downloads.downloads) == 1
        dl = ui_ctx.downloads.downloads[0]
        assert dl.url == "https://www.pinterest.com/pin/123456789/"
        assert dl.service_type == ServiceType.PINTEREST

    def test_instagram_callback_creates_download(self) -> None:
        from src.handlers.instagram_handler import InstagramHandler

        handler = InstagramHandler(
            instagram_auth_manager=MockInstagramAuthManager(),
            error_handler=MockErrorNotifier(),
            message_queue=MockMessageQueue(),
            config=get_config(),
        )

        ui_ctx = self._make_ui_context()
        callback = handler.get_ui_callback()
        callback("https://www.instagram.com/p/ABC123/", ui_ctx)

        assert len(ui_ctx.downloads.downloads) >= 1
        urls = [dl.url for dl in ui_ctx.downloads.downloads]
        assert "https://www.instagram.com/p/ABC123/" in urls


# ============================================================================
# E2E Tests: Spotify Dialog Flow (the bug fix verification)
# ============================================================================


class TestE2ESpotifyDialogFlow:
    """Test the Spotify dialog's full flow: YouTube search → URL extraction → Download."""

    def test_extract_youtube_url_with_webpage_url(self) -> None:
        result = {"webpage_url": "https://www.youtube.com/watch?v=abc123", "id": "abc123"}
        url = SpotifyDownloader._extract_youtube_url(result)
        assert url == "https://www.youtube.com/watch?v=abc123"

    def test_extract_youtube_url_with_id_only(self) -> None:
        result = {"id": "abc123", "title": "Test Video"}
        url = SpotifyDownloader._extract_youtube_url(result)
        assert url == "https://www.youtube.com/watch?v=abc123"

    def test_extract_youtube_url_with_http_url(self) -> None:
        result = {"url": "https://www.youtube.com/watch?v=abc123"}
        url = SpotifyDownloader._extract_youtube_url(result)
        assert url == "https://www.youtube.com/watch?v=abc123"

    def test_extract_youtube_url_with_relative_url(self) -> None:
        result = {"url": "/watch?v=abc123"}
        url = SpotifyDownloader._extract_youtube_url(result)
        assert url is None

    def test_extract_youtube_url_empty_result(self) -> None:
        url = SpotifyDownloader._extract_youtube_url({})
        assert url is None

    def test_spotify_dialog_download_uses_extract_youtube_url(self) -> None:
        """Verify the Spotify dialog creates Download with valid YouTube URL."""
        mock_yt_results = [
            {
                "id": "dQw4w9WgXcQ",
                "title": "The Killers - Mr Brightside (Lyrics)",
                "duration": 222,
            }
        ]

        youtube_url = SpotifyDownloader._extract_youtube_url(mock_yt_results[0])
        assert youtube_url is not None
        assert "dQw4w9WgXcQ" in youtube_url

        download = Download(
            url=youtube_url,
            name="Mr Brightside.mp3",
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
        )
        assert download.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert download.service_type == ServiceType.SPOTIFY
        assert download.audio_only is True

    def test_spotify_dialog_old_behavior_would_fail(self) -> None:
        """Verify that the old .get('webpage_url') would return None for flat results."""
        flat_result = {
            "id": "abc123",
            "title": "Test Video",
            "duration": 180,
        }
        old_url = flat_result.get("webpage_url")
        new_url = SpotifyDownloader._extract_youtube_url(flat_result)
        assert old_url is None
        assert new_url == "https://www.youtube.com/watch?v=abc123"


# ============================================================================
# E2E Tests: Spotify Playlist Flow
# ============================================================================


class TestE2ESpotifyPlaylistFlow:
    """Test the Spotify playlist dialog flow."""

    def test_playlist_best_match_url_extraction(self) -> None:
        best_match = {"id": "abc123", "title": "Track 1 Official"}
        url = SpotifyDownloader._extract_youtube_url(best_match)
        assert url == "https://www.youtube.com/watch?v=abc123"

    def test_playlist_no_best_match_returns_none(self) -> None:
        track_data = {"title": "Track 1", "best_match": None}
        best_match = track_data.get("best_match")
        assert best_match is None

        url = SpotifyDownloader._extract_youtube_url(best_match) if best_match else None
        assert url is None

    def test_playlist_extract_youtube_url_fallback_to_id(self) -> None:
        best_match = {"id": "xyz789", "title": "Song"}
        url = SpotifyDownloader._extract_youtube_url(best_match)
        assert url == "https://www.youtube.com/watch?v=xyz789"


# ============================================================================
# E2E Tests: Download Model Validation
# ============================================================================


class TestE2EDownloadValidation:
    """Test that Download model rejects invalid inputs."""

    def test_download_rejects_none_url(self) -> None:
        with pytest.raises(ValueError, match="URL cannot be None"):
            Download(url=None, name="test")

    def test_download_rejects_invalid_url(self) -> None:
        with pytest.raises((ValueError, Exception), match="URL"):
            Download(url="not-a-url", name="test")

    def test_download_accepts_valid_http_url(self) -> None:
        dl = Download(url="http://example.com/video", name="test")
        assert dl.url == "http://example.com/video"

    def test_download_accepts_valid_https_url(self) -> None:
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test")
        assert dl.url == "https://www.youtube.com/watch?v=abc"

    def test_download_all_service_types(self) -> None:
        urls = {
            ServiceType.YOUTUBE: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            ServiceType.SPOTIFY: "https://open.spotify.com/track/abc123",
            ServiceType.SOUNDCLOUD: "https://soundcloud.com/artist/track",
            ServiceType.TIKTOK: "https://www.tiktok.com/@user/video/123",
            ServiceType.TWITTER: "https://x.com/user/status/123",
            ServiceType.INSTAGRAM: "https://www.instagram.com/p/abc/",
            ServiceType.PINTEREST: "https://www.pinterest.com/pin/123/",
            ServiceType.RADIOJAVAN: "https://www.radiojavan.com/mp3s/mp3/artist-song",
        }
        for service_type, url in urls.items():
            dl = Download(url=url, name="test", service_type=service_type)
            assert dl.service_type == service_type


# ============================================================================
# E2E Tests: Full LinkDetector Flow
# ============================================================================


class TestE2ELinkDetectorFlow:
    """Test the complete detect_and_handle flow for each platform."""

    def setup_method(self) -> None:
        from src.handlers import _register_link_handlers

        _register_link_handlers()
        LinkDetectionRegistry.set_handler_factory(_create_handler_factory())

    def teardown_method(self) -> None:
        LinkDetectionRegistry._handler_factory = None

    def _make_ui_context(self) -> MockUIContext:
        return MockUIContext()

    def test_soundcloud_detect_and_handle(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        result = detector.detect_and_handle(
            "https://soundcloud.com/forss/flickermood", ui_ctx
        )
        assert result is True
        assert len(ui_ctx.downloads.downloads) == 1
        assert ui_ctx.downloads.downloads[0].url == "https://soundcloud.com/forss/flickermood"

    def test_tiktok_detect_and_handle(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        result = detector.detect_and_handle(
            "https://www.tiktok.com/@scout2015/video/6718335390845095173", ui_ctx
        )
        assert result is True
        assert len(ui_ctx.downloads.downloads) == 1

    def test_twitter_detect_and_handle(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        result = detector.detect_and_handle(
            "https://x.com/SpaceX/status/1798743372168431848", ui_ctx
        )
        assert result is True
        assert len(ui_ctx.downloads.downloads) == 1

    def test_radiojavan_detect_and_handle(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        result = detector.detect_and_handle(
            "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro", ui_ctx
        )
        assert result is True
        assert len(ui_ctx.downloads.downloads) == 1

    def test_pinterest_detect_and_handle(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        result = detector.detect_and_handle(
            "https://www.pinterest.com/pin/123456789/", ui_ctx
        )
        assert result is True
        assert len(ui_ctx.downloads.downloads) == 1

    def test_instagram_detect_and_handle(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        result = detector.detect_and_handle(
            "https://www.instagram.com/p/ABC123/", ui_ctx
        )
        assert result is True
        assert len(ui_ctx.downloads.downloads) >= 1
        urls = [dl.url for dl in ui_ctx.downloads.downloads]
        assert "https://www.instagram.com/p/ABC123/" in urls

    def test_spotify_detect_and_handle_opens_dialog(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        with patch(
            "src.handlers.spotify_handler.schedule_on_main_thread"
        ) as mock_schedule:
            mock_schedule.side_effect = lambda _root, func, **_kwargs: func()
            with patch(
                "src.handlers.spotify_handler.SpotifyDownloaderDialog"
            ) as mock_dialog_cls:
                result = detector.detect_and_handle(
                    "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp",
                    ui_ctx,
                )
                assert result is True
                mock_dialog_cls.assert_called_once()

    def test_youtube_detect_and_handle_opens_dialog(self) -> None:
        detector = LinkDetector()
        ui_ctx = self._make_ui_context()
        with patch(
            "src.handlers.youtube_handler.schedule_on_main_thread"
        ) as mock_schedule:
            mock_schedule.side_effect = lambda _root, func, **_kwargs: func()
            with patch(
                "src.handlers.youtube_handler.YouTubeDownloaderDialog"
            ) as mock_dialog_cls:
                result = detector.detect_and_handle(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ui_ctx
                )
                assert result is True
                mock_dialog_cls.assert_called_once()


# ============================================================================
# E2E Tests: Platform Dialog Coordinator Flow
# ============================================================================


class TestE2EPlatformDialogCoordinator:
    """Test the PlatformDialogCoordinator creates correct Download objects."""

    def test_sync_dialog_handlers_create_valid_downloads(self) -> None:
        from src.coordinators.platform_dialog_coordinator import (
            InstagramDialogHandler,
            PinterestDialogHandler,
            RadioJavanDialogHandler,
            TikTokDialogHandler,
            TwitterDialogHandler,
        )

        error_handler = MockErrorNotifier()

        handlers_and_urls = [
            (TwitterDialogHandler(error_handler), "https://x.com/user/status/123"),
            (InstagramDialogHandler(error_handler), "https://www.instagram.com/p/abc/"),
            (PinterestDialogHandler(error_handler), "https://www.pinterest.com/pin/123/"),
            (RadioJavanDialogHandler(error_handler), "https://www.radiojavan.com/mp3s/mp3/song"),
            (TikTokDialogHandler(error_handler), "https://www.tiktok.com/@u/video/123"),
        ]

        for handler, url in handlers_and_urls:
            received_download: list[Download] = []

            def capture(download: Download, _dl_list: list[Download] = received_download) -> None:
                _dl_list.append(download)

            handler.show_dialog(url, capture)
            assert len(received_download) == 1
            dl = received_download[0]
            assert dl.url == url
            assert dl.name is not None
            assert len(dl.name) > 0

    def test_soundcloud_dialog_handler_async(self) -> None:
        from src.coordinators.platform_dialog_coordinator import SoundCloudDialogHandler

        error_handler = MockErrorNotifier()
        handler = SoundCloudDialogHandler(error_handler)
        received_download: list[Download] = []

        def capture(download: Download) -> None:
            received_download.append(download)

        handler.show_dialog("https://soundcloud.com/artist/track", capture)

        deadline = time.time() + 5
        while not received_download and time.time() < deadline:
            time.sleep(0.05)

        assert len(received_download) == 1
        dl = received_download[0]
        assert dl.url == "https://soundcloud.com/artist/track"
        assert dl.name is not None
        assert len(dl.name) > 0


# ============================================================================
# E2E Tests: ServiceFactory URL Detection
# ============================================================================


class TestE2EServiceFactoryDetection:
    """Test ServiceFactory.detect_service_type() correctly maps URLs to ServiceType."""

    def setup_method(self) -> None:
        from src.application.service_factory import ServiceFactory

        self.factory = ServiceFactory()

    def test_youtube_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == ServiceType.YOUTUBE

    def test_youtube_short_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://youtu.be/dQw4w9WgXcQ") == ServiceType.YOUTUBE

    def test_soundcloud_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://soundcloud.com/forss/flickermood") == ServiceType.SOUNDCLOUD

    def test_twitter_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://x.com/SpaceX/status/1798743372168431848") == ServiceType.TWITTER

    def test_twitter_old_domain_detection(self) -> None:
        assert self.factory.detect_service_type("https://twitter.com/user/status/123") == ServiceType.TWITTER

    def test_instagram_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://www.instagram.com/p/ABC123/") == ServiceType.INSTAGRAM

    def test_pinterest_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://www.pinterest.com/pin/123456789/") == ServiceType.PINTEREST

    def test_pinterest_short_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://pin.it/abc123") == ServiceType.PINTEREST

    def test_tiktok_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://www.tiktok.com/@scout2015/video/6718335390845095173") == ServiceType.TIKTOK

    def test_tiktok_vm_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://vm.tiktok.com/abc123") == ServiceType.TIKTOK

    def test_radiojavan_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro") == ServiceType.RADIOJAVAN

    def test_radiojavan_play_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://play.radiojavan.com/mp3s/mp3/artist-song") == ServiceType.RADIOJAVAN

    def test_radiojavan_app_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://rj.app/mp3s/mp3/artist-song") == ServiceType.RADIOJAVAN

    def test_spotify_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp") == ServiceType.SPOTIFY

    def test_spotify_short_url_detection(self) -> None:
        assert self.factory.detect_service_type("https://spotify.link/abc123") == ServiceType.SPOTIFY

    def test_unknown_url_returns_generic(self) -> None:
        assert self.factory.detect_service_type("https://example.com/video") == ServiceType.GENERIC


# ============================================================================
# E2E Tests: ServiceFactory Downloader Creation
# ============================================================================


class TestE2EServiceFactoryDownloaderCreation:
    """Test ServiceFactory.get_downloader() creates the correct downloader class for each platform."""

    def setup_method(self) -> None:
        from src.application.service_factory import ServiceFactory

        self.factory = ServiceFactory()

    def test_youtube_downloader_created(self) -> None:
        from src.services.youtube.downloader import YouTubeDownloader

        downloader = self.factory.get_downloader("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert downloader is not None
        assert isinstance(downloader, YouTubeDownloader)

    def test_soundcloud_downloader_created(self) -> None:
        from src.services.soundcloud.downloader import SoundCloudDownloader

        downloader = self.factory.get_downloader("https://soundcloud.com/forss/flickermood")
        assert downloader is not None
        assert isinstance(downloader, SoundCloudDownloader)

    def test_twitter_downloader_created(self) -> None:
        from src.services.twitter.downloader import TwitterDownloader

        downloader = self.factory.get_downloader("https://x.com/SpaceX/status/1798743372168431848")
        assert downloader is not None
        assert isinstance(downloader, TwitterDownloader)

    def test_instagram_downloader_created(self) -> None:
        from src.services.instagram.downloader import InstagramDownloader

        downloader = self.factory.get_downloader("https://www.instagram.com/p/ABC123/")
        assert downloader is not None
        assert isinstance(downloader, InstagramDownloader)

    def test_pinterest_downloader_created(self) -> None:
        from src.services.pinterest.downloader import PinterestDownloader

        downloader = self.factory.get_downloader("https://www.pinterest.com/pin/123/")
        assert downloader is not None
        assert isinstance(downloader, PinterestDownloader)

    def test_tiktok_downloader_created(self) -> None:
        from src.services.tiktok.downloader import TikTokDownloader

        downloader = self.factory.get_downloader("https://www.tiktok.com/@u/video/123")
        assert downloader is not None
        assert isinstance(downloader, TikTokDownloader)

    def test_radiojavan_downloader_created(self) -> None:
        from src.services.radiojavan.downloader import RadioJavanDownloader

        downloader = self.factory.get_downloader("https://www.radiojavan.com/mp3s/mp3/artist-song")
        assert downloader is not None
        assert isinstance(downloader, RadioJavanDownloader)

    def test_spotify_downloader_created(self) -> None:
        from src.services.spotify.downloader import SpotifyDownloader

        downloader = self.factory.get_downloader("https://open.spotify.com/track/abc123")
        assert downloader is not None
        assert isinstance(downloader, SpotifyDownloader)

    def test_unknown_url_returns_no_downloader(self) -> None:
        downloader = self.factory.get_downloader("https://unknown-site.com/video")
        assert downloader is None


# ============================================================================
# E2E Tests: DownloadHandler.process_url() Full Flow
# ============================================================================


class TestE2EDownloadHandlerProcessUrl:
    """Test DownloadHandler.process_url() creates Download and adds to queue."""

    def _make_handler(self) -> Any:
        from src.handlers.download_handler import DownloadHandler

        mock_service_factory = MagicMock()
        mock_file_service = MagicMock()
        mock_file_service.clean_filename.return_value = "test_file"
        mock_ui_state = MagicMock()
        mock_cookie_handler = MagicMock()

        handler = DownloadHandler(
            service_factory=mock_service_factory,
            file_service=mock_file_service,
            ui_state=mock_ui_state,
            cookie_handler=mock_cookie_handler,
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )
        return handler  # noqa: RET504

    def test_process_youtube_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_process_soundcloud_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://soundcloud.com/forss/flickermood")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].url == "https://soundcloud.com/forss/flickermood"

    def test_process_twitter_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://x.com/SpaceX/status/1798743372168431848")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1

    def test_process_instagram_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://www.instagram.com/p/ABC123/")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1

    def test_process_pinterest_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://www.pinterest.com/pin/123/")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1

    def test_process_tiktok_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://www.tiktok.com/@u/video/123")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1

    def test_process_radiojavan_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://www.radiojavan.com/mp3s/mp3/artist-song")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1

    def test_process_spotify_url(self) -> None:
        handler = self._make_handler()
        result = handler.process_url("https://open.spotify.com/track/abc123")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1

    def test_process_multiple_urls(self) -> None:
        handler = self._make_handler()
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://soundcloud.com/forss/flickermood",
            "https://x.com/SpaceX/status/123",
        ]
        for url in urls:
            result = handler.process_url(url)
            assert result is True
        assert len(handler.get_downloads()) == 3

    def test_add_download_creates_valid_download(self) -> None:
        handler = self._make_handler()
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test")
        handler.add_download(dl)
        downloads = handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].url == "https://www.youtube.com/watch?v=abc"

    def test_remove_downloads(self) -> None:
        handler = self._make_handler()
        dl1 = Download(url="https://www.youtube.com/watch?v=abc", name="test1")
        dl2 = Download(url="https://soundcloud.com/artist/track", name="test2")
        handler.add_download(dl1)
        handler.add_download(dl2)
        handler.remove_downloads([0])
        downloads = handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].url == "https://soundcloud.com/artist/track"

    def test_clear_downloads(self) -> None:
        handler = self._make_handler()
        handler.add_download(Download(url="https://www.youtube.com/watch?v=abc", name="t1"))
        handler.add_download(Download(url="https://soundcloud.com/artist/track", name="t2"))
        handler.clear_downloads()
        assert len(handler.get_downloads()) == 0


# ============================================================================
# E2E Tests: DownloadHandler._download_worker Full Pipeline
# ============================================================================


_TEST_DOWNLOAD_DIR = "/tmp/test_downloads"  # noqa: S108


class TestE2EDownloadWorkerPipeline:
    """Test DownloadHandler._download_worker with mocked ServiceFactory and Downloader."""

    def _make_handler_with_mock_factory(self, mock_downloader: MagicMock) -> Any:
        from src.handlers.download_handler import DownloadHandler

        mock_service_factory = MagicMock()
        mock_service_factory.detect_service_type.return_value = ServiceType.YOUTUBE
        mock_service_factory.get_downloader.return_value = mock_downloader

        mock_file_service = MagicMock()
        mock_file_service.clean_filename.return_value = "test_output"

        mock_ui_state = MagicMock()
        mock_cookie_handler = MagicMock()

        handler = DownloadHandler(
            service_factory=mock_service_factory,
            file_service=mock_file_service,
            ui_state=mock_ui_state,
            cookie_handler=mock_cookie_handler,
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )
        return handler  # noqa: RET504

    def test_download_worker_success(self) -> None:
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = True

        handler = self._make_handler_with_mock_factory(mock_downloader)
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test_video")

        handler._download_worker(dl, _TEST_DOWNLOAD_DIR, None)

        assert dl.status == DownloadStatus.COMPLETED
        mock_downloader.download.assert_called_once()

    def test_download_worker_failure(self) -> None:
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = False

        handler = self._make_handler_with_mock_factory(mock_downloader)
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test_video")

        handler._download_worker(dl, _TEST_DOWNLOAD_DIR, None)

        assert dl.status == DownloadStatus.FAILED

    def test_download_worker_no_downloader(self) -> None:
        mock_service_factory = MagicMock()
        mock_service_factory.detect_service_type.return_value = ServiceType.YOUTUBE
        mock_service_factory.get_downloader.return_value = None

        mock_file_service = MagicMock()
        mock_file_service.clean_filename.return_value = "test_output"

        from src.handlers.download_handler import DownloadHandler

        handler = DownloadHandler(
            service_factory=mock_service_factory,
            file_service=mock_file_service,
            ui_state=MagicMock(),
            cookie_handler=MagicMock(),
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )

        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test_video")
        handler._download_worker(dl, _TEST_DOWNLOAD_DIR, None)

        assert dl.status == DownloadStatus.FAILED

    def test_download_worker_exception_handling(self) -> None:
        mock_downloader = MagicMock()
        mock_downloader.download.side_effect = Exception("Network error")

        handler = self._make_handler_with_mock_factory(mock_downloader)
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test_video")

        handler._download_worker(dl, _TEST_DOWNLOAD_DIR, None)

        assert dl.status == DownloadStatus.FAILED
        assert "Network error" in dl.error_message

    def test_download_worker_service_detection(self) -> None:
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = True

        handler = self._make_handler_with_mock_factory(mock_downloader)
        dl = Download(url="https://soundcloud.com/artist/track", name="test_track")

        handler._download_worker(dl, _TEST_DOWNLOAD_DIR, None)

        handler.service_factory.detect_service_type.assert_called_with("https://soundcloud.com/artist/track")
        handler.service_factory.get_downloader.assert_called_with(
            "https://soundcloud.com/artist/track",
            service_type=ServiceType.YOUTUBE,
        )

    def test_download_worker_passes_correct_args_to_downloader(self) -> None:
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = True

        handler = self._make_handler_with_mock_factory(mock_downloader)
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test_video")

        handler._download_worker(dl, _TEST_DOWNLOAD_DIR, None)

        call_kwargs = mock_downloader.download.call_args
        assert call_kwargs[1]["url"] == "https://www.youtube.com/watch?v=abc"
        assert "test_output" in call_kwargs[1]["save_path"]

    def test_download_worker_progress_callback(self) -> None:
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = True

        handler = self._make_handler_with_mock_factory(mock_downloader)
        dl = Download(url="https://www.youtube.com/watch?v=abc", name="test_video")

        progress_calls: list[tuple[Download, float]] = []
        handler._download_worker(
            dl, _TEST_DOWNLOAD_DIR,
            lambda d, p: progress_calls.append((d, p)),
        )

        call_kwargs = mock_downloader.download.call_args
        progress_wrapper = call_kwargs[1]["progress_callback"]
        assert progress_wrapper is not None


# ============================================================================
# E2E Tests: EventCoordinator Dynamic Dispatch
# ============================================================================


class TestE2EEventCoordinatorDispatch:
    """Test EventCoordinator.__getattr__ dynamic dispatch for all platforms."""

    def _make_event_coordinator(self) -> Any:
        from src.coordinators.main_coordinator import EventCoordinator

        mock_root = MagicMock()
        mock_error_handler = MockErrorNotifier()
        mock_download_handler = MagicMock()
        mock_file_service = MagicMock()
        mock_network_checker = MagicMock()
        mock_cookie_handler = MagicMock()

        with (
            patch("src.coordinators.main_coordinator.DownloadEventBus"),
            patch("src.coordinators.main_coordinator.DownloadCoordinator"),
            patch("src.coordinators.main_coordinator.PlatformDialogCoordinator"),
        ):
            coord = EventCoordinator(
                root_window=mock_root,
                error_handler=mock_error_handler,
                download_handler=mock_download_handler,
                file_service=mock_file_service,
                network_checker=mock_network_checker,
                cookie_handler=mock_cookie_handler,
            )
        return coord  # noqa: RET504

    def test_youtube_download_dispatches_to_add_download(self) -> None:
        coord = self._make_event_coordinator()
        callback = coord.youtube_download
        assert callback is not None

    def test_twitter_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.twitter_download
            callback("https://x.com/user/status/123")
            mock_pd.assert_called_once_with("twitter", "https://x.com/user/status/123", None)

    def test_instagram_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.instagram_download
            callback("https://www.instagram.com/p/abc/")
            mock_pd.assert_called_once_with("instagram", "https://www.instagram.com/p/abc/", None)

    def test_pinterest_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.pinterest_download
            callback("https://www.pinterest.com/pin/123/")
            mock_pd.assert_called_once_with("pinterest", "https://www.pinterest.com/pin/123/", None)

    def test_spotify_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.spotify_download
            callback("https://open.spotify.com/track/abc")
            mock_pd.assert_called_once_with("spotify", "https://open.spotify.com/track/abc", None)

    def test_tiktok_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.tiktok_download
            callback("https://www.tiktok.com/@u/video/123")
            mock_pd.assert_called_once_with("tiktok", "https://www.tiktok.com/@u/video/123", None)

    def test_radiojavan_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.radiojavan_download
            callback("https://www.radiojavan.com/mp3s/mp3/song")
            mock_pd.assert_called_once_with("radiojavan", "https://www.radiojavan.com/mp3s/mp3/song", None)

    def test_soundcloud_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.soundcloud_download
            callback("https://soundcloud.com/artist/track")
            mock_pd.assert_called_once_with("soundcloud", "https://soundcloud.com/artist/track", None)

    def test_generic_download_dispatches_to_platform_download(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.generic_download
            callback("https://example.com/video", name="Custom Name")
            mock_pd.assert_called_once_with("generic", "https://example.com/video", "Custom Name")

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        coord = self._make_event_coordinator()
        with pytest.raises(AttributeError, match="object has no attribute 'nonexistent'"):
            _ = coord.nonexistent

    def test_platform_download_with_name_kwarg(self) -> None:
        coord = self._make_event_coordinator()
        with patch.object(coord, "platform_download") as mock_pd:
            callback = coord.twitter_download
            callback("https://x.com/user/status/123", name="My Tweet")
            mock_pd.assert_called_once_with("twitter", "https://x.com/user/status/123", "My Tweet")


# ============================================================================
# E2E Tests: PlatformDownload Routing
# ============================================================================


class TestE2EPlatformDownloadRouting:
    """Test EventCoordinator.platform_download routes to correct dialog handler."""

    def _make_event_coordinator(self) -> Any:
        from src.coordinators.main_coordinator import EventCoordinator

        mock_root = MagicMock()
        mock_error_handler = MockErrorNotifier()
        mock_download_handler = MagicMock()
        mock_file_service = MagicMock()
        mock_network_checker = MagicMock()
        mock_cookie_handler = MagicMock()

        with (
            patch("src.coordinators.main_coordinator.DownloadEventBus"),
            patch("src.coordinators.main_coordinator.DownloadCoordinator") as mock_dc_cls,
            patch("src.coordinators.main_coordinator.PlatformDialogCoordinator") as mock_pdc_cls,
        ):
            coord = EventCoordinator(
                root_window=mock_root,
                error_handler=mock_error_handler,
                download_handler=mock_download_handler,
                file_service=mock_file_service,
                network_checker=mock_network_checker,
                cookie_handler=mock_cookie_handler,
            )
            coord.downloads = mock_dc_cls.return_value
            coord.platform_dialogs = mock_pdc_cls.return_value
        return coord

    def test_twitter_routes_to_show_twitter_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("twitter", "https://x.com/user/status/123")
        coord.platform_dialogs.show_twitter_dialog.assert_called_once()

    def test_instagram_routes_to_show_instagram_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("instagram", "https://www.instagram.com/p/abc/")
        coord.platform_dialogs.show_instagram_dialog.assert_called_once()

    def test_pinterest_routes_to_show_pinterest_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("pinterest", "https://www.pinterest.com/pin/123/")
        coord.platform_dialogs.show_pinterest_dialog.assert_called_once()

    def test_soundcloud_routes_to_show_soundcloud_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("soundcloud", "https://soundcloud.com/artist/track")
        coord.platform_dialogs.show_soundcloud_dialog.assert_called_once()

    def test_spotify_routes_to_show_spotify_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("spotify", "https://open.spotify.com/track/abc")
        coord.platform_dialogs.show_spotify_dialog.assert_called_once()

    def test_tiktok_routes_to_show_tiktok_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("tiktok", "https://www.tiktok.com/@u/video/123")
        coord.platform_dialogs.show_tiktok_dialog.assert_called_once()

    def test_radiojavan_routes_to_show_radiojavan_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("radiojavan", "https://www.radiojavan.com/mp3s/mp3/song")
        coord.platform_dialogs.show_radiojavan_dialog.assert_called_once()

    def test_generic_routes_to_generic_download(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("generic", "https://example.com/video", name="My Video")
        coord.platform_dialogs.generic_download.assert_called_once()

    def test_unknown_platform_logs_error(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("unknown_platform", "https://example.com/video")
        coord.platform_dialogs.show_twitter_dialog.assert_not_called()
        coord.platform_dialogs.show_instagram_dialog.assert_not_called()

    def test_youtube_returns_without_dialog(self) -> None:
        coord = self._make_event_coordinator()
        coord.platform_download("youtube", "https://www.youtube.com/watch?v=abc")
        coord.platform_dialogs.show_youtube_dialog.assert_not_called()


# ============================================================================
# E2E Tests: SoundCloud Premium Track Rejection
# ============================================================================


class TestE2ESoundCloudPremiumRejection:
    """Test SoundCloudDialogHandler rejects premium tracks."""

    def test_premium_track_rejected(self) -> None:
        from src.coordinators.platform_dialog_coordinator import SoundCloudDialogHandler

        error_handler = MockErrorNotifier()

        with patch("src.coordinators.platform_dialog_coordinator.SoundCloudDownloader") as mock_sc_cls:
            mock_downloader = MagicMock()
            mock_downloader.get_info.return_value = {
                "title": "Premium Track",
                "artist": "Artist",
                "access": "premium",
            }
            mock_downloader._is_premium_track.return_value = True
            mock_sc_cls.return_value = mock_downloader

            handler = SoundCloudDialogHandler(error_handler)
            callback_calls: list[Download] = []
            handler.show_dialog("https://soundcloud.com/artist/premium-track", callback_calls.append)

            deadline = time.time() + 5
            while not callback_calls and not error_handler.errors and time.time() < deadline:
                time.sleep(0.05)

            assert len(callback_calls) == 0
            assert len(error_handler.errors) > 0

    def test_free_track_accepted(self) -> None:
        from src.coordinators.platform_dialog_coordinator import SoundCloudDialogHandler

        error_handler = MockErrorNotifier()

        with patch("src.coordinators.platform_dialog_coordinator.SoundCloudDownloader") as mock_sc_cls:
            mock_downloader = MagicMock()
            mock_downloader.get_info.return_value = {
                "title": "Free Track",
                "artist": "Artist",
                "access": "free",
            }
            mock_downloader._is_premium_track.return_value = False
            mock_sc_cls.return_value = mock_downloader

            handler = SoundCloudDialogHandler(error_handler)
            callback_calls: list[Download] = []
            handler.show_dialog("https://soundcloud.com/artist/free-track", callback_calls.append)

            deadline = time.time() + 5
            while not callback_calls and time.time() < deadline:
                time.sleep(0.05)

            assert len(callback_calls) == 1
            assert callback_calls[0].url == "https://soundcloud.com/artist/free-track"
            assert "Artist" in callback_calls[0].name
            assert "Free Track" in callback_calls[0].name


# ============================================================================
# E2E Tests: SpotifyDialogHandler Metadata Fetch
# ============================================================================


class TestE2ESpotifyDialogMetadataFetch:
    """Test SpotifyDialogHandler fetches metadata and creates Download with track name."""

    def test_spotify_handler_fetches_metadata(self) -> None:
        from src.coordinators.platform_dialog_coordinator import SpotifyDialogHandler

        error_handler = MockErrorNotifier()

        with patch("src.coordinators.platform_dialog_coordinator.SpotifyDownloader") as mock_sp_cls:
            mock_downloader = MagicMock()
            mock_downloader.get_metadata.return_value = {"title": "Mr Brightside"}
            mock_sp_cls.return_value = mock_downloader

            handler = SpotifyDialogHandler(error_handler)
            callback_calls: list[Download] = []
            handler.show_dialog("https://open.spotify.com/track/abc123", callback_calls.append)

            assert len(callback_calls) == 1
            assert callback_calls[0].name == "Mr Brightside"
            assert callback_calls[0].url == "https://open.spotify.com/track/abc123"

    def test_spotify_handler_fallback_name_on_error(self) -> None:
        from src.coordinators.platform_dialog_coordinator import SpotifyDialogHandler

        error_handler = MockErrorNotifier()

        with patch("src.coordinators.platform_dialog_coordinator.SpotifyDownloader") as mock_sp_cls:
            mock_downloader = MagicMock()
            mock_downloader.get_metadata.side_effect = Exception("API error")
            mock_sp_cls.return_value = mock_downloader

            handler = SpotifyDialogHandler(error_handler)
            callback_calls: list[Download] = []
            handler.show_dialog("https://open.spotify.com/track/abc123", callback_calls.append)

            assert len(callback_calls) == 0
            assert len(error_handler.errors) > 0


# ============================================================================
# E2E Tests: get_platform_callback Routing
# ============================================================================


class TestE2EGetPlatformCallback:
    """Test get_platform_callback returns the correct callback for each platform."""

    def test_youtube_returns_add_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "youtube")
        assert callback is not None
        assert callback == ctx.downloads.add_download

    def test_spotify_returns_add_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "spotify")
        assert callback is not None
        assert callback == ctx.downloads.add_download

    def test_twitter_returns_platform_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "twitter")
        assert callback is not None
        assert callback == ctx.twitter_download

    def test_instagram_returns_platform_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "instagram")
        assert callback is not None
        assert callback == ctx.instagram_download

    def test_pinterest_returns_platform_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "pinterest")
        assert callback is not None
        assert callback == ctx.pinterest_download

    def test_tiktok_returns_platform_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "tiktok")
        assert callback is not None
        assert callback == ctx.tiktok_download

    def test_radiojavan_returns_platform_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "radiojavan")
        assert callback is not None
        assert callback == ctx.radiojavan_download

    def test_soundcloud_returns_platform_download(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "soundcloud")
        assert callback is not None
        assert callback == ctx.soundcloud_download

    def test_unknown_platform_returns_none(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        ctx = MockUIContext()
        callback = get_platform_callback(ctx, "unknown")
        assert callback is None

    def test_none_context_returns_none(self) -> None:
        from src.utils.type_helpers import get_platform_callback

        callback = get_platform_callback(None, "youtube")
        assert callback is None


# ============================================================================
# E2E Tests: Edge Cases
# ============================================================================


class TestE2EEdgeCases:
    """Test edge cases in URL handling and download creation."""

    def test_download_rejects_none_url(self) -> None:
        with pytest.raises(ValueError, match="URL cannot be None"):
            Download(url=None, name="test")

    def test_download_accepts_empty_string_url(self) -> None:
        dl = Download(url="", name="test")
        assert dl.url == ""

    def test_handler_process_url_with_empty_url(self) -> None:
        from src.handlers.download_handler import DownloadHandler

        mock_service_factory = MagicMock()
        mock_file_service = MagicMock()
        mock_file_service.clean_filename.return_value = "download"

        handler = DownloadHandler(
            service_factory=mock_service_factory,
            file_service=mock_file_service,
            ui_state=MagicMock(),
            cookie_handler=MagicMock(),
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )

        result = handler.process_url("")
        assert result is True
        downloads = handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].url == ""

    def test_service_factory_detects_case_insensitive(self) -> None:
        from src.application.service_factory import ServiceFactory

        factory = ServiceFactory()
        assert factory.detect_service_type("https://WWW.YOUTUBE.COM/watch?v=abc") == ServiceType.YOUTUBE
        assert factory.detect_service_type("https://SOUNDCLOUD.COM/artist/track") == ServiceType.SOUNDCLOUD
        assert factory.detect_service_type("https://X.COM/user/status/123") == ServiceType.TWITTER

    def test_download_all_service_types_roundtrip(self) -> None:
        urls = {
            ServiceType.YOUTUBE: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            ServiceType.SPOTIFY: "https://open.spotify.com/track/abc123",
            ServiceType.SOUNDCLOUD: "https://soundcloud.com/artist/track",
            ServiceType.TIKTOK: "https://www.tiktok.com/@user/video/123",
            ServiceType.TWITTER: "https://x.com/user/status/123",
            ServiceType.INSTAGRAM: "https://www.instagram.com/p/abc/",
            ServiceType.PINTEREST: "https://www.pinterest.com/pin/123/",
            ServiceType.RADIOJAVAN: "https://www.radiojavan.com/mp3s/mp3/artist-song",
        }
        from src.application.service_factory import ServiceFactory

        factory = ServiceFactory()
        for service_type, url in urls.items():
            detected = factory.detect_service_type(url)
            assert detected == service_type, f"Failed for {url}: expected {service_type}, got {detected}"

    def test_download_handler_start_empty_list(self) -> None:
        from src.handlers.download_handler import DownloadHandler

        handler = DownloadHandler(
            service_factory=MagicMock(),
            file_service=MagicMock(),
            ui_state=MagicMock(),
            cookie_handler=MagicMock(),
            error_handler=MockErrorNotifier(),
            config=get_config(),
        )

        completion_results: list[tuple[bool, str | None]] = []
        handler.start_downloads([], completion_callback=lambda s, m: completion_results.append((s, m)))
        assert len(completion_results) == 1
        assert completion_results[0][0] is False
