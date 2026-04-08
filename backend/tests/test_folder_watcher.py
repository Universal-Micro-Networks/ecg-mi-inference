import logging
import re
import time
from pathlib import Path

from app.folder_watcher import FolderWatcherService, _resolve_mfer_watch_folder


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


def test_resolve_absolute_watch_folder(tmp_path: Path, monkeypatch):
    watch = tmp_path / "abs_watch"
    watch.mkdir()
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_mfer_watch_folder(str(watch))
    assert resolved == watch.resolve()


def test_snapshot_reports_use_polling_observer(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MFER_WATCH_FOLDER", str(tmp_path))
    monkeypatch.setenv("MFER_WATCH_USE_POLLING", "1")
    svc = FolderWatcherService(importer_func=lambda p: None)
    assert svc.snapshot()["use_polling_observer"] is True


def test_snapshot_default_no_polling_observer(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MFER_WATCH_FOLDER", str(tmp_path))
    monkeypatch.delenv("MFER_WATCH_USE_POLLING", raising=False)
    svc = FolderWatcherService(importer_func=lambda p: None)
    assert svc.snapshot()["use_polling_observer"] is False


def test_bootstrap_waits_until_watch_folder_exists_polling_observer(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    """監視パスが後から出現するまでブートストラップが待機し、PollingObserver で起動する。"""
    watch_dir = tmp_path / "incoming"
    monkeypatch.setenv("MFER_WATCH_FOLDER", str(watch_dir))
    monkeypatch.setenv("MFER_WATCH_USE_POLLING", "1")
    monkeypatch.setenv("MFER_WATCH_POLLING_INTERVAL_SEC", "1")
    monkeypatch.setenv("MFER_STATS_INTERVAL", "600")
    monkeypatch.setenv("MFER_WRITE_WAIT_INTERVAL", "0")
    monkeypatch.setenv("MFER_WRITE_TIMEOUT", "2")
    caplog.set_level(logging.ERROR, logger="app.folder_watcher")

    imported: list[str] = []
    svc = FolderWatcherService(importer_func=lambda p: imported.append(p))
    svc.start()
    time.sleep(0.15)
    snap = svc.snapshot()
    assert snap["bootstrap_pending"] is True
    assert snap["watching"] is False
    assert snap["use_polling_observer"] is True
    assert any("Watch folder not found" in r.message for r in caplog.records)

    watch_dir.mkdir()
    (watch_dir / "preexist.mwf").write_bytes(b"x")

    deadline = time.time() + 8
    while time.time() < deadline and not svc.snapshot()["watching"]:
        time.sleep(0.05)
    assert svc.snapshot()["watching"] is True

    deadline = time.time() + 5
    while time.time() < deadline and not imported:
        time.sleep(0.05)
    svc.stop()
    assert len(imported) == 1


def test_periodic_stats_log_matches_snapshot_counters(tmp_path: Path, monkeypatch, caplog) -> None:
    """_stats_loop の INFO ログが snapshot の detected/success/failed/active と一致する。"""
    monkeypatch.setenv("MFER_WATCH_FOLDER", str(tmp_path))
    monkeypatch.delenv("MFER_WATCH_USE_POLLING", raising=False)
    monkeypatch.setenv("MFER_STATS_INTERVAL", "1")
    monkeypatch.setenv("MFER_WRITE_WAIT_INTERVAL", "0")
    monkeypatch.setenv("MFER_WRITE_TIMEOUT", "3")
    caplog.set_level(logging.INFO, logger="app.folder_watcher")

    imported: list[str] = []
    svc = FolderWatcherService(importer_func=lambda p: imported.append(p))
    svc.start()
    deadline = time.time() + 8
    while time.time() < deadline and not svc.snapshot()["watching"]:
        time.sleep(0.05)
    assert svc.snapshot()["watching"] is True

    mwf = tmp_path / "stats_test.mwf"
    mwf.write_bytes(b"data")
    svc.enqueue_if_target(mwf)
    deadline = time.time() + 5
    while time.time() < deadline and len(imported) < 1:
        time.sleep(0.05)

    # 次の統計ログ周期まで待ち、直近ログと snapshot を突き合わせる
    time.sleep(2.2)
    stats_msgs = [
        r.message for r in caplog.records if r.message.startswith("folder-watcher stats:")
    ]
    assert stats_msgs, f"expected stats log on interval; got:\n{caplog.text}"
    last = stats_msgs[-1]
    m = re.search(
        r"detected=(\d+) success=(\d+) failed=(\d+) active=(\d+)",
        last,
    )
    assert m, last
    det, succ, fail, act = map(int, m.groups())
    snap = svc.snapshot()
    svc.stop()
    assert (det, succ, fail, act) == (
        snap["detected"],
        snap["success"],
        snap["failed"],
        snap["active_tasks"],
    )
    assert det >= 1 and succ >= 1 and fail == 0
