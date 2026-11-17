import json
import re

import httpx
from eth_account import Account
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from starlette.middleware.base import BaseHTTPMiddleware
from x402 import x402Client
from x402.http import FacilitatorConfig, HTTPFacilitatorClient
from x402.http.utils import (
    decode_payment_required_header,
    decode_payment_response_header,
    decode_payment_signature_header,
    encode_payment_required_header,
    encode_payment_response_header,
    encode_payment_signature_header,
)
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.schemas import PaymentRequired, PaymentRequirements, ResourceInfo, SettleResponse

from .security import allowed_endpoint, digest
from .specialists import SERVICES


class AmbiguousPayment(RuntimeError):
    """A signed payment may have settled. Preserve reservation; never silently pay again."""


def requirements(config, price):
    return PaymentRequirements(
        scheme="exact",
        network="eip155:84532",
        asset=config.usdc_address,
        amount=str(price),
        pay_to=config.agent_pay_to,
        max_timeout_seconds=120,
        extra={"name": "USDC", "version": "2"},
    )


class PaymentGate(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        match = re.fullmatch(r"/agents/([a-z-]+)/run", request.url.path)
        if not match or request.method != "POST" or match[1] not in SERVICES:
            return await call_next(request)
        config, store = request.app.state.config, request.app.state.store
        required = requirements(config, SERVICES[match[1]]["price"])
        challenge = PaymentRequired(
            accepts=[required], resource=ResourceInfo(url=config.api_public_url + request.url.path)
        )
        signature = request.headers.get("payment-signature")
        if not signature:
            return JSONResponse(
                challenge.model_dump(by_alias=True),
                status_code=402,
                headers={"PAYMENT-REQUIRED": encode_payment_required_header(challenge)},
            )
        try:
            payload = decode_payment_signature_header(signature)
            if payload.x402_version != 2 or payload.accepted != required:
                raise ValueError("Payment does not match this resource")
            key = request.headers.get("idempotency-key", "")
            if not re.fullmatch(r"[a-zA-Z0-9:_-]{8,160}", key):
                raise ValueError("A valid Idempotency-Key is required")
            body = await request.body()
            if len(body) > 64000:
                raise ValueError("Request too large")
            binding = digest(request.url.path + body.decode() + signature)
            # Claim payment authorization itself, not just an attacker-controlled request key.
            authorization = payload.payload.get("authorization", {})
            nonce_key = digest(str(authorization.get("from")) + str(authorization.get("nonce")))
            call_id = "paid:" + nonce_key
            cached = await store.query("SELECT * FROM agent_calls WHERE id=%s", (call_id,), one=True)
            if cached:
                if cached["binding"] != binding:
                    return JSONResponse({"detail": "Payment replay with changed input"}, 409)
                if cached["status"] == "settled":
                    return JSONResponse(
                        cached["result"],
                        headers={
                            "PAYMENT-RESPONSE": encode_payment_response_header(
                                SettleResponse.model_validate(cached["receipt"])
                            )
                        },
                    )
                return JSONResponse({"detail": "Payment is in progress or needs reconciliation"}, 409)
            async with HTTPFacilitatorClient(FacilitatorConfig(url=config.facilitator_url)) as facilitator:
                verification = await facilitator.verify(payload, required)
                if not verification.is_valid:
                    return JSONResponse(
                        {"detail": "Payment authorization rejected"},
                        402,
                        headers={"PAYMENT-REQUIRED": encode_payment_required_header(challenge)},
                    )
                claim = await store.query(
                    "INSERT INTO agent_calls(id,binding,status) VALUES(%s,%s,'executing') ON CONFLICT DO NOTHING RETURNING id",
                    (call_id, binding),
                    one=True,
                )
                if not claim:
                    return JSONResponse({"detail": "Payment already claimed"}, 409)
                response = await call_next(request)
                content = b"".join([chunk async for chunk in response.body_iterator])
                if response.status_code != 200:
                    await store.query("UPDATE agent_calls SET status='failed' WHERE id=%s", (call_id,))
                    return JSONResponse({"detail": "Agent failed before settlement"}, 503)
                result = json.loads(content)
                await store.query(
                    "UPDATE agent_calls SET status='settling',result=%s WHERE id=%s", (Jsonb(result), call_id)
                )
                receipt = await facilitator.settle(payload, required)
                if not receipt.success:
                    return JSONResponse({"detail": "Settlement not confirmed"}, 502)
                await store.query(
                    "UPDATE agent_calls SET status='settled',receipt=%s,updated_at=now() WHERE id=%s",
                    (Jsonb(receipt.model_dump()), call_id),
                )
                return JSONResponse(result, headers={"PAYMENT-RESPONSE": encode_payment_response_header(receipt)})
        except ValueError:
            return JSONResponse({"detail": "Invalid payment request"}, 400)
        except Exception:
            return JSONResponse({"detail": "Payment service unavailable; reconcile before retrying"}, 503)


class Buyer:
    def __init__(self, config, store):
        self.config, self.store = config, store
        self.client = x402Client()
        signer = EthAccountSigner(Account.from_key(config.orchestrator_private_key.get_secret_value()))
        self.client.register("eip155:84532", ExactEvmScheme(signer=signer))

    async def call(self, agent, body, payment_id, run_id, *, obligation):
        await allowed_endpoint(agent.endpoint, self.config.agent_allowed_hosts)
        payment = await self.store.reserve(
            payment_id,
            run_id,
            agent.id,
            agent.price,
            int(self.config.max_agent_usdc * 1_000_000),
            obligation=obligation,
        )
        if payment["status"] == "cancelled":
            raise ValueError("This payment attempt was cancelled; use another bidder")
        signed = payment.get("payload")
        async with httpx.AsyncClient(timeout=100, follow_redirects=False) as client:
            if payment["status"] == "settled":
                # A result not checkpointed after settlement must be fetched with the identical authorization.
                if not signed:
                    raise AmbiguousPayment("Settled payment lacks replay payload")
            if not signed:
                try:
                    response = await client.post(agent.endpoint, json=body)
                    if response.status_code != 402:
                        raise ValueError("Agent did not request x402 payment")
                    challenge = decode_payment_required_header(response.headers["payment-required"])
                    choices = [
                        r
                        for r in challenge.accepts
                        if r.network == "eip155:84532"
                        and r.scheme == "exact"
                        and r.asset.lower() == self.config.usdc_address.lower()
                        and r.pay_to.lower() == agent.pay_to.lower()
                        and int(r.amount) == agent.price
                    ]
                    if challenge.x402_version != 2 or not choices:
                        raise ValueError("Payment requirements differ from winning bid")
                    challenge.accepts = choices[:1]
                    payload = await self.client.create_payment_payload(challenge)
                    signed = payload.model_dump(by_alias=True)
                    await self.store.query(
                        "UPDATE payments SET payload=%s,status='signed' WHERE id=%s", (Jsonb(signed), payment_id)
                    )
                except Exception:
                    await self.store.finish_payment(payment_id, "cancelled")
                    raise
            from x402.schemas import PaymentPayload

            header = encode_payment_signature_header(PaymentPayload.model_validate(signed))
            try:
                response = await client.post(
                    agent.endpoint, json=body, headers={"PAYMENT-SIGNATURE": header, "Idempotency-Key": payment_id}
                )
                response.raise_for_status()
                receipt = decode_payment_response_header(response.headers["payment-response"])
                if (
                    not receipt.success
                    or receipt.network != "eip155:84532"
                    or not re.fullmatch(r"0x[0-9a-fA-F]{64}", receipt.transaction)
                ):
                    raise ValueError("Invalid settlement receipt")
                # A remote server's response header alone is not proof of an on-chain transfer.
                import asyncio

                from web3 import Web3

                rpc = Web3(Web3.HTTPProvider(self.config.base_sepolia_rpc_url, request_kwargs={"timeout": 15}))
                onchain = await asyncio.to_thread(rpc.eth.wait_for_transaction_receipt, receipt.transaction, 30)
                transfer = Web3.keccak(text="Transfer(address,address,uint256)")
                matched = any(
                    log["address"].lower() == self.config.usdc_address.lower()
                    and len(log["topics"]) == 3
                    and log["topics"][0] == transfer
                    and ("0x" + log["topics"][1].hex()[-40:]).lower() == self.config.payer.lower()
                    and ("0x" + log["topics"][2].hex()[-40:]).lower() == agent.pay_to.lower()
                    and int.from_bytes(log["data"], "big") == agent.price
                    for log in onchain["logs"]
                )
                if onchain["status"] != 1 or not matched:
                    raise ValueError("USDC transfer receipt does not match payment")
                await self.store.finish_payment(payment_id, "settled", receipt.transaction)
                await self.store.event(
                    run_id,
                    "pay",
                    {
                        "agent_id": agent.id,
                        "amount": agent.price,
                        "tx_hash": receipt.transaction,
                        "payment_id": payment_id,
                    },
                )
                return response.json(), receipt.transaction
            except Exception as error:
                raise AmbiguousPayment("Payment submitted; settlement requires reconciliation") from error
