import json
import logging
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from upstash_redis.asyncio import Redis

from .config import Settings


class Store:
    def __init__(self, config: Settings):
        self.url = config.database_url.get_secret_value()
        self.redis = Redis(url=config.upstash_redis_rest_url, token=config.upstash_redis_rest_token.get_secret_value())

    @asynccontextmanager
    async def connection(self):
        async with await AsyncConnection.connect(self.url, row_factory=dict_row, connect_timeout=8) as connection:
            yield connection

    async def query(self, sql, params=(), one=False):
        async with self.connection() as c:
            cursor = await c.execute(sql, params)
            if cursor.description:
                return await cursor.fetchone() if one else await cursor.fetchall()

    async def event(self, run_id, kind, data, *, status=None, answer=None):
        async with self.connection() as connection:
            # Serialize allocation and commit per run. Otherwise a later sequence
            # ID can commit first and a resumable cursor can skip an earlier event.
            await connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (str(run_id),))
            if status:
                await connection.execute(
                    "UPDATE runs SET status=%s,answer=COALESCE(%s,answer),updated_at=now() WHERE id=%s",
                    (status, answer, run_id),
                )
            cursor = await connection.execute(
                "INSERT INTO events(run_id,type,data) VALUES(%s,%s,%s) RETURNING *", (run_id, kind, Jsonb(data))
            )
            row = await cursor.fetchone()
        logging.getLogger("bazaar").info(json.dumps({"run_id": str(run_id), "event": kind, "event_id": row["id"]}))
        # Postgres is authoritative. Notification outage cannot undo a persisted event.
        try:
            await self.redis.publish(f"run:{run_id}", json.dumps({"id": row["id"]}))
        except Exception:
            pass
        return row

    async def reserve(self, payment_id, run_id, agent_id, amount, agent_cap, *, obligation, mode="x402"):
        if mode not in ("x402", "escrow") or amount <= 0:
            raise ValueError("Invalid payment mode or amount")
        async with self.connection() as c:
            # Lock session first: serializes concurrent DAG budget reservations.
            cursor = await c.execute(
                "SELECT s.* FROM sessions s JOIN runs r ON r.session_id=s.id WHERE r.id=%s FOR UPDATE OF s", (run_id,)
            )
            session = await cursor.fetchone()
            if not session:
                raise ValueError("Session does not exist")
            cursor = await c.execute("SELECT * FROM payments WHERE id=%s", (payment_id,))
            existing = await cursor.fetchone()
            if existing:
                if (
                    str(existing["run_id"]) != str(run_id)
                    or existing["agent_id"] != agent_id
                    or existing["amount"] != amount
                    or existing.get("obligation") != obligation
                    or existing["mode"] != mode
                ):
                    raise ValueError("Payment binding changed")
                return existing
            cursor = await c.execute(
                "SELECT id FROM payments WHERE obligation=%s AND status<>'cancelled'", (obligation,)
            )
            if await cursor.fetchone():
                raise ValueError("This obligation already has an active payment")
            cursor = await c.execute(
                "SELECT COALESCE(sum(p.amount),0) AS total FROM payments p JOIN runs r ON r.id=p.run_id WHERE r.session_id=%s AND p.agent_id=%s AND p.status<>'cancelled'",
                (session["id"], agent_id),
            )
            used = (await cursor.fetchone())["total"]
            if used + amount > agent_cap:
                raise ValueError("Per-agent session spend cap exceeded")
            cursor = await c.execute(
                "UPDATE sessions SET reserved=reserved+%s WHERE id=%s AND spent+reserved+%s<=cap AND expires_at>now() RETURNING id",
                (amount, session["id"], amount),
            )
            if not await cursor.fetchone():
                raise ValueError("Session expired or budget exceeded")
            cursor = await c.execute(
                "INSERT INTO payments(id,run_id,agent_id,amount,obligation,mode) VALUES(%s,%s,%s,%s,%s,%s) RETURNING *",
                (payment_id, run_id, agent_id, amount, obligation, mode),
            )
            return await cursor.fetchone()

    async def finish_payment(self, payment_id, status, tx=None):
        if status not in ("settled", "cancelled"):
            raise ValueError("Invalid payment terminal status")
        async with self.connection() as c:
            cursor = await c.execute(
                "SELECT p.*,r.session_id FROM payments p JOIN runs r ON p.run_id=r.id WHERE p.id=%s FOR UPDATE OF p",
                (payment_id,),
            )
            payment = await cursor.fetchone()
            if not payment or payment["status"] in ("settled", "cancelled"):
                return
            await c.execute(
                "UPDATE payments SET status=%s,tx_hash=%s,updated_at=now() WHERE id=%s", (status, tx, payment_id)
            )
            await c.execute(
                "UPDATE sessions SET reserved=reserved-%s,spent=spent+%s WHERE id=%s",
                (payment["amount"], payment["amount"] if status == "settled" else 0, payment["session_id"]),
            )

    async def rate_limit(self, key, limit=20, seconds=60):
        count = await self.redis.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
            [key],
            [seconds],
        )
        return int(count) <= limit
