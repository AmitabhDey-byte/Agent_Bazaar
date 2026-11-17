"""Register the eight real specialist endpoints after verifying their public manifests."""
import json
import os
from pathlib import Path
import sys
import httpx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"api"))
from bazaar.specialists import SERVICES
load_dotenv(root/".env")
required=["BASE_SEPOLIA_RPC_URL","DEPLOYER_PRIVATE_KEY","REGISTRY_ADDRESS","AGENT_PAY_TO","API_PUBLIC_URL"]
missing=[key for key in required if not os.getenv(key)]
if missing:raise SystemExit("Missing seed configuration: "+", ".join(missing))
w3=Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC_URL"],request_kwargs={"timeout":20}))
if w3.eth.chain_id!=84532:raise SystemExit("Base Sepolia only")
account=Account.from_key(os.environ["DEPLOYER_PRIVATE_KEY"])
registry=w3.eth.contract(address=Web3.to_checksum_address(os.environ["REGISTRY_ADDRESS"]),abi=json.loads((root/"shared/AgentRegistry.json").read_text()))
existing={registry.functions.getAgent(i).call()[5] for i in range(1,registry.functions.count().call()+1)}
receipts=[]
for slug,service in SERVICES.items():
    endpoint=os.environ["API_PUBLIC_URL"].rstrip("/")+f"/agents/{slug}/run"
    if endpoint in existing:
        print(f"Already registered: {slug}")
        continue
    response=httpx.get(endpoint.removesuffix("/run")+"/manifest",timeout=15,follow_redirects=False)
    response.raise_for_status()
    manifest=response.json()
    if manifest["price"]!=service["price"] or manifest["capability"]!=service["capability"] or manifest["pay_to"].lower()!=os.environ["AGENT_PAY_TO"].lower():
        raise SystemExit(f"Manifest differs from seed configuration: {slug}")
    tx=registry.functions.register(endpoint,service["capability"],service["price"],Web3.to_checksum_address(os.environ["AGENT_PAY_TO"])).build_transaction({"from":account.address,"nonce":w3.eth.get_transaction_count(account.address,"pending"),"chainId":84532})
    signed=account.sign_transaction(tx)
    tx_hash=w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt=w3.eth.wait_for_transaction_receipt(tx_hash,120)
    if receipt["status"]!=1:raise SystemExit(f"Registration reverted: {slug}")
    receipts.append({"slug":slug,"transaction":Web3.to_hex(tx_hash),"block":receipt["blockNumber"]})
    print(f"Registered {slug}: {Web3.to_hex(tx_hash)}")
(root/"shared/seed-receipts.json").write_text(json.dumps(receipts,indent=2)+"\n")
