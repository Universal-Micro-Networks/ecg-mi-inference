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
        self.watch_folder = Path(os.getenv("MFER_WATCH_FOLDER", "")).expanduser()
        self.recursive = _env_bool("MFER_WATCH_RECURSIVE", True)
        self.max_concurrent = _env_int("MFER_MAX_CONCURRENT", 5)
        self.write_wait_interval = _env_int("MFER_WRITE_WAIT_INTERVAL", 2)
        self.write_timeout = _env_int("MFER_WRITE_TIMEOUT", 60)
        self.shutdown_timeout = _env_int("MFER_SHUTDOWN_TIMEOUT", 30)
        self.tracking_limit = _env_int("MFER_TRACKING_LIMIT", 10000)
        self.stats_interval = _env_int("MFER_STATS_INTERVAL", 300)
        self._importer_func = importer_func

        # watchdog 型スタブ上 Observer が変数扱いになるため
        self._observer: WatchdogObserver | None = None  # pyright: ignore[reportInvalidTypeForm]
        self._executor: ThreadPoolExecutor | None = None
        self._stats = WatcherStats()
        self._tracked: OrderedDict[str, float] = OrderedDict()
        self._in_progress: set[str] = set()
        self._futures: set[Future] = set()
        self._lock = threading.Lock()
        self._stop_stats = threading.Event()
        self._stats_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._stats.started:
            return
        if not self.watch_folder:
            logger.info("folder-watcher disabled: MFER_WATCH_FOLDER is empty")
            return

        # If folder does not exist, poll until available.
        while not self.watch_folder.exists():
            logger.error("Watch folder not found: %s. waiting...", self.watch_folder)
            time.sleep(2)

        observer = WatchdogObserver()
        executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self._observer = observer
        self._executor = executor
        handler = _MferEventHandler(self)
        observer.schedule(handler, str(self.watch_folder), recursive=self.recursive)
        observer.start()
        self._stats.started = True
        logger.info(
            "folder-watcher started: folder=%s recursive=%s", self.watch_folder, self.recursive
        )

        self._stop_stats.clear()
        self._stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        self._stats_thread.start()

    def stop(self) -> None:
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
        logger.info("folder-watcher stopped")

    def enqueue_if_target(self, path: Path) -> None:
        if not _is_mfer_file(path):
            logger.debug("ignore non-mfer file: %s", path.name)
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
            return {
                "watching": self._stats.started,
                "folder": str(self.watch_folder),
                "detected": self._stats.detected,
                "success": self._stats.success,
                "failed": self._stats.failed,
                "active_tasks": self._stats.active_tasks,
                "last_detected_at": self._stats.last_detected_at,
            }
