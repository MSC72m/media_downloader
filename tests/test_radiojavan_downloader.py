from __future__ import annotations

import sys

import pytest

sys.modules.pop("requests", None)
import requests  # noqa: E402

from src.services.radiojavan.downloader import RadioJavanDownloader  # noqa: E402


class _FakeResponse:
    def __init__(self, text: str, headers: dict[str, str], status_code: int = 200):
        self.text = text
        self.headers = headers
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def test_downloader_stops_host_lookup_on_challenge(monkeypatch: pytest.MonkeyPatch) -> None:
    downloader = RadioJavanDownloader()

    def fake_request_context(force_refresh: bool = False) -> tuple[dict[str, str], None]:
        _ = force_refresh
        return {"User-Agent": "ua"}, None

    def fake_post(*_args: object, **_kwargs: object) -> _FakeResponse:
        return _FakeResponse("<html>window._cf_chl_opt=1</html>", {"cf-mitigated": "challenge"}, 200)

    monkeypatch.setattr(downloader, "_request_context", fake_request_context)
    monkeypatch.setattr("src.services.radiojavan.downloader.requests.post", fake_post)

    host = downloader._fetch_host_from_endpoint(
        "https://www.radiojavan.com/mp3s/mp3_host",
        "shadmehr-asteni",
    )

    assert host is None


def test_resolve_direct_media_url_from_play_search(monkeypatch: pytest.MonkeyPatch) -> None:
    downloader = RadioJavanDownloader()
    expected = "https://host2.media-rj.com/media/mp3/mp3-256/152298-435d6d1b99ff0ba.mp3"
    html = (
        '{"songs":[{"id":152298,'
        f'"link":"{expected}",'
        '"permlink":"Shadmehr-Aghili-Mamnoon"}]}'
    )

    def fake_get(*_args: object, **_kwargs: object) -> _FakeResponse:
        return _FakeResponse(html, {}, 200)

    monkeypatch.setattr("src.services.radiojavan.downloader.requests.get", fake_get)

    resolved = downloader._resolve_direct_media_url_from_play(
        media_name="shadmehr-aghili-mamnoon",
        media_type="mp3",
    )

    assert resolved == expected
