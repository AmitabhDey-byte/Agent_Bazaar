from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from x402.http.utils import decode_payment_required_header, encode_payment_signature_header
from x402.schemas import PaymentPayload, SettleResponse, VerifyResponse

from bazaar.payments import PaymentGate, requirements


class MemoryStore:
    def __init__(self):
        self.rows = {}

    async def query(self, sql, params=(), one=False):
        if sql.startswith("SELECT"):
            return self.rows.get(params[0])
        if sql.startswith("INSERT"):
            key, binding = params
            if key in self.rows:
                return None
            self.rows[key] = {"id": key, "binding": binding, "status": "executing", "result": None, "receipt": None}
            return {"id": key}
        if "status='settling'" in sql:
            self.rows[params[1]].update(status="settling", result=params[0].obj)
        if "status='settled'" in sql:
            self.rows[params[1]].update(status="settled", receipt=params[0].obj)


@pytest.fixture
def paid_app(monkeypatch):
    app = FastAPI()
    config = SimpleNamespace(
        usdc_address="0x" + "1" * 40,
        agent_pay_to="0x" + "2" * 40,
        api_public_url="https://agents.example",
        facilitator_url="https://facilitator.example",
    )
    app.state.config = config
    app.state.store = MemoryStore()
    app.state.calls = 0
    fake = SimpleNamespace(
        verify=AsyncMock(return_value=VerifyResponse(is_valid=True)),
        settle=AsyncMock(
            return_value=SettleResponse(success=True, transaction="0x" + "3" * 64, network="eip155:84532")
        ),
    )

    class Facilitator:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return fake

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr("bazaar.payments.HTTPFacilitatorClient", Facilitator)
    app.add_middleware(PaymentGate)

    @app.post("/agents/summarizer/run")
    async def run():
        app.state.calls += 1
        return {"output": "Test-only specialist response"}

    return app, config, fake


async def test_402_then_paid_and_cached_replay(paid_app):
    app, config, facilitator = paid_app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://agents.example") as client:
        unpaid = await client.post("/agents/summarizer/run", json={"instruction": "summarize"})
        assert unpaid.status_code == 402 and app.state.calls == 0
        challenge = decode_payment_required_header(unpaid.headers["payment-required"])
        payload = PaymentPayload(
            accepted=challenge.accepts[0],
            payload={"authorization": {"from": "0x" + "4" * 40, "nonce": "0x" + "5" * 64}},
        )
        headers = {"payment-signature": encode_payment_signature_header(payload), "idempotency-key": "test-payment-1"}
        paid = await client.post("/agents/summarizer/run", json={"instruction": "summarize"}, headers=headers)
        assert paid.status_code == 200 and "payment-response" in paid.headers
        replay = await client.post("/agents/summarizer/run", json={"instruction": "summarize"}, headers=headers)
        assert replay.status_code == 200 and app.state.calls == 1
        changed = await client.post("/agents/summarizer/run", json={"instruction": "changed input"}, headers=headers)
        assert changed.status_code == 409
        facilitator.settle.assert_awaited_once()


async def test_wrong_price_rejected_before_execution(paid_app):
    app, config, facilitator = paid_app
    payload = PaymentPayload(accepted=requirements(config, 1), payload={})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://agents.example") as client:
        response = await client.post(
            "/agents/summarizer/run",
            json={},
            headers={
                "payment-signature": encode_payment_signature_header(payload),
                "idempotency-key": "test-payment-2",
            },
        )
    assert response.status_code == 400 and app.state.calls == 0
    facilitator.verify.assert_not_awaited()


async def test_declined_facilitator_never_runs_agent(paid_app):
    app, config, facilitator = paid_app
    facilitator.verify.return_value = VerifyResponse(is_valid=False)
    payload = PaymentPayload(accepted=requirements(config, 2000), payload={})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://agents.example") as client:
        response = await client.post(
            "/agents/summarizer/run",
            json={},
            headers={
                "payment-signature": encode_payment_signature_header(payload),
                "idempotency-key": "test-payment-3",
            },
        )
    assert response.status_code == 402 and app.state.calls == 0
    facilitator.settle.assert_not_awaited()
