from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from bazaar.config import Settings
from bazaar.hardening import SecurityMiddleware


async def test_body_limit_applies_without_content_length():
    app = FastAPI()
    calls = []

    @app.post("/paid")
    async def paid():
        calls.append(True)
        return {"ok": True}

    app.add_middleware(SecurityMiddleware, store=SimpleNamespace(rate_limit=AsyncMock(return_value=True)), max_body=5)

    async def body():
        yield b"123456"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.com") as client:
        response = await client.post("/paid", content=body())
    assert response.status_code == 413 and not calls


async def test_redis_outage_fails_closed_for_paid_requests():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware, store=SimpleNamespace(rate_limit=AsyncMock(side_effect=ConnectionError())))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.com") as client:
        assert (await client.post("/paid")).status_code == 503


def test_configuration_never_accepts_empty_or_zero_addresses():
    with pytest.raises(ValueError):
        Settings(_env_file=None)
    with pytest.raises(ValueError):
        Settings.address("0x" + "0" * 40)
    with pytest.raises(ValueError):
        Settings.positive_budget(-1)
