"""Basic tests for the media downloader application."""

import pytest
import sys
from pathlib import Path

from core.models import Download, DownloadStatus, ServiceType


def test_download_model_creation():
    """Test that Download model can be created with basic parameters."""
    download = Download(
        name="Test Video",
        url="https://example.com/video",
        service_type=ServiceType.YOUTUBE
    )

    assert download.name == "Test Video"
    assert download.url == "https://example.com/video"
    assert download.service_type == ServiceType.YOUTUBE
    assert download.status == DownloadStatus.PENDING
    assert download.progress == 0.0


def test_download_model_with_optional_fields():
    """Test Download model with all optional fields."""
    download = Download(
        name="Test Video 2",
        url="https://example.com/video2",
        service_type=ServiceType.YOUTUBE,
        quality="1080p",
        format="video",
        audio_only=False,
        video_only=False,
        download_playlist=False,
        download_subtitles=True,
        selected_subtitles=[{"language_code": "en", "language_name": "English"}],
        download_thumbnail=True,
        embed_metadata=True,
        cookie_path="/path/to/cookies",
        selected_browser="chrome",
        speed_limit=1000000,
        retries=5,
        concurrent_downloads=2
    )

    assert download.quality == "1080p"
    assert download.format == "video"
    assert download.download_subtitles is True
    assert len(download.selected_subtitles) == 1
    assert download.selected_subtitles[0]["language_code"] == "en"


def test_service_type_enum():
    """Test ServiceType enum values."""
    assert ServiceType.YOUTUBE.value == "youtube"
    assert ServiceType.INSTAGRAM.value == "instagram"
    assert ServiceType.TWITTER.value == "twitter"
    assert ServiceType.PINTEREST.value == "pinterest"


def test_download_status_enum():
    """Test DownloadStatus enum values."""
    assert DownloadStatus.PENDING.value == "Pending"
    assert DownloadStatus.DOWNLOADING.value == "Downloading"
    assert DownloadStatus.COMPLETED.value == "Completed"
    assert DownloadStatus.FAILED.value == "Failed"