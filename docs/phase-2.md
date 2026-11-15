# Phase 2

Implemented Python/FastAPI specialists, x402 v2 payment middleware using the official SDK, real Claude tool-based planning/verification, paid image-provider calls, reverse auctions, durable budgets/payment journal, payment-replay protection, agent circuit breakers, escrow funding/release, on-chain receipt validation, session wallet authentication, invite-gated sponsorship, persisted events and SSE execution.

15 initial pytest checks passed, including a mocked-facilitator 402 -> signed request -> settlement -> cached replay flow, wrong-price rejection, invalid facilitator response, DAG validation, price/reputation ranking, SSRF input rules and failover. Test doubles exist only under `api/tests`.

The API fails startup if configuration is absent. No live payment, Claude invocation, database migration, Redis call, image call or deployment is claimed as verified. Ambiguous settlements retain reservations and stop failover to prevent a second charge. A crashed specialist call may need operator reconciliation; this deliberate limitation is not described as automatic recovery.

Execution stays inside a 230-second streaming request. Durable checkpoints allow a paused run to resume; finished partial runs preserve failed task details. The server's sponsor wallet pays within an authenticated off-chain session budget; this is not an on-chain smart-account session-key system. A trusted verifier key signs releases only after a paid verifier approves.
