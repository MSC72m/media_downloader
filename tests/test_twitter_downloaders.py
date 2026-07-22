from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from src.core.config import AppConfig
from src.services.twitter.downloader import TwitterDownloader
from src.services.twitter.spaces import TwitterSpacesDownloader, _SpaceUnavailableError


class _TweetResponse:
    def __init__(self, payload: dict | None = None, *, invalid_json: bool = False) -> None:
        self.headers = {"content-type": "application/json"}
        self.text = ""
        self._payload = payload or {}
        self._invalid_json = invalid_json

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        if self._invalid_json:
            raise ValueError("invalid JSON")
        return self._payload


def test_tweet_scrape_continues_after_transport_and_json_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloader = TwitterDownloader(config=AppConfig())
    responses: list[object] = [
        requests.ConnectionError("first endpoint unavailable"),
        _TweetResponse(invalid_json=True),
        _TweetResponse({"tweet": {"text": "hello", "media": {"all": []}}}),
    ]
    calls: list[str] = []

    def fake_get(endpoint: str, **_kwargs: object) -> _TweetResponse:
        calls.append(endpoint)
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, _TweetResponse)
        return result

    monkeypatch.setattr("src.services.twitter.downloader.requests.get", fake_get)

    result = downloader._scrape_tweet_data("123", "author")

    assert result is not None
    assert result["text"] == "hello"
    assert len(calls) == 3


def test_unavailable_space_reports_one_actionable_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    error_handler = MagicMock()
    downloader = TwitterSpacesDownloader(error_handler=error_handler, config=AppConfig())
    monkeypatch.setattr(downloader, "_activate_guest_token", lambda: "guest")

    def unavailable(_space_id: str) -> dict:
        raise _SpaceUnavailableError(
            "Space is unavailable. It may be private, deleted, or have replay disabled."
        )

    monkeypatch.setattr(downloader, "_fetch_space_data", unavailable)

    assert (
        downloader.download(
            "https://x.com/i/spaces/1mnGeRdbdQXGX",
            str(tmp_path / "space"),
        )
        is False
    )
    error_handler.handle_service_failure.assert_called_once()
    error_handler.handle_exception.assert_not_called()


def test_spaces_ffmpeg_uses_central_path_and_finite_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = AppConfig()
    config.twitter.space_download_timeout_seconds = 7
    downloader = TwitterSpacesDownloader(config=config)
    process = MagicMock()
    process.communicate.side_effect = [subprocess.TimeoutExpired("ffmpeg", 7), ("", "stopped")]
    process.returncode = None

    monkeypatch.setattr("src.services.twitter.spaces.get_ffmpeg_path", lambda: "/opt/ffmpeg")
    popen = MagicMock(return_value=process)
    monkeypatch.setattr("src.services.twitter.spaces.subprocess.Popen", popen)

    with pytest.raises(RuntimeError, match="configured Twitter Spaces download timeout"):
        downloader._download_hls(
            "https://media.example/space.m3u8",
            str(tmp_path / "space.m4a"),
        )

    assert popen.call_args.args[0][0] == "/opt/ffmpeg"
    process.communicate.assert_any_call(timeout=7)
    process.kill.assert_called_once_with()
