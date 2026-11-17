import asyncio
import hmac
import json
import logging
import secrets
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from psycopg.types.json import Jsonb
from pydantic import ValidationError
from x402.http import FacilitatorConfig, HTTPFacilitatorClient

from .chain import Chain
from .config import Settings
from .events import event_cursor, replay_events
from .models import AgentInput, GoalInput, SessionInput
from .orchestrator import Orchestrator
from .payments import Buyer, PaymentGate
from .security import allowed_endpoint, digest, session_message
from .specialists import SERVICES, Intelligence
from .storage import Store

logger = logging.getLogger("bazaar")


def create_app(config=None):
    try:
        config = config or Settings()
    except ValidationError as error:
        missing = ", ".join(".".join(str(p) for p in e["loc"]) for e in error.errors())
        raise RuntimeError("Agent Bazaar configuration invalid: " + missing) from None
    if config.agent_pay_to.lower() == config.payer.lower():
        raise RuntimeError("AGENT_PAY_TO must differ from the orchestrator payer")
    store = Store(config)
    chain = Chain(config, store)
    brain = Intelligence(config, chain)
    buyer = Buyer(config, store)
    orchestrator = Orchestrator(config, store, chain, brain, buyer)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await brain.client.close()

    app = FastAPI(title="Agent Bazaar", version="0.1.0", lifespan=lifespan)
    app.state.config, app.state.store, app.state.chain, app.state.brain = config, store, chain, brain
    app.add_middleware(PaymentGate)
    from .hardening import SecurityMiddleware

    app.add_middleware(SecurityMiddleware, store=store)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[x.strip() for x in config.allowed_origins.split(",")],
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Invite-Token",
            "Last-Event-ID",
            "Payment-Signature",
            "Idempotency-Key",
            "X-Escrow-Id",
            "X-Payer-Signature",
        ],
        expose_headers=["Payment-Required", "Payment-Response", "X-Trace-ID"],
    )

    @app.middleware("http")
    async def observe(request, call_next):
        trace = str(uuid.uuid4())
        path = request.url.path
        safe_path = "/public/[token]" if path.startswith("/public/") else path
        run_id = path.split("/")[2] if path.startswith("/runs/") else None
        try:
            response = await call_next(request)
        except Exception as error:
            logger.error(
                json.dumps({"trace_id": trace, "run_id": run_id, "path": safe_path, "error": type(error).__name__})
            )
            response = JSONResponse({"detail": "Service unavailable", "trace_id": trace}, 503)
        response.headers.update(
            {
                "X-Trace-ID": trace,
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
            }
        )
        logger.info(
            json.dumps(
                {
                    "trace_id": trace,
                    "run_id": run_id,
                    "method": request.method,
                    "path": safe_path,
                    "status": response.status_code,
                }
            )
        )
        return response

    async def session(request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if len(token) < 32:
            raise HTTPException(401, "Connect your wallet and authorize a session")
        row = await store.query("SELECT * FROM sessions WHERE id=%s AND expires_at>now()", (digest(token),), one=True)
        if not row:
            raise HTTPException(401, "Session expired")
        return row

    async def owned_run(request, run_id):
        s = await session(request)
        try:
            uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(404, "Run not found")
        run = await store.query(
            "SELECT r.* FROM runs r JOIN sessions s ON s.id=r.session_id WHERE r.id=%s AND s.wallet=%s",
            (run_id, s["wallet"]),
            one=True,
        )
        if not run:
            raise HTTPException(404, "Run not found")
        return run

    async def health():
        checks = {}

        async def check(name, operation):
            try:
                value = await asyncio.wait_for(operation(), 15)
                checks[name] = {"ok": True, "detail": value}
            except Exception as error:
                checks[name] = {"ok": False, "detail": type(error).__name__}

        async def rpc():
            chain_id = await asyncio.to_thread(lambda: chain.web3.eth.chain_id)
            if chain_id != 84532:
                raise ValueError("Wrong network")
            return "Base Sepolia"

        async def wallet():
            balance = await asyncio.to_thread(chain.token.functions.balanceOf(config.payer).call)
            eth = await asyncio.to_thread(chain.web3.eth.get_balance, config.payer)
            if balance <= 0 or eth <= 0:
                raise ValueError("Wallet needs USDC and ETH")
            return {"usdc_units": balance, "gas_funded": True}

        async def facilitator():
            async with HTTPFacilitatorClient(FacilitatorConfig(url=config.facilitator_url)) as client:
                supported = await asyncio.to_thread(client.get_supported)
            if not any(k.network == "eip155:84532" and k.scheme == "exact" for k in supported.kinds):
                raise ValueError("Facilitator lacks Base Sepolia exact support")
            return "x402 exact supported"

        async def claude():
            await brain.client.models.retrieve(config.claude_routing_model)
            await brain.client.models.retrieve(config.claude_synthesis_model)
            return "Configured models accessible"

        async def database():
            await store.query("SELECT id FROM sessions LIMIT 1")
            return "Schema reachable"

        async def redis():
            await store.redis.ping()
            return "Connected"

        await asyncio.gather(
            *(
                check(name, op)
                for name, op in [
                    ("rpc", rpc),
                    ("wallet", wallet),
                    ("facilitator", facilitator),
                    ("claude", claude),
                    ("database", database),
                    ("redis", redis),
                ]
            )
        )
        return {"ok": all(v["ok"] for v in checks.values()), "checks": checks, "network": "Base Sepolia"}

    @app.get("/health")
    async def get_health():
        result = await health()
        return JSONResponse(result, status_code=200 if result["ok"] else 503)

    @app.get("/status")
    async def status():
        result = await health()
        try:
            agents = await chain.agents()

            async def probe(a):
                try:
                    await allowed_endpoint(a.endpoint, config.agent_allowed_hosts)
                    import httpx

                    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
                        r = await client.get(a.endpoint.removesuffix("/run") + "/manifest")
                        r.raise_for_status()
                    return {"id": a.id, "capability": a.capability, "ok": True}
                except Exception:
                    return {"id": a.id, "capability": a.capability, "ok": False}

            result["agents"] = await asyncio.gather(*(probe(a) for a in agents))
        except Exception:
            result["agents"] = []
        return result

    @app.get("/auth/challenge")
    async def challenge(address: str, budget: Decimal, request: Request):
        if (
            not chain.web3.is_address(address)
            or budget <= 0
            or budget > config.max_session_usdc
            or budget * 1_000_000 != int(budget * 1_000_000)
        ):
            raise HTTPException(400, "Invalid wallet or budget")
        if not await store.rate_limit("challenge:" + request.client.host, 10):
            raise HTTPException(429, "Too many challenges")
        nonce = secrets.token_urlsafe(24)
        message = session_message(address, nonce, str(budget))
        await store.redis.set(
            "challenge:" + nonce, {"address": address.lower(), "budget": str(budget), "message": message}, ex=300
        )
        return {"nonce": nonce, "message": message}

    @app.post("/auth/session")
    async def authorize(body: SessionInput, request: Request, x_invite_token: str = Header(default="")):
        if not hmac.compare_digest(x_invite_token, config.session_invite_token.get_secret_value()):
            raise HTTPException(403, "A valid sponsor invite is required")
        challenge = await store.redis.getdel("challenge:" + body.nonce)
        if not challenge or challenge["address"] != body.address.lower() or Decimal(challenge["budget"]) != body.budget:
            raise HTTPException(401, "Challenge expired or changed")
        signer = Account.recover_message(encode_defunct(text=challenge["message"]), signature=body.signature)
        if signer.lower() != body.address.lower():
            raise HTTPException(401, "Signature does not match wallet")
        if not await store.rate_limit("session:" + body.address.lower(), 3, 3600):
            raise HTTPException(429, "Session creation limit reached")
        token = secrets.token_urlsafe(48)
        cap = int(body.budget * 1_000_000)
        await store.query(
            "INSERT INTO sessions(id,wallet,cap,expires_at) VALUES(%s,%s,%s,%s)",
            (digest(token), signer, cap, datetime.now(UTC) + timedelta(hours=1)),
        )
        return {"token": token, "cap": cap, "wallet": signer, "expires_in": 3600}

    @app.get("/session")
    async def get_session(request: Request):
        s = await session(request)
        return {k: v for k, v in s.items() if k != "id"}

    @app.get("/agents")
    async def agents():
        return [a.model_dump() for a in await chain.agents()]

    @app.get("/agents/{slug}/manifest")
    async def manifest(slug: str):
        if slug not in SERVICES:
            raise HTTPException(404, "Unknown specialist")
        return {
            "slug": slug,
            **SERVICES[slug],
            "network": "eip155:84532",
            "pay_to": config.agent_pay_to,
            "endpoint": f"{config.api_public_url}/agents/{slug}/run",
        }

    @app.post("/agents/{slug}/bid")
    async def bid(slug: str, body: AgentInput):
        if slug not in SERVICES:
            raise HTTPException(404, "Unknown specialist")
        item = SERVICES[slug]
        return {"price": item["price"], "eta_seconds": item["eta_seconds"], "confidence": 0.85}

    @app.post("/agents/{slug}/run")
    async def specialist(slug: str, body: AgentInput):
        if slug not in SERVICES:
            raise HTTPException(404, "Unknown specialist")
        return await brain.run(slug, body)

    @app.post("/agents/{slug}/escrow")
    async def escrow_specialist(
        slug: str, body: AgentInput, x_escrow_id: str = Header(), x_payer_signature: str = Header()
    ):
        if slug not in SERVICES:
            raise HTTPException(404, "Unknown specialist")
        job = await asyncio.to_thread(chain.escrow.functions.jobs(x_escrow_id).call)
        registered = await asyncio.to_thread(chain.registry.functions.getAgent(job[2]).call)
        expected_endpoint = f"{config.api_public_url}/agents/{slug}/run"
        if (
            job[5] not in (1, 2)
            or job[1].lower() != config.agent_pay_to.lower()
            or job[3] < SERVICES[slug]["price"]
            or registered[5] != expected_endpoint
        ):
            raise HTTPException(403, "Escrow is not funded for this agent")
        binding = digest(json.dumps(body.model_dump(), sort_keys=True))
        message = f"Agent Bazaar escrow\n{x_escrow_id}\n{binding}"
        if Account.recover_message(encode_defunct(text=message), signature=x_payer_signature).lower() != job[0].lower():
            raise HTTPException(403, "Payer signature required")
        key = "escrow:" + x_escrow_id
        cached = await store.query("SELECT * FROM agent_calls WHERE id=%s", (key,), one=True)
        if cached:
            if cached["binding"] != binding or not cached["result"]:
                raise HTTPException(409, "Escrow call in progress or input changed")
            return cached["result"]
        if job[5] != 1 or job[4] <= int(datetime.now(UTC).timestamp()):
            raise HTTPException(403, "Escrow no longer permits new work")
        row = await store.query(
            "INSERT INTO agent_calls(id,binding,status) VALUES(%s,%s,'executing') ON CONFLICT DO NOTHING RETURNING id",
            (key, binding),
            one=True,
        )
        if not row:
            raise HTTPException(409, "Escrow call in progress")
        result = await brain.run(slug, body)
        await store.query("UPDATE agent_calls SET result=%s,status='completed' WHERE id=%s", (Jsonb(result), key))
        return result

    @app.post("/runs")
    async def create_run(body: GoalInput, request: Request):
        s = await session(request)
        if not await store.rate_limit("runs:" + s["id"], 5, 60):
            raise HTTPException(429, "Run rate limit exceeded")
        if not (await health())["ok"]:
            raise HTTPException(503, "Preflight failed; inspect /status before spending")
        run_id = str(uuid.uuid4())
        await store.query("INSERT INTO runs(id,session_id,goal) VALUES(%s,%s,%s)", (run_id, s["id"], body.goal))
        return {"id": run_id}

    @app.get("/runs")
    async def runs(request: Request, q: str = ""):
        s = await session(request)
        return await store.query(
            "SELECT r.id,r.goal,r.status,r.created_at,r.updated_at FROM runs r JOIN sessions s ON s.id=r.session_id WHERE s.wallet=%s AND r.goal ILIKE %s ORDER BY r.created_at DESC LIMIT 100",
            (s["wallet"], "%" + q[:200] + "%"),
        )

    @app.get("/runs/{run_id}")
    async def run_detail(run_id: str, request: Request):
        run = await owned_run(request, run_id)
        run.pop("session_id", None)
        run["events"] = await store.query("SELECT * FROM events WHERE run_id=%s ORDER BY id", (run_id,))
        run["payments"] = await store.query(
            "SELECT id,agent_id,amount,status,tx_hash,escrow_id FROM payments WHERE run_id=%s", (run_id,)
        )
        return run

    @app.post("/runs/{run_id}/share")
    async def share(run_id: str, request: Request):
        await owned_run(request, run_id)
        token = secrets.token_urlsafe(24)
        await store.query("UPDATE runs SET share_token=%s WHERE id=%s", (token, run_id))
        return {"share_token": token}

    @app.get("/public/{token}")
    async def public_run(token: str):
        run = await store.query(
            "SELECT id,goal,status,answer,results,created_at FROM runs WHERE share_token=%s", (token,), one=True
        )
        if not run:
            raise HTTPException(404, "Shared run not found")
        run["events"] = await store.query(
            "SELECT id,type,data,created_at FROM events WHERE run_id=%s ORDER BY id", (run["id"],)
        )
        return run

    @app.get("/runs/{run_id}/events")
    async def run_events(run_id: str, request: Request, last_event_id: str = Header(default="0")):
        await owned_run(request, run_id)
        try:
            cursor = event_cursor(last_event_id)
        except ValueError:
            raise HTTPException(400, "Invalid Last-Event-ID")
        return StreamingResponse(
            replay_events(store, run_id, cursor, request),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache, no-transform"},
        )

    @app.post("/runs/{run_id}/execute")
    async def execute(run_id: str, request: Request, last_event_id: str = Header(default="0")):
        run = await owned_run(request, run_id)
        try:
            cursor = event_cursor(last_event_id)
        except ValueError:
            raise HTTPException(400, "Invalid Last-Event-ID")
        if run["status"] in ("completed", "partial"):
            return StreamingResponse(
                replay_events(store, run_id, cursor, request),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache, no-transform"},
            )
        if not await store.query(
            "SELECT id FROM sessions WHERE id=%s AND expires_at>now()", (run["session_id"],), one=True
        ):
            raise HTTPException(409, "This run's spending authorization expired. Start a new run.")
        owner = secrets.token_hex(16)
        if not await store.redis.set("run-lock:" + run_id, owner, nx=True, ex=280):
            raise HTTPException(409, "Run is already executing")

        async def stream():
            nonlocal cursor
            task = asyncio.create_task(orchestrator.execute(run))
            try:
                while True:
                    finished = task.done()
                    events = await store.query(
                        "SELECT * FROM events WHERE run_id=%s AND id>%s ORDER BY id LIMIT 200", (run_id, cursor)
                    )
                    for event in events:
                        cursor = event["id"]
                        yield f"id: {cursor}\nevent: {event['type']}\ndata: {json.dumps(jsonable_encoder(event))}\n\n"
                    if finished and not events:
                        await task
                        break
                    if await request.is_disconnected():
                        break
                    if not events:
                        yield ": heartbeat\n\n"
                    await asyncio.sleep(0.6)
            finally:
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                await store.redis.eval(
                    "if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0",
                    ["run-lock:" + run_id],
                    [owner],
                )

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache, no-transform"},
        )

    return app
