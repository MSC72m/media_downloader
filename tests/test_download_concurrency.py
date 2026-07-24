from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

from src.core.config import AppConfig
from src.core.models import Download
from src.handlers.download_handler import DownloadHandler


def test_download_handler_runs_two_workers_concurrently(tmp_path: Path) -> None:
    config = AppConfig()
    config.downloads.max_concurrent_downloads = 2
    file_service = MagicMock()
    file_service.clean_filename.side_effect = lambda value: value
    handler = DownloadHandler(
        service_factory=MagicMock(),
        file_service=file_service,
        ui_state=MagicMock(),
        cookie_handler=MagicMock(),
        config=config,
    )

    downloads = [
        Download(url=f"https://example.com/{index}", name=f"item-{index}")
        for index in range(3)
    ]
    lock = threading.Lock()
    release_workers = threading.Event()
    two_workers_active = threading.Event()
    all_done = threading.Event()
    active = 0
    max_active = 0
    started: list[str] = []

    def fake_worker(
        download: Download,
        _download_dir: str,
        _progress_callback: object,
    ) -> None:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            started.append(download.name)
            if active == 2:
                two_workers_active.set()
        release_workers.wait(timeout=2)
        with lock:
            active -= 1

    handler._download_worker = fake_worker  # type: ignore[method-assign]
    handler.start_downloads(
        downloads,
        str(tmp_path),
        completion_callback=lambda _success, _message: all_done.set(),
    )

    assert two_workers_active.wait(timeout=1), "two workers never overlapped"
    with lock:
        assert max_active == 2
        assert len(started) == 2

    release_workers.set()
    assert all_done.wait(timeout=2), "download processor did not finish"
    assert sorted(started) == ["item-0", "item-1", "item-2"]
