import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic.types import ToolUseBlock

from bazaar.events import event_cursor, replay_events
from bazaar.models import Agent, Task
from bazaar.orchestrator import Orchestrator, run_wave
from bazaar.payments import AmbiguousPayment
from bazaar.specialists import Intelligence


async def test_claude_receives_actual_persistable_tool_result():
    brain = Intelligence.__new__(Intelligence)
    brain.config = SimpleNamespace(claude_routing_model="routing", claude_synthesis_model="synthesis")
    tool = ToolUseBlock(
        type="tool_use",
        id="tool_actual_response_id",
        name="execute_plan",
        input={"tasks": [{"id": "one", "capability": "summarizer", "instruction": "Summarize facts"}]},
    )
    create = AsyncMock(
        side_effect=[
            SimpleNamespace(content=[tool]),
            SimpleNamespace(content=[SimpleNamespace(type="text", text="Verified summary")]),
        ]
    )
    brain.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    plan, messages = await brain.plan("Summarize these facts")
    # JSON round trip represents a durable checkpoint, not an in-memory tool runner.
    answer = await brain.synthesize(
        "Summarize these facts",
        {"one": {"output": "Facts", "verified": True}},
        messages=json.loads(json.dumps(messages)),
    )
    assert answer == "Verified summary" and plan.tasks[0].id == "one"
    sent = create.await_args.kwargs["messages"]
    assert sent[-1]["content"][0]["tool_use_id"] == tool.id
    assert sent[-1]["content"][0]["type"] == "tool_result"
    assert create.await_args.kwargs["model"] == "synthesis"


async def test_invalid_model_plan_never_reaches_execution():
    brain = Intelligence.__new__(Intelligence)
    brain.config = SimpleNamespace(claude_routing_model="routing")
    tool = ToolUseBlock(
        type="tool_use",
        id="invalid",
        name="execute_plan",
        input={
            "tasks": [{"id": "a", "capability": "summarizer", "instruction": "Summarize facts", "dependencies": ["a"]}]
        },
    )
    brain.client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(content=[tool])))
    )
    with pytest.raises(ValueError):
        await brain.plan("Summarize these facts")


def registered_agent():
    return Agent(
        id=1,
        owner="0x" + "1" * 40,
        pay_to="0x" + "2" * 40,
        price=1000,
        endpoint="https://agents.example/summary/run",
        capability="summarizer",
        reputation=8000,
        active=True,
    )


async def test_resume_reuses_payment_winner_and_mode_without_new_auction(monkeypatch):
    auction = AsyncMock()
    monkeypatch.setattr("bazaar.orchestrator.auction", auction)
    previous = {"agent_id": 1, "amount": 1000, "obligation": "bound", "mode": "x402"}
    store = SimpleNamespace(query=AsyncMock(return_value=previous), event=AsyncMock())
    buyer = SimpleNamespace(call=AsyncMock(return_value=({"output": "Recovered paid result"}, "receipt")))
    # A changed escrow threshold must not fund escrow for an already signed x402 obligation.
    orchestrator = Orchestrator(SimpleNamespace(escrow_threshold_usdc=Decimal("0.0001")), store, None, None, buyer)
    result, _, _, escrow = await orchestrator.paid(
        Task(id="one", capability="summarizer", instruction="Summarize facts"),
        {"instruction": "Summarize facts"},
        "run",
        [registered_agent()],
    )
    assert result["output"] == "Recovered paid result" and escrow is None
    auction.assert_not_awaited()
    assert len(buyer.call.await_args.kwargs["obligation"]) == 64


async def test_changed_price_or_missing_agent_requires_reconciliation(monkeypatch):
    auction = AsyncMock()
    monkeypatch.setattr("bazaar.orchestrator.auction", auction)
    store = SimpleNamespace(query=AsyncMock(return_value={"agent_id": 1, "amount": 1001, "obligation": "bound"}))
    orchestrator = Orchestrator(None, store, None, None, None)
    with pytest.raises(AmbiguousPayment):
        await orchestrator.paid(
            Task(id="one", capability="summarizer", instruction="Summarize facts"), {}, "run", [registered_agent()]
        )
    auction.assert_not_awaited()


async def test_ambiguous_task_cancels_and_drains_parallel_work():
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def pending():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def failed():
        await started.wait()
        raise AmbiguousPayment("Needs reconciliation")

    with pytest.raises(AmbiguousPayment):
        await run_wave([pending(), failed()])
    assert cancelled.is_set()


async def test_completed_event_replay_drains_multiple_pages_after_cursor():
    rows = [{"id": i, "type": "result", "data": {}} for i in range(1, 406)]

    async def query(sql, params, one=False):
        if "SELECT status" in sql:
            return {"status": "completed"}
        return [row for row in rows if row["id"] > params[1]][:200]

    store = SimpleNamespace(query=query)
    request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
    chunks = [chunk async for chunk in replay_events(store, "run", 4, request)]
    ids = [int(chunk.splitlines()[0].split(": ")[1]) for chunk in chunks]
    assert ids == list(range(5, 406))


@pytest.mark.parametrize("value", ["-1", "bad", str(2**63)])
def test_invalid_event_cursors_fail(value):
    with pytest.raises(ValueError):
        event_cursor(value)
