"""Postgres replay works independently of execution and never starts paid work."""

import asyncio
import json
from time import monotonic

from fastapi.encoders import jsonable_encoder


def event_cursor(value):
    cursor = int(value)
    if not 0 <= cursor <= 9223372036854775807:
        raise ValueError("Invalid event cursor")
    return cursor


async def replay_events(store, run_id, cursor, request, *, duration=230):
    deadline = monotonic() + duration
    while monotonic() < deadline and not await request.is_disconnected():
        # Read status first so a concurrent terminal write cannot make us stop
        # before its final event has been read on the next iteration.
        state = await store.query("SELECT status FROM runs WHERE id=%s", (run_id,), one=True)
        events = await store.query(
            "SELECT * FROM events WHERE run_id=%s AND id>%s ORDER BY id LIMIT 200", (run_id, cursor)
        )
        for event in events:
            cursor = event["id"]
            yield f"id: {cursor}\nevent: {event['type']}\ndata: {json.dumps(jsonable_encoder(event))}\n\n"
        if state and state["status"] in ("completed", "partial", "paused") and not events:
            return
        if not events:
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.6)
