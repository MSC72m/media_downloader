"""Exact unit contracts for download progress reporting."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.core.config import get_config
from src.services.file.downloader import FileDownloader
from src.services.network.downloader import _stream_chunks_to_temp_file
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.services.tiktok.downloader import TikTokDownloader
from src.services.youtube.downloader import YouTubeDownloader
from src.ui.helpers.download_formatting import format_file_size, format_speed

_BYTES_PER_MB = 1024 * 1024


@pytest.mark.parametrize(
    ("hook_factory", "speed_bytes", "expected_mbps"),
    [
        (lambda callback: YouTubeDownloader._create_progress_hook(callback), 3 * _BYTES_PER_MB, 3.0),
        (
            lambda callback: SoundCloudDownloader(config=get_config())._create_progress_hook(
                callback
            ),
            2 * _BYTES_PER_MB,
            2.0,
        ),
        (
            lambda callback: TikTokDownloader(config=get_config())._create_progress_hook(callback),
            _BYTES_PER_MB,
            1.0,
        ),
    ],
)
def test_ytdlp_progress_hooks_report_mbps(
    hook_factory,
    speed_bytes: int,
    expected_mbps: float,
) -> None:
    updates: list[tuple[float, float]] = []
    hook = hook_factory(lambda progress, speed: updates.append((progress, speed)))

    hook(
        {
            "status": "downloading",
            "downloaded_bytes": _BYTES_PER_MB,
            "total_bytes": 2 * _BYTES_PER_MB,
            "speed": speed_bytes,
        }
    )

    assert updates == [(50.0, expected_mbps)]


def test_network_stream_reports_mbps(monkeypatch, tmp_path) -> None:
    updates: list[tuple[float, float]] = []
    times = iter((10.0, 11.0))
    monkeypatch.setattr("src.services.network.downloader.time.time", lambda: next(times))
    temp_file = str(tmp_path / "network.part")

    _stream_chunks_to_temp_file(
        chunks=[b"x" * _BYTES_PER_MB],
        temp_file=temp_file,
        total_size=2 * _BYTES_PER_MB,
        progress_callback=lambda progress, speed: updates.append((progress, speed)),
        config=get_config(),
    )

    assert updates == [(50.0, 1.0)]


def test_file_downloader_reports_mbps(monkeypatch, tmp_path) -> None:
    updates: list[tuple[float, float]] = []
    response = Mock()
    response.headers = {"content-length": str(2 * _BYTES_PER_MB)}
    response.iter_content.return_value = [b"x" * _BYTES_PER_MB]
    response.raise_for_status.return_value = None
    session = Mock()
    session.get.return_value = response
    monkeypatch.setattr("src.services.file.downloader.requests.Session", lambda: session)
    times = iter((10.0, 11.0, 12.0, 13.0))
    monkeypatch.setattr("src.services.file.downloader.time.time", lambda: next(times))

    result = FileDownloader(config=get_config()).download_file(
        "https://example.com/media.bin",
        str(tmp_path / "media.bin"),
        lambda progress, speed: updates.append((progress, speed)),
    )

    assert result.success is True
    assert updates[0] == (50.0, 1.0)
    assert updates[-1] == (100.0, 0.0)


def test_size_and_speed_labels_use_distinct_units() -> None:
    assert format_file_size(_BYTES_PER_MB) == "1.0MB"
    assert format_speed(1.0) == "1.0 MB/s"
    assert format_speed(0.5) == "500 KB/s"
