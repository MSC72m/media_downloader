from __future__ import annotations

import sys
from typing import Self

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


def test_feature_alias_selects_reported_broken_angel_result() -> None:
    expected = "https://host2.media-rj.com/media/mp3/arash-broken-angel.mp3"

    assert (
        RadioJavanDownloader._select_best_media_link(
            "Arash-Broken-Angel-feat-Helena",
            [("Arash-Broken-Angel-(Ft-Helena)", expected)],
        )
        == expected
    )


def test_construct_download_url_obeys_probe_budget_and_rejects_guesses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloader = RadioJavanDownloader()
    downloader.max_candidate_probes = 3
    probes: list[str] = []

    monkeypatch.setattr(downloader, "_resolve_direct_media_url_from_play", lambda *_args: None)
    monkeypatch.setattr(downloader, "_candidate_hosts", lambda *_args: ["https://one", "https://two"])
    monkeypatch.setattr(
        downloader,
        "_validate_url",
        lambda candidate: probes.append(candidate) or False,
    )

    result = downloader._construct_download_url(
        "https://www.radiojavan.com/mp3s/mp3/example-track"
    )

    assert result is None
    assert len(probes) == 3


def test_range_validation_does_not_materialize_streamed_media_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloader = RadioJavanDownloader()

    class StreamResponse:
        status_code = 206

        def __init__(self) -> None:
            self.headers = {"content-type": "audio/mpeg"}

        @property
        def text(self) -> str:
            raise AssertionError("streamed media body must not be decoded")

        def raise_for_status(self) -> None:
            return None

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(
        "src.services.radiojavan.downloader.requests.get",
        lambda *_args, **_kwargs: StreamResponse(),
    )

    assert downloader._validate_with_range_get("https://media.example/song.mp3") is True
