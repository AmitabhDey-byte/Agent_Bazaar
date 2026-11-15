# Phase 1

Implemented permissionless agent registration/update, authorized settlement reporters, unique receipt protection, payment-weighted reputation with 30-day discrete half-life, USDC escrow, EIP-712 verifier release, timeout refunds, Base Sepolia-only deployment script and ABI export.

Forge: 8 passing tests, including two 256-case fuzz tests and 128 invariant runs / 4096 calls. Slither was executed: timestamp comparisons are intrinsic to expiry/decay and intentionally retained; the reported divide-before-multiply was replaced with a remainder-based timestamp calculation. This is not an external security audit.

Deployment and BaseScan verification require the deferred credentials/funds. No addresses were invented. Later phase gates remain unavailable until their implementation. `docs/phase-checks.json` records the checks at this phase boundary.
