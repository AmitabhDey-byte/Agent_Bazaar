# Phase 0 — tooling

Date: 2026-11-15 (Asia/Calcutta). Tooling setup is implemented; the outstanding checks below are not passing. Phase 1 has not started.

## Completed

- Backed up `~/.codex/config.toml` to `~/.codex/config.toml.agent-bazaar.20261115T065423874407Z.bak` before modification. Parsed TOML and asserted preservation of all existing settings and MCP entries.
- Added Context7, Playwright, shadcn and GitHub MCP configuration. GitHub references `GITHUB_PAT`; no secret was written to configuration or the repository.
- Connected directly to the actual Context7, Playwright and shadcn stdio servers and listed their tools. Context7 resolved and queried all six requested documentation topics; see [sources](tooling-sources.md).
- Installed Chromium using `npx playwright install chromium`, including its headless shell and FFmpeg. Real browser launch/viewport checks passed at 1440x1000 and 390x844. These are tool checks, not Agent Bazaar UI checks.
- Ran `foundryup` in Git Bash. Foundry v1.9.0 installation/activation succeeded with Sigstore attestation verification.
- Created a Python 3.12.13 virtual environment. Installed pytest 9.2.0 and Slither 0.11.6. Frozen development dependencies are in `requirements-tooling.lock`.
- Installed pinned npm development tools: Playwright test 1.65.1, Playwright MCP 0.0.85, Context7 MCP 4.7.0, shadcn 4.23.0, MCP SDK 1.32.2. `package-lock.json` records resolved dependencies.
- Verified 30 requested/supporting package identifiers against upstream README content or its documented target. [Machine-readable evidence](package-verification.json) records URLs and hashes.
- Added project instructions, folder placeholders, two-viewport Playwright configuration, a fail-closed phase check runner and package/MCP verification scripts.

## Outstanding failures

1. `GITHUB_PAT` is absent from the process environment. GitHub MCP authentication is not verified. Set the token privately in the environment inherited by Codex, then restart/reload the app to expose the configured MCP servers. Do not paste the token into chat.
2. `npm audit` reports **7 development-dependency findings: 2 low, 5 moderate; 0 high, 0 critical**. A normal `npm audit fix` made no changes. The affected dependency chains include `@hono/node-server`, `minimatch`/`ts-morph`, and `deepmerge`/shadcn. The suggested forced remediation would downgrade shadcn to 1.0.0; it was not applied. These remain open, not waived or fixed. See [Hono advisory](https://github.com/advisories/GHSA-rmxm-3fg6-px4f), [minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249), [deepmerge advisory](https://github.com/advisories/GHSA-gcqx-w48m-w2h4).
3. Product phase gates cannot pass before their implementations exist. No dummy application or passing placeholder tests were introduced. [Phase gate results](phase-checks.json) record these failures.

## Actual check output

```text
python scripts/verify_packages.py
30 verified; exit 0

node scripts/check-browser.mjs
Chromium 159.0.8154.6: launch + 1440x1000 viewport OK
Chromium 159.0.8154.6: launch + 390x844 viewport OK

forge test --root contracts
Nothing to compile
[No contracts or tests exist; this is not accepted as a passing contract gate.]

.venv/Scripts/python.exe -m pytest api/tests -q
ERROR: file or directory not found: api/tests
no tests ran in 0.01s

npm --prefix web run build
ENOENT: web/package.json does not exist
[Next.js build cannot start.]

python scripts/check_phase.py
forge test: blocked - Implementation missing: contracts\foundry.toml
pytest: blocked - Implementation missing: api\tests
next build: blocked - Implementation missing: web\package.json
playwright smoke: failed - Error: No tests found
exit 1
```

## Next phase

Phase 1: Registry, Escrow and reputation contracts; unit/fuzz/invariant tests, Slither, deployment and ABI export tooling. Actual Base Sepolia deployment/verification will require a funded deployer, RPC endpoint and explorer credentials. No contracts, agents or addresses are deployed yet.
