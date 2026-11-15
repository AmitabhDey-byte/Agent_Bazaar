"""Verify requested package identifiers against upstream READMEs, without installing the app."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = [
    ("next", "vercel/next.js/canary/packages/next/README.md"),
    ("react", "facebook/react/main/README.md"),
    ("react-dom", "facebook/react/main/packages/react-dom/README.md"),
    ("typescript", "microsoft/TypeScript/main/README.md"),
    ("tailwindcss", "tailwindlabs/tailwindcss/main/README.md"),
    ("shadcn", "shadcn-ui/ui/main/packages/shadcn/README.md"),
    ("motion", "motiondivision/motion/main/README.md"),
    ("@xyflow/react", "xyflow/xyflow/main/packages/react/README.md"),
    ("wagmi", "wevm/wagmi/main/packages/react/README.md"),
    ("viem", "wevm/viem/main/src/README.md"),
    ("@tanstack/react-query", "TanStack/query/main/packages/react-query/README.md"),
    ("zustand", "pmndrs/zustand/main/README.md"),
    ("fastapi", "fastapi/fastapi/master/README.md"),
    ("anthropic", "anthropics/anthropic-sdk-python/main/README.md"),
    ("x402", "coinbase/x402/main/python/x402/README.md"),
    ("web3", "ethereum/web3.py/main/README.md"),
    ("pydantic", "pydantic/pydantic/main/README.md"),
    ("tenacity", "jd/tenacity/main/doc/source/index.rst"),
    ("psycopg", "psycopg/psycopg/master/README.rst"),
    ("upstash-redis", "upstash/redis-py/main/README.md"),
    ("pytest", "pytest-dev/pytest/main/README.rst"),
    ("slither-analyzer", "crytic/slither/master/README.md"),
    ("@openzeppelin/contracts", "OpenZeppelin/openzeppelin-contracts/master/README.md"),
    ("forge", "foundry-rs/foundry/master/README.md"),
    ("@playwright/test", "microsoft/playwright/main/README.md"),
    ("@playwright/mcp", "microsoft/playwright-mcp/main/README.md"),
    ("@upstash/context7-mcp", "upstash/context7/master/packages/mcp/README.md"),
    ("@modelcontextprotocol/sdk", "modelcontextprotocol/typescript-sdk/v1.x/README.md"),
    ("zod", "colinhacks/zod/main/README.md"),
    ("github-mcp-server", "github/github-mcp-server/main/README.md"),
]

def verify(item):
    package, location = item
    url = "https://raw.githubusercontent.com/" + location
    try:
        with urlopen(Request(url, headers={"User-Agent": "Agent-Bazaar-tooling"}), timeout=35) as response:
            body = response.read()
        content = body.decode("utf-8")
        matches = [line.strip()[:240] for line in content.splitlines() if package.lower() in line.lower()]
        return {"package": package, "source": url, "status": "verified" if matches else "needs-review", "evidence": matches[:2], "sha256": hashlib.sha256(body).hexdigest()}
    except Exception as error:
        return {"package": package, "source": url, "status": "failed", "error": str(error)}

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(verify, SOURCES))
    destination = Path("docs/package-verification.json")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(), "scope": "Package identity only; not API or compatibility validation", "packages": results}, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result['status']}: {result['package']}" + (f" - {result['error']}" if "error" in result else ""))
    raise SystemExit(int(any(result["status"] != "verified" for result in results)))
