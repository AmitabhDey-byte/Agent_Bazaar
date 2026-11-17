import asyncio
import json

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from psycopg.types.json import Jsonb
from web3 import Web3

from .auction import auction
from .models import Plan, Task, VerifyResult
from .payments import AmbiguousPayment
from .security import allowed_endpoint, digest, filter_output


class Orchestrator:
    def __init__(self, config, store, chain, brain, buyer):
        self.config, self.store, self.chain, self.brain, self.buyer = config, store, chain, brain, buyer

    async def paid(self, task, body, run_id, agents, force_direct=False):
        bids = await auction(task, agents, self.store, self.config, run_id)
        for index, bid in enumerate(bids):
            agent = next(a for a in agents if a.id == bid.agent_id)
            payment_id = digest(f"{run_id}:{task.id}:{agent.id}:{json.dumps(body, sort_keys=True)}")
            await self.store.event(
                run_id, "win", {"task_id": task.id, "agent_id": agent.id, "price": bid.price, "failover": index > 0}
            )
            try:
                if bid.price >= int(self.config.escrow_threshold_usdc * 1_000_000) and not force_direct:
                    payment = await self.store.reserve(
                        payment_id, run_id, agent.id, agent.price, int(self.config.max_agent_usdc * 1_000_000)
                    )
                    job_id = payment.get("escrow_id")
                    if not job_id:
                        # The transaction journal prevents a new fund transaction on resume.
                        job_id, tx = await self.chain.fund(agent.id, agent.price, payment_id)
                        await self.store.query(
                            "UPDATE payments SET escrow_id=%s,status='escrowed',tx_hash=%s WHERE id=%s",
                            (job_id, tx, payment_id),
                        )
                        await self.store.event(
                            run_id,
                            "pay",
                            {
                                "task_id": task.id,
                                "agent_id": agent.id,
                                "amount": agent.price,
                                "tx_hash": tx,
                                "escrow_id": job_id,
                                "reserved": True,
                            },
                        )
                    await allowed_endpoint(agent.endpoint, self.config.agent_allowed_hosts)
                    message = f"Agent Bazaar escrow\n{job_id}\n{digest(json.dumps(body, sort_keys=True))}"
                    sig = Account.sign_message(
                        encode_defunct(text=message), self.config.orchestrator_private_key.get_secret_value()
                    ).signature.hex()
                    async with httpx.AsyncClient(timeout=100, follow_redirects=False) as client:
                        response = await client.post(
                            agent.endpoint.removesuffix("/run") + "/escrow",
                            json=body,
                            headers={"X-Escrow-Id": job_id, "X-Payer-Signature": sig},
                        )
                        response.raise_for_status()
                    return response.json(), agent, payment_id, job_id
                result, tx = await self.buyer.call(agent, body, payment_id, run_id)
                return result, agent, payment_id, None
            except AmbiguousPayment:
                raise
            except Exception as error:
                if bid.price >= int(self.config.escrow_threshold_usdc * 1_000_000) and not force_direct:
                    # Any funding failure can be a mined transaction with a lost response.
                    raise AmbiguousPayment("Escrow funding/execution needs reconciliation") from error
                await self.store.redis.set(f"circuit:{agent.id}", "open", ex=60)
                await self.store.event(
                    run_id,
                    "failover",
                    {
                        "task_id": task.id,
                        "agent_id": agent.id,
                        "reason": type(error).__name__,
                        "next_agent_id": bids[index + 1].agent_id if index + 1 < len(bids) else None,
                    },
                )
        raise ValueError("No available eligible bidder")

    async def task(self, task, run_id, results, agents):
        context = json.dumps({key: results[key] for key in task.dependencies})[:24000]
        result = {}
        try:
            async with asyncio.timeout(170):
                paid_result, agent, payment_id, job_id = await self.paid(
                    task, {"instruction": task.instruction, "context": context}, run_id, agents
                )
                output = filter_output(paid_result["output"])
                result = {**paid_result}
                result["output"] = output
                result["agent_id"] = agent.id
                result["escrow_id"] = job_id
                await self.store.event(
                    run_id, "result", {"task_id": task.id, "agent_id": agent.id, "output": output[:4000]}
                )
                verify_task = Task(
                    id=f"v_{task.id}"[:40],
                    capability="verifier",
                    instruction="Check completion of: " + task.instruction,
                )
                verification, _, _, _ = await self.paid(
                    verify_task,
                    {"instruction": verify_task.instruction, "context": output},
                    run_id,
                    agents,
                    force_direct=True,
                )
                verdict = VerifyResult.model_validate(verification.get("verdict") or json.loads(verification["output"]))
                await self.store.event(
                    run_id, "verify", {"task_id": task.id, "agent_id": agent.id, **verdict.model_dump()}
                )
                tx = None
                if job_id and verdict.approved:
                    tx = await self.chain.release(
                        job_id, Web3.keccak(text=json.dumps(result, sort_keys=True)), payment_id
                    )
                    await self.store.finish_payment(payment_id, "settled", tx)
                elif not job_id:
                    payment = await self.store.query(
                        "SELECT tx_hash FROM payments WHERE id=%s", (payment_id,), one=True
                    )
                    receipt = await self.chain.reputation(agent.id, agent.price, verdict.approved, payment["tx_hash"])
                    tx = Web3.to_hex(receipt["transactionHash"])
                if tx:
                    await self.store.event(
                        run_id, "settle", {"task_id": task.id, "agent_id": agent.id, "tx_hash": tx, "escrow_id": job_id}
                    )
                result.update(
                    {
                        "verified": verdict.approved,
                        "verification": verdict.reason,
                        "agent_id": agent.id,
                        "escrow_id": job_id,
                    }
                )
                if job_id and not verdict.approved:
                    result["warning"] = "Escrow held; payer can refund after its deadline."
        except (Exception, asyncio.CancelledError) as error:
            result.update(
                {
                    "error": type(error).__name__,
                    "verified": False,
                    "message": "Task incomplete; existing payment reservations are preserved when settlement is uncertain.",
                }
            )
            if isinstance(error, asyncio.CancelledError):
                # A cancelled task is retried using its durable payment/transaction identifiers.
                raise
            await self.store.event(run_id, "error", {"task_id": task.id, **result})
        await self.store.query(
            "UPDATE runs SET results=results || %s,updated_at=now() WHERE id=%s", (Jsonb({task.id: result}), run_id)
        )
        return task.id, result

    async def execute(self, run):
        run_id = str(run["id"])
        await self.store.query("UPDATE runs SET status='running',updated_at=now() WHERE id=%s", (run_id,))
        try:
            async with asyncio.timeout(230):
                plan = Plan.model_validate(run["plan"]) if run["plan"] else await self.brain.plan(run["goal"])
                if not run["plan"]:
                    await self.store.query("UPDATE runs SET plan=%s WHERE id=%s", (Jsonb(plan.model_dump()), run_id))
                    await self.store.event(run_id, "plan", plan.model_dump())
                agents = await self.chain.agents()
                results = dict(run["results"])
                remaining = {t.id: t for t in plan.tasks if t.id not in results}
                while remaining:
                    ready = [t for t in remaining.values() if set(t.dependencies) <= results.keys()]
                    if not ready:
                        raise ValueError("No executable DAG tasks")
                    outcomes = await asyncio.gather(*(self.task(t, run_id, results, agents) for t in ready))
                    for key, result in outcomes:
                        results[key] = result
                        remaining.pop(key)
                answer = await self.brain.synthesize(run["goal"], results)
                status = (
                    "partial" if any(r.get("error") or not r.get("verified") for r in results.values()) else "completed"
                )
                await self.store.query(
                    "UPDATE runs SET status=%s,answer=%s,updated_at=now() WHERE id=%s", (status, answer, run_id)
                )
                await self.store.event(run_id, "complete", {"status": status, "answer": answer})
        except (TimeoutError, asyncio.CancelledError):
            await self.store.query("UPDATE runs SET status='paused',updated_at=now() WHERE id=%s", (run_id,))
            await self.store.event(
                run_id, "paused", {"message": "Execution paused at a durable checkpoint. Resume to continue."}
            )
        except Exception as error:
            await self.store.query("UPDATE runs SET status='partial',updated_at=now() WHERE id=%s", (run_id,))
            await self.store.event(
                run_id,
                "error",
                {"message": "Run interrupted; partial results retained.", "reason": type(error).__name__},
            )
