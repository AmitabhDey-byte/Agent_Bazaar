# Phase 0 source verification

Checked 2026-11-15. `package-verification.json` records 30 package identifiers, official README URLs, short matching excerpts and content hashes. This verifies identity, not version compatibility or application behavior. Tenacity's README is a pointer to `doc/source/index.rst`; that target was checked.

## MCP configuration

- [Official Codex MCP configuration](https://developers.openai.com/codex/mcp/): existing configuration is preserved; stdio uses `command`/`args`, GitHub uses `url` and `bearer_token_env_var`.
- [Context7 MCP README](https://github.com/upstash/context7/blob/master/packages/mcp/README.md): `npx -y @upstash/context7-mcp`.
- [Playwright MCP README](https://github.com/microsoft/playwright-mcp): `npx -y @playwright/mcp@latest`.
- [shadcn MCP](https://ui.shadcn.com/docs/mcp): `npx -y shadcn@latest mcp`.
- [GitHub MCP server](https://github.com/github/github-mcp-server): remote endpoint `https://api.githubcopilot.com/mcp/`; token supplied only through `GITHUB_PAT`.
- [MCP TypeScript SDK v1](https://github.com/modelcontextprotocol/typescript-sdk/tree/v1.x): pinned maintenance-line SDK used only by the tooling adapter to call actual local MCP servers. Product code has no dependency on this adapter.

The newly configured servers are not injected into this already-running chat's tool catalog. `scripts/mcp-client.mjs` checks their actual stdio servers using the official SDK. Restart/reload Codex to expose the configured tools natively. Raw local MCP responses are ignored under `.local/mcp/`.

## Context7 queries completed

| Topic | Resolved library | Findings / primary sources |
| --- | --- | --- |
| x402 | `/coinbase/x402` | [Python SDK](https://github.com/coinbase/x402/blob/main/python/x402/README.md), [FastAPI example](https://github.com/coinbase/x402/blob/main/examples/python/servers/fastapi/README.md): package extras `fastapi,httpx,evm`; v2 uses resource server, exact EVM scheme, ASGI middleware and CAIP-2 networks. Check signatures against the installed version; upstream snippets differ. |
| viem | `/wevm/viem` | [Contract simulation](https://viem.sh/docs/contract/simulateContract), [write](https://viem.sh/docs/contract/writeContract): simulate, submit with a wallet client, then confirm receipt. Configure Base Sepolia explicitly; generic examples use other chains. |
| wagmi | `/wevm/wagmi` | [SSR guide](https://wagmi.sh/react/guides/ssr): client-side WagmiProvider plus QueryClientProvider, SSR config and cookie hydration. App Router headers are awaited. |
| FastAPI on Vercel | `/websites/vercel` | [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [duration](https://vercel.com/docs/functions/configuring-functions/duration): export `app` from `index.py` relative to API project root; configure duration on that entrypoint. StreamingResponse supports response streaming; no invented streaming config flag. |
| Neon | `/websites/neon` | [Connection selection](https://neon.com/docs/connect/choose-connection): pooled runtime hostname includes `-pooler`; choose direct connections for session-sensitive migration operations. No JS Neon SDK is required for a Python backend. |
| Upstash | `/upstash/docs` | [Python client](https://github.com/upstash/docs/blob/main/redis/sdks/py/gettingstarted.mdx), [REST API](https://github.com/upstash/docs/blob/main/redis/features/restapi.mdx): async client imports from `upstash_redis.asyncio`; SET NX with expiry is atomic. Specialized REST subscribe endpoint streams SSE; ordinary REST command calls do not provide a persistent TCP subscription. Verify Python support before choosing the transport. |

## Installation and execution

[Foundry installation](https://getfoundry.sh/introduction/installation/) requires Git Bash or WSL on Windows. `foundryup` verified the release Sigstore bundle before activating v1.9.0. Python 3.12.13 is installed and selected by `.python-version`; the system default remains 3.14.

Only development dependencies are installed in this phase. `web/`, `api/`, `contracts/`, and `shared/` are reserved directories, not completed implementations. No service provisioning, deployment, paid model calls or blockchain transactions were performed.
