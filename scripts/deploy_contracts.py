"""Broadcast and verify real Base Sepolia contracts; never invent deployment metadata."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from dotenv import load_dotenv
from eth_account import Account

root=Path(__file__).resolve().parents[1]
load_dotenv(root/".env")
required=["BASE_SEPOLIA_RPC_URL","DEPLOYER_PRIVATE_KEY","ORCHESTRATOR_PRIVATE_KEY","VERIFIER_PRIVATE_KEY","USDC_ADDRESS","ETHERSCAN_API_KEY"]
missing=[key for key in required if not os.getenv(key)]
if missing:raise SystemExit("Missing deployment configuration: "+", ".join(missing))
for role in ("ORCHESTRATOR","VERIFIER"):
    derived=Account.from_key(os.environ[role+"_PRIVATE_KEY"]).address
    if os.getenv(role+"_ADDRESS",derived).lower()!=derived.lower():raise SystemExit(role+" key/address mismatch")
    os.environ[role+"_ADDRESS"]=derived
broadcast=root/"contracts/broadcast/Deploy.s.sol/84532/run-latest.json"
if broadcast.exists():raise SystemExit("Existing broadcast found. Inspect and resume with Foundry; this script refuses duplicate deployments.")
forge=shutil.which("forge") or str(Path.home()/".foundry/bin"/("forge.exe" if os.name=="nt" else "forge"))
subprocess.run([forge,"script","script/Deploy.s.sol:Deploy","--rpc-url","base_sepolia","--broadcast","--verify","--slow"],cwd=root/"contracts",check=True)
subprocess.run([sys.executable,str(root/"scripts/export_contracts.py")],cwd=root,check=True)
