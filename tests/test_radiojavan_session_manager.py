from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.modules.pop("requests", None)
import requests  # noqa: E402

from src.core.config import get_config  # noqa: E402
from src.services.cookies import RadioJavanSessionManager  # noqa: E402
from src.services.radiojavan.downloader import RadioJavanDownloader  # noqa: E402


class _FakeResponse:
    def __init__(self, text: str, headers: dict[str, str], status_code: int = 200):
        self.text = text
        self.headers = headers
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_challenge_detection() -> None:
    assert RadioJavanSessionManager.is_challenge_response("anything", "challenge", 200) is True
    assert (
        RadioJavanSessionManager.is_challenge_response(
            "<html>window._cf_chl_opt=1</html>",
            None,
            403,
        )
        is True
    )
    assert RadioJavanSessionManager.is_challenge_response('{"host":"rj.app"}', None, 200) is False


def test_get_request_context_from_saved_session(tmp_path: Path) -> None:
    config = get_config()
    manager = RadioJavanSessionManager(storage_dir=tmp_path, config=config)
    manager.state_file = tmp_path / "state.json"
    manager.session_file = tmp_path / "session.json"

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    _write_json(
        manager.state_file,
        {
            "is_valid": True,
            "is_generating": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": future,
            "cookie_count": 1,
            "error_message": None,
        },
    )
    _write_json(
        manager.session_file,
        {
            "headers": {"User-Agent": "test-agent"},
            "cookies": [
                {
                    "name": "cf_clearance",
                    "value": "abc",
                    "domain": ".radiojavan.com",
                    "path": "/",
                }
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": future,
        },
    )

    context = manager.get_request_context()
    assert context is not None
    headers, cookie_jar = context
    assert headers.get("User-Agent") == "test-agent"
    assert cookie_jar.get("cf_clearance") == "abc"


def test_retry_cooldown_skips_regeneration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = get_config()
    manager = RadioJavanSessionManager(storage_dir=tmp_path, config=config)
    manager.state_file = tmp_path / "state.json"
    manager.session_file = tmp_path / "session.json"

    next_retry = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    _write_json(
        manager.state_file,
        {
            "is_valid": False,
            "is_generating": False,
            "generated_at": None,
            "expires_at": None,
            "next_retry_at": next_retry,
            "cookie_count": 0,
            "error_message": "Previous failure",
        },
    )

    generate_calls = {"count": 0}

    def fake_generate() -> dict[str, str | bool | int | None]:
        generate_calls["count"] += 1
        return manager._invalid_state("should-not-run")

    monkeypatch.setattr(manager, "_run_generate_session", fake_generate)

    manager.initialize()
    assert manager.get_request_context() is None
    assert manager.get_request_context(force_refresh=True) is None
    assert generate_calls["count"] == 0


def test_downloader_stops_host_lookup_on_challenge(monkeypatch: pytest.MonkeyPatch) -> None:
    downloader = RadioJavanDownloader()

    def fake_request_context(force_refresh: bool = False):
        _ = force_refresh
        return {"User-Agent": "ua"}, None

    def fake_post(*_args, **_kwargs):
        return _FakeResponse("<html>window._cf_chl_opt=1</html>", {"cf-mitigated": "challenge"}, 200)

    monkeypatch.setattr(downloader, "_request_context", fake_request_context)
    monkeypatch.setattr("src.services.radiojavan.downloader.requests.post", fake_post)

    host = downloader._fetch_host_from_endpoint(
        "https://www.radiojavan.com/mp3s/mp3_host",
        "shadmehr-asteni",
    )

    assert host is None


def test_session_manager_refresh_inside_running_event_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = get_config()
    manager = RadioJavanSessionManager(storage_dir=tmp_path, config=config)
    manager.state_file = tmp_path / "state.json"
    manager.session_file = tmp_path / "session.json"

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    async def fake_generate() -> dict[str, str | bool | int | None]:
        _write_json(
            manager.session_file,
            {
                "headers": {"User-Agent": "ua"},
                "cookies": [
                    {
                        "name": "cf_clearance",
                        "value": "token",
                        "domain": ".radiojavan.com",
                        "path": "/",
                    }
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": future,
            },
        )
        return {
            "is_valid": True,
            "is_generating": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": future,
            "cookie_count": 1,
            "error_message": None,
        }

    monkeypatch.setattr(manager, "_generate_session", fake_generate)

    async def run_refresh() -> bool:
        return manager.refresh_session()

    assert asyncio.run(run_refresh()) is True


def test_resolve_direct_media_url_from_play_search(monkeypatch: pytest.MonkeyPatch) -> None:
    downloader = RadioJavanDownloader()
    expected = "https://host2.media-rj.com/media/mp3/mp3-256/152298-435d6d1b99ff0ba.mp3"
    html = (
        '{"songs":[{"id":152298,'
        f'"link":"{expected}",'
        '"permlink":"Shadmehr-Aghili-Mamnoon"}]}'
    )

    def fake_get(*_args, **_kwargs):
        return _FakeResponse(html, {}, 200)

    monkeypatch.setattr("src.services.radiojavan.downloader.requests.get", fake_get)

    resolved = downloader._resolve_direct_media_url_from_play(
        media_name="shadmehr-aghili-mamnoon",
        media_type="mp3",
    )

    assert resolved == expected
