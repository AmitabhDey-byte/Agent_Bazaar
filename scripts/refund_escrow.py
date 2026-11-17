"""Refund an expired job through the payer's durable transaction journal."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"api"))
from dotenv import load_dotenv
from bazaar.config import Settings
from bazaar.storage import Store
from bazaar.chain import Chain

async def main(payment_id):
    load_dotenv(Path(__file__).resolve().parents[1]/".env")
    config=Settings()
    store=Store(config)
    payment=await store.query("SELECT * FROM payments WHERE id=%s",(payment_id,),one=True)
    if not payment or not payment["escrow_id"] or payment["status"]=="settled":
        raise SystemExit("No refundable escrow for this payment")
    chain=Chain(config,store)
    receipt=await chain.send(chain.escrow.functions.refund(payment["escrow_id"]),"refund:"+payment_id)
    await store.finish_payment(payment_id,"cancelled",chain.web3.to_hex(receipt["transactionHash"]))
    print("Refund confirmed: "+chain.web3.to_hex(receipt["transactionHash"]))

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Usage: refund_escrow.py PAYMENT_ID")
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop if sys.platform=="win32" else None) as runner:
        runner.run(main(sys.argv[1]))
