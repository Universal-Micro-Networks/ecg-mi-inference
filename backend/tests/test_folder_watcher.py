import time
from pathlib import Path

from app.folder_watcher import FolderWatcherService


def test_enqueue_skips_non_mfer(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MFER_WATCH_FOLDER", str(tmp_path))
    called: list[str] = []

    service = FolderWatcherService(importer_func=lambda p: called.append(p))
    service.enqueue_if_target(tmp_path / "sample.txt")

    assert called == []


def test_enqueue_processes_mfer_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MFER_WATCH_FOLDER", str(tmp_path))
    monkeypatch.setenv("MFER_WRITE_WAIT_INTERVAL", "0")
    monkeypatch.setenv("MFER_WRITE_TIMEOUT", "1")

    file_path = tmp_path / "sample.mwf"
    file_path.write_text("dummy")

    called: list[str] = []
    service = FolderWatcherService(importer_func=lambda p: called.append(p))
    service.enqueue_if_target(file_path)
    deadline = time.time() + 1
    while time.time() < deadline and not called:
        time.sleep(0.01)
    service.stop()

    assert len(called) == 1
