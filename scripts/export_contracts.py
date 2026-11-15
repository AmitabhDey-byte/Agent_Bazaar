"""Export compiled ABIs. Addresses are exported only from successful Base Sepolia broadcasts."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for name in ("AgentRegistry", "Escrow"):
    artifact = json.loads((root / f"contracts/out/{name}.sol/{name}.json").read_text())
    target = root / f"shared/{name}.json"
    target.write_text(json.dumps(artifact["abi"], indent=2) + "\n")
    # API is deployed as a separate Vercel project, so include its own ABI copy.
    destination = root / "api/abis"
    destination.mkdir(exist_ok=True)
    (destination / f"{name}.json").write_text(json.dumps(artifact["abi"]) + "\n")
broadcast = root / "contracts/broadcast/Deploy.s.sol/84532/run-latest.json"
if broadcast.exists():
    data = json.loads(broadcast.read_text())
    receipts = {r["transactionHash"].lower(): r for r in data.get("receipts", []) if str(r.get("status")) in ("0x1", "1")}
    addresses = {t["contractName"]: t["contractAddress"] for t in data["transactions"]
                 if t.get("transactionType") == "CREATE" and t.get("hash", "").lower() in receipts}
    if not {"AgentRegistry", "Escrow"} <= addresses.keys():
        raise SystemExit("Deployment receipts incomplete; addresses not exported")
    (root / "shared/addresses.json").write_text(json.dumps({"chainId": 84532, **addresses}, indent=2) + "\n")
    print("ABIs and successful deployment addresses exported")
else:
    print("ABIs exported; no deployment broadcast, so no addresses fabricated")
