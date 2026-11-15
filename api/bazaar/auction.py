import asyncio

import httpx

from .models import Bid
from .security import allowed_endpoint


def rank_bids(bids, agents):
    by_id = {a.id: a for a in agents}
    if not bids:
        return []
    minimum = min(b.price for b in bids)
    for bid in bids:
        reputation = by_id[bid.agent_id].reputation / 10000
        bid.score = round(
            0.45 * reputation + 0.35 * minimum / bid.price + 0.15 / bid.eta_seconds + 0.05 * bid.confidence, 6
        )
    return sorted(bids, key=lambda b: (-b.score, b.price, b.agent_id))


async def auction(task, agents, store, config, run_id):
    eligible = [
        a
        for a in agents
        if a.active and a.capability == task.capability and a.price <= int(config.max_agent_usdc * 1_000_000)
    ]

    async def ask(agent):
        try:
            if await store.redis.get(f"circuit:{agent.id}"):
                raise ValueError("Circuit open")
            await allowed_endpoint(agent.endpoint, config.agent_allowed_hosts)
            async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                response = await client.post(
                    agent.endpoint.removesuffix("/run") + "/bid", json={"instruction": task.instruction}
                )
                response.raise_for_status()
                bid = Bid.model_validate(response.json() | {"agent_id": agent.id})
            if bid.price != agent.price:
                raise ValueError("Bid price differs from registered price")
            await store.event(run_id, "bid", {"task_id": task.id, **bid.model_dump()})
            return bid
        except Exception as error:
            await store.event(
                run_id, "bid", {"task_id": task.id, "agent_id": agent.id, "rejected": type(error).__name__}
            )
            return None

    bids = await asyncio.gather(*(ask(a) for a in eligible))
    ranked = rank_bids([b for b in bids if b], eligible)
    for index, bid in enumerate(ranked):
        await store.event(
            run_id, "bid", {"task_id": task.id, **bid.model_dump(), "rank": index + 1, "winner": index == 0}
        )
    return ranked
