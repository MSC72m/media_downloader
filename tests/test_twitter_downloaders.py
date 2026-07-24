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


class _SpaceResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 400

    def raise_for_status(self) -> None:
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_space_metadata_uses_current_operation_and_falls_back_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloader = TwitterSpacesDownloader(config=AppConfig())
    downloader._guest_token = "guest"
    metadata = {
        "title": "Replay title",
        "state": "Ended",
        "is_space_available_for_replay": True,
        "media_key": "28_123",
    }
    responses = [
        _SpaceResponse({"data": {"audioSpace": {}}}),
        _SpaceResponse({"data": {"audioSpace": {"metadata": metadata}}}),
    ]
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_get(url: str, **kwargs: object) -> _SpaceResponse:
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr("src.services.twitter.spaces.requests.get", fake_get)

    result = downloader._fetch_space_data("1OwxWwQOPlNxQ")

    assert result["metadata"] == metadata
    assert "xpwpkJD3FetGBaSq7zH4Lw" in calls[0][0]
    assert "kZ9wfR8EBtiP0As3sFFrBA" in calls[1][0]
    params = calls[0][1]["params"]
    assert isinstance(params, dict)
    assert '"isMetatagsQuery":true' in str(params["variables"])


def test_space_replay_prefers_no_redirect_url_and_current_stream_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloader = TwitterSpacesDownloader(config=AppConfig())
    downloader._guest_token = "guest"
    response = _SpaceResponse(
        {
            "source": {
                "location": "https://redirect.example/replay.m3u8",
                "noRedirectPlaybackUrl": "https://cdn.example/replay.m3u8",
            }
        }
    )
    get = MagicMock(return_value=response)
    monkeypatch.setattr("src.services.twitter.spaces.requests.get", get)

    assert downloader._fetch_replay_url("28_123") == "https://cdn.example/replay.m3u8"
    assert get.call_args.kwargs["params"] == {
        "client": "web",
        "use_syndication_guest_id": "false",
        "cookie_set_host": "x.com",
    }


def test_space_title_supports_current_creator_core_schema() -> None:
    metadata = {
        "title": "Current Space",
        "creator_results": {
            "result": {"core": {"name": "Current Creator", "screen_name": "creator"}}
        },
    }

    assert (
        TwitterSpacesDownloader._format_title(metadata)
        == "Current Creator - Current Space"
    )
