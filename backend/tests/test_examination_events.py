"""examination_events: thread-safe broadcast hook."""

import asyncio

import pytest

from app import examination_events


def test_notify_no_crash_when_loop_unset() -> None:
    examination_events.set_main_event_loop(None)
    examination_events.notify_examinations_changed(examination_id="e1", reason="import")


@pytest.mark.asyncio
async def test_subscriber_receives_broadcast() -> None:
    loop = asyncio.get_running_loop()
    examination_events.set_main_event_loop(loop)
    q = examination_events.subscribe()
    try:
        examination_events.notify_examinations_changed(examination_id="abc", reason="import")
        await asyncio.sleep(0)
        msg = await asyncio.wait_for(q.get(), timeout=1.0)
        assert msg["type"] == "examinations_changed"
        assert msg["examination_id"] == "abc"
        assert msg["reason"] == "import"
    finally:
        examination_events.unsubscribe(q)
        examination_events.set_main_event_loop(None)


@pytest.mark.asyncio
async def test_notify_examinations_changed_threadsafe_from_other_thread() -> None:
    loop = asyncio.get_running_loop()
    examination_events.set_main_event_loop(loop)
    q = examination_events.subscribe()
    try:

        def from_thread() -> None:
            examination_events.notify_examinations_changed(examination_id="t2", reason="import")

        await asyncio.to_thread(from_thread)
        msg = await asyncio.wait_for(q.get(), timeout=2.0)
        assert msg["examination_id"] == "t2"
    finally:
        examination_events.unsubscribe(q)
        examination_events.set_main_event_loop(None)
