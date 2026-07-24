from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.service_factory import ServiceFactory
from src.core.config import AppConfig
from src.core.enums import ServiceType
from src.core.models import Download, DownloadResult
from src.services.instagram.downloader import InstagramDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.services.tiktok.downloader import TikTokDownloader
from src.services.youtube.downloader import YouTubeDownloader


def test_factory_propagates_all_youtube_download_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.youtube.downloader.is_ffmpeg_available", lambda: True)
    queued = Download(
        name="custom",
        url="https://www.youtube.com/watch?v=abc&list=playlist",
        service_type=ServiceType.YOUTUBE,
        quality="1080p",
        download_playlist=True,
        audio_only=True,
        format="audio",
        download_subtitles=True,
        selected_subtitles=[{"language_code": "en"}],
        download_thumbnail=False,
        embed_metadata=False,
        speed_limit=256,
        retries=5,
    )

    downloader = ServiceFactory(config=AppConfig()).get_downloader(
        queued.url,
        service_type=ServiceType.YOUTUBE,
        download=queued,
    )

    assert isinstance(downloader, YouTubeDownloader)
    assert downloader.quality == "1080p"
    assert downloader.download_playlist is True
    assert downloader.audio_only is True
    assert downloader.format == "audio"
    assert downloader.download_subtitles is True
    assert downloader.selected_subtitles == [{"language_code": "en"}]
    assert downloader.download_thumbnail is False
    assert downloader.embed_metadata is False
    assert downloader.speed_limit == 256
    assert downloader.retries == 5
    assert "noplaylist" not in downloader.ytdl_opts


def test_factory_enables_soundcloud_sets() -> None:
    downloader = ServiceFactory(config=AppConfig()).get_downloader(
        "https://soundcloud.com/artist/sets/my-set"
    )

    assert isinstance(downloader, SoundCloudDownloader)
    assert downloader.download_playlist is True
    assert "noplaylist" not in downloader.ytdl_opts


def test_factory_detection_uses_hostnames_and_international_pinterest() -> None:
    factory = ServiceFactory(config=AppConfig())

    assert (
        factory.detect_service_type("https://www.pinterest.co.uk/pin/123/")
        == ServiceType.PINTEREST
    )
    assert factory.detect_service_type("https://vt.tiktok.com/ABC123/") == ServiceType.TIKTOK
    assert (
        factory.detect_service_type(
            "https://evil.example/?next=https://instagram.com/p/ABC123/"
        )
        == ServiceType.GENERIC
    )


def test_mobile_youtube_and_tiktok_share_patterns_are_supported() -> None:
    config = AppConfig()

    assert any(
        re.match(pattern, "https://m.youtube.com/watch?v=abc")
        for pattern in config.youtube.url_patterns
    )
    assert any(
        re.match(pattern, "https://vt.tiktok.com/ABC123")
        for pattern in config.tiktok.url_patterns
    )


def test_instaloader_uses_configured_timeout_and_attempt_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("src.services.instagram.downloader.instaloader.Instaloader", constructor)
    config = AppConfig()
    config.instagram.default_timeout = 7
    config.instagram.max_login_attempts = 2

    InstagramDownloader(config=config)._create_loader()

    assert constructor.call_args.kwargs["request_timeout"] == 7
    assert constructor.call_args.kwargs["max_connection_attempts"] == 2


def test_instagram_carousel_progress_is_aggregate_and_partial_failure_fails(
    tmp_path: Path,
) -> None:
    downloader = InstagramDownloader(config=AppConfig())
    nodes = [
        SimpleNamespace(is_video=False, video_url=None, display_url="https://media/one.jpg"),
        SimpleNamespace(is_video=False, video_url=None, display_url="https://media/two.jpg"),
    ]
    post = SimpleNamespace(get_sidecar_nodes=lambda: iter(nodes))
    file_service = MagicMock()
    file_service.download_file.side_effect = [
        DownloadResult(success=True),
        DownloadResult(success=False, error_message="blocked"),
    ]

    def download_file(_url: str, _path: str, callback: object) -> DownloadResult:
        index = file_service.download_file.call_count
        assert callable(callback)
        callback(50.0, 1.0)
        callback(100.0, 0.0)
        return [
            DownloadResult(success=True),
            DownloadResult(success=False, error_message="blocked"),
        ][index - 1]

    file_service.download_file.side_effect = download_file
    updates: list[float] = []

    result = downloader._download_sidecar(
        post,
        str(tmp_path),
        "carousel",
        file_service,
        lambda percent, _speed: updates.append(percent),
    )

    assert result is False
    assert updates == [25.0, 50.0, 75.0, 100.0]
    assert updates == sorted(updates)


def test_tiktok_rejects_metadata_only_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ydl = MagicMock()
    ydl.extract_info.return_value = {"id": "abc", "title": "No file"}
    ydl_context = MagicMock()
    ydl_context.__enter__.return_value = ydl
    monkeypatch.setattr(
        "src.services.tiktok.downloader.yt_dlp.YoutubeDL",
        MagicMock(return_value=ydl_context),
    )

    assert (
        TikTokDownloader(config=AppConfig())._perform_download(
            "https://www.tiktok.com/@user/video/123",
            str(tmp_path / "video"),
            None,
        )
        is False
    )
