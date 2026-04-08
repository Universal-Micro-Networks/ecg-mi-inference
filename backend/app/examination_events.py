"""
診察一覧の SSE 用。file_importer 等の同期スレッドからメイン asyncio ループへ安全にイベントを届ける。
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_subscribers_lock = threading.Lock()
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_event_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    global _main_loop
    _main_loop = loop


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
    with _subscribers_lock:
        _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    with _subscribers_lock:
        _subscribers.discard(q)


def _broadcast_in_loop(payload: dict[str, Any]) -> None:
    with _subscribers_lock:
        subs = list(_subscribers)
    for q in subs:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("SSE: subscriber queue full, event dropped")
        except Exception:
            logger.exception("SSE: broadcast to subscriber failed")


def notify_examinations_changed(
    *,
    examination_id: str | None = None,
    reason: str = "import",
) -> None:
    """同期スレッド（folder watcher / importer）から呼び出す。"""
    payload: dict[str, Any] = {"type": "examinations_changed", "reason": reason}
    if examination_id:
        payload["examination_id"] = examination_id
    loop = _main_loop
    if loop is None or not loop.is_running():
        return
    try:
        loop.call_soon_threadsafe(_broadcast_in_loop, payload)
    except RuntimeError:
        logger.debug("SSE: broadcast skipped (event loop not accepting callbacks)")
