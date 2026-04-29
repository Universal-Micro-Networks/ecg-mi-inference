"""
Folder watcher service for new MFER files (.mwf/.MWF).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer as WatchdogObserver
from watchdog.observers.api import BaseObserver

from .file_importer import FileImporterError

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int env %s=%r. Use default=%d", name, raw, default)
        return default


def _is_mfer_file(path: Path) -> bool:
    return path.suffix.lower() == ".mwf"


def _resolve_dir_for_compare(raw: str, *, fallback: str) -> Path:
    p = Path(raw.strip() if raw else fallback).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _normalize_absolute_watch_path(p: Path) -> Path:
    """絶対パスを正規化。ネットワークドライブ等で resolve が失敗する場合は入力を優先する。"""
    try:
        return p.resolve(strict=False)
    except (OSError, RuntimeError) as e:
        logger.warning(
            "MFER_WATCH_FOLDER の resolve に失敗したため指定どおり使用します: %s (%s)",
            p,
            e,
        )
        return p


def _resolve_mfer_watch_folder(raw: str) -> Path | None:
    """
    MFER_WATCH_FOLDER を決定する。
    - 絶対パス: `~` 展開後に resolve（失敗時は指定パスのまま）。UNC（Windows \\\\server\\share\\...）や
      /Volumes/... のネットワークマウント、ドライブレター（D:\\...）を想定。
    - 相対パス: まず cwd 基準。無ければリポジトリルート基準（docker-compose.yml がある階層）。
      これにより `cd backend && uv run uvicorn` でも `develop/test_data` が使える。
    """
    s = raw.strip()
    if not s:
        return None
    p = Path(s).expanduser()
    if p.is_absolute():
        return _normalize_absolute_watch_path(p)

    cwd_hit = (Path.cwd() / p).resolve()
    if cwd_hit.exists():
        return cwd_hit

    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    if (repo_root / "docker-compose.yml").is_file():
        repo_hit = (repo_root / p).resolve()
        if repo_hit.exists():
            logger.info("MFER_WATCH_FOLDER resolved from repo root: %s -> %s", p, repo_hit)
            return repo_hit

    return cwd_hit


@dataclass
class WatcherStats:
    detected: int = 0
    success: int = 0
    failed: int = 0
    active_tasks: int = 0
    last_detected_at: float | None = None
    started: bool = False


class _MferEventHandler(FileSystemEventHandler):
    def __init__(self, service: FolderWatcherService) -> None:
        self._service = service

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = event.src_path
        path_str = os.fsdecode(src) if isinstance(src, bytes) else src
        self._service.enqueue_if_target(Path(path_str))


class FolderWatcherService:
    def __init__(self, importer_func: Callable[[str], None]) -> None:
        self.watch_folder = _resolve_mfer_watch_folder(os.getenv("MFER_WATCH_FOLDER", ""))
        self._processed_dir = _resolve_dir_for_compare(
            os.getenv("MFER_PROCESSED_FOLDER", ""),
            fallback="./processed",
        )
        self._error_dir = _resolve_dir_for_compare(
            os.getenv("MFER_ERROR_FOLDER", ""),
            fallback="./error",
        )
        self.recursive = _env_bool("MFER_WATCH_RECURSIVE", True)
        self.max_concurrent = _env_int("MFER_MAX_CONCURRENT", 5)
        self.write_wait_interval = _env_int("MFER_WRITE_WAIT_INTERVAL", 2)
        self.write_timeout = _env_int("MFER_WRITE_TIMEOUT", 60)
        self.shutdown_timeout = _env_int("MFER_SHUTDOWN_TIMEOUT", 30)
        self.tracking_limit = _env_int("MFER_TRACKING_LIMIT", 10000)
        self.stats_interval = _env_int("MFER_STATS_INTERVAL", 300)
        self._importer_func = importer_func

        self._observer: BaseObserver | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._stats = WatcherStats()
        self._tracked: OrderedDict[str, float] = OrderedDict()
        self._in_progress: set[str] = set()
        self._futures: set[Future] = set()
        self._lock = threading.Lock()
        self._stop_stats = threading.Event()
        self._stats_thread: threading.Thread | None = None
        self._bootstrap_stop = threading.Event()
        self._bootstrap_thread: threading.Thread | None = None
        self._observer_uses_polling = _env_bool("MFER_WATCH_USE_POLLING", False)

    def _create_observer(self) -> BaseObserver:
        """ネットワーク共有等で OS ネイティブ監視が不安定な場合は PollingObserver を選べる。"""
        if self._observer_uses_polling:
            from watchdog.observers.polling import PollingObserver

            interval = float(_env_int("MFER_WATCH_POLLING_INTERVAL_SEC", 1))
            logger.info(
                "folder-watcher: MFER_WATCH_USE_POLLING=1 のため PollingObserver を使用します（interval=%ss）",
                interval,
            )
            return PollingObserver(timeout=interval)
        return WatchdogObserver()

    def start(self) -> None:
        if self._stats.started:
            return
        if self._bootstrap_thread and self._bootstrap_thread.is_alive():
            return
        if self.watch_folder is None:
            logger.info("folder-watcher disabled: MFER_WATCH_FOLDER is empty")
            return

        # 監視パス待ちはメインスレッド（FastAPI lifespan）をブロックしないよう別スレッドで行う
        self._bootstrap_stop.clear()
        self._bootstrap_thread = threading.Thread(
            target=self._bootstrap_and_watch,
            name="folder-watcher-bootstrap",
            daemon=True,
        )
        self._bootstrap_thread.start()

    def _bootstrap_and_watch(self) -> None:
        if self.watch_folder is None:
            return
        try:
            while not self.watch_folder.exists():
                logger.error("Watch folder not found: %s. waiting...", self.watch_folder)
                if self._bootstrap_stop.wait(timeout=2):
                    logger.info("folder-watcher bootstrap aborted before folder was available")
                    return

            if self._bootstrap_stop.is_set():
                return

            with self._lock:
                if self._stats.started:
                    return

            if self._bootstrap_stop.is_set():
                return

            observer = self._create_observer()
            executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
            if self._bootstrap_stop.is_set():
                executor.shutdown(wait=False)
                return

            self._observer = observer
            self._executor = executor
            handler = _MferEventHandler(self)
            observer.schedule(handler, str(self.watch_folder), recursive=self.recursive)
            observer.start()

            self._enqueue_pre_existing_mfer_files()

            if self._bootstrap_stop.is_set():
                observer.stop()
                observer.join(timeout=self.shutdown_timeout)
                executor.shutdown(wait=False)
                self._observer = None
                self._executor = None
                return

            self._stats.started = True
            logger.info(
                "folder-watcher started: folder=%s recursive=%s",
                self.watch_folder,
                self.recursive,
            )

            self._stop_stats.clear()
            self._stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
            self._stats_thread.start()
        except Exception:
            logger.exception("folder-watcher bootstrap failed")

    def _enqueue_pre_existing_mfer_files(self) -> None:
        """起動時点で既に置いてある .mwf を取り込む（on_created は新規作成のみのため）。"""
        if self.watch_folder is None:
            return
        if not self.watch_folder.is_dir():
            return
        if self.recursive:
            candidates = self.watch_folder.rglob("*")
        else:
            candidates = self.watch_folder.iterdir()
        for path in candidates:
            if path.is_file() and _is_mfer_file(path):
                logger.info("folder-watcher: enqueue pre-existing MFER %s", path.name)
                self.enqueue_if_target(path)

    def stop(self) -> None:
        self._bootstrap_stop.set()
        if self._bootstrap_thread and self._bootstrap_thread.is_alive():
            self._bootstrap_thread.join(timeout=5)
        self._bootstrap_thread = None

        if self._stats.started:
            logger.info("folder-watcher stopping...")
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=self.shutdown_timeout)
        self._stop_stats.set()
        if self._stats_thread and self._stats_thread.is_alive():
            self._stats_thread.join(timeout=1)
        # Wait for running imports.
        deadline = time.time() + self.shutdown_timeout
        while time.time() < deadline:
            with self._lock:
                if not self._in_progress:
                    break
            time.sleep(0.1)
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        self._observer = None
        self._stats.started = False
        self._bootstrap_stop.clear()
        logger.info("folder-watcher stopped")

    def enqueue_if_target(self, path: Path) -> None:
        if not _is_mfer_file(path):
            logger.debug("ignore non-mfer file: %s", path.name)
            return
        if _is_under(path, self._processed_dir) or _is_under(path, self._error_dir):
            logger.debug("ignore mfer already moved to destination: %s", path)
            return

        abs_path = str(path.resolve())
        with self._lock:
            if abs_path in self._in_progress or abs_path in self._tracked:
                logger.debug("skip duplicated file: %s", path.name)
                return
            self._in_progress.add(abs_path)
            self._tracked[abs_path] = time.time()
            self._trim_tracking()
            self._stats.detected += 1
            self._stats.last_detected_at = time.time()
            self._stats.active_tasks = len(self._in_progress)
        logger.info("detected file: %s", path.name)

        if not self._executor:
            # Allow unit tests to enqueue without full start.
            self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        future = self._executor.submit(self._process_file, path)
        with self._lock:
            self._futures.add(future)
        future.add_done_callback(self._done_callback)

    def _process_file(self, path: Path) -> None:
        abs_path = str(path.resolve())
        try:
            if not self._wait_write_complete(path):
                logger.warning("skip file write-timeout: %s", path.name)
                with self._lock:
                    self._stats.failed += 1
                return
            self._importer_func(abs_path)
            logger.info("file-importer success: %s", path.name)
            with self._lock:
                self._stats.success += 1
        except FileImporterError as e:
            logger.warning("file-importer skipped: %s — %s", path.name, e)
            with self._lock:
                self._stats.failed += 1
        except Exception:
            logger.exception("file-importer failed: %s", path.name)
            with self._lock:
                self._stats.failed += 1
        finally:
            with self._lock:
                self._in_progress.discard(abs_path)
                self._stats.active_tasks = len(self._in_progress)

    def _wait_write_complete(self, path: Path) -> bool:
        timeout_at = time.time() + self.write_timeout
        prev_size = -1
        stable_for = 0
        while time.time() < timeout_at:
            if not path.exists():
                return False
            size = path.stat().st_size
            if size == prev_size:
                stable_for += self.write_wait_interval
            else:
                stable_for = 0
                prev_size = size
            if stable_for >= self.write_wait_interval:
                return True
            time.sleep(self.write_wait_interval)
        return False

    def _trim_tracking(self) -> None:
        while len(self._tracked) > self.tracking_limit:
            self._tracked.popitem(last=False)

    def _done_callback(self, future: Future) -> None:
        with self._lock:
            self._futures.discard(future)

    def _stats_loop(self) -> None:
        while not self._stop_stats.wait(self.stats_interval):
            s = self.snapshot()
            logger.info(
                "folder-watcher stats: detected=%d success=%d failed=%d active=%d",
                s["detected"],
                s["success"],
                s["failed"],
                s["active_tasks"],
            )

    def snapshot(self) -> dict:
        with self._lock:
            boot = self._bootstrap_thread is not None and self._bootstrap_thread.is_alive()
            return {
                "watching": self._stats.started,
                "bootstrap_pending": boot and not self._stats.started,
                "use_polling_observer": self._observer_uses_polling,
                "folder": str(self.watch_folder) if self.watch_folder is not None else "",
                "detected": self._stats.detected,
                "success": self._stats.success,
                "failed": self._stats.failed,
                "active_tasks": self._stats.active_tasks,
                "last_detected_at": self._stats.last_detected_at,
            }
