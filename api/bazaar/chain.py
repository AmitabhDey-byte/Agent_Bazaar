import asyncio
import json
import secrets
from pathlib import Path

from eth_account import Account
from web3 import Web3

from .models import Agent

TOKEN_ABI = [
    {
        "type": "function",
        "name": "balanceOf",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "approve",
        "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "outputs": [{"type": "bool"}],
        "stateMutability": "nonpayable",
    },
]


class Chain:
    def __init__(self, config, store):
        self.config, self.store = config, store
        self.web3 = Web3(Web3.HTTPProvider(config.base_sepolia_rpc_url, request_kwargs={"timeout": 15}))
        abis = Path(__file__).resolve().parents[1] / "abis"
        self.registry = self.web3.eth.contract(
            address=config.registry_address, abi=json.loads((abis / "AgentRegistry.json").read_text())
        )
        self.escrow = self.web3.eth.contract(
            address=config.escrow_address, abi=json.loads((abis / "Escrow.json").read_text())
        )
        self.token = self.web3.eth.contract(address=config.usdc_address, abi=TOKEN_ABI)

    async def agents(self):
        def read():
            if self.web3.eth.chain_id != 84532:
                raise ValueError("RPC is not Base Sepolia")
            count = self.registry.functions.count().call()
            if count > 500:
                raise ValueError("Registry requires pagination beyond 500 agents")
            result = []
            for i in range(1, count + 1):
                a = self.registry.functions.getAgent(i).call()
                try:
                    result.append(
                        Agent(
                            id=i,
                            owner=a[0],
                            pay_to=a[1],
                            price=a[2],
                            active=a[4],
                            endpoint=a[5],
                            capability=a[6],
                            reputation=self.registry.functions.reputation(i).call(),
                        )
                    )
                except ValueError:
                    continue
            return result

        return await asyncio.to_thread(read)

    async def send(self, function, operation):
        account = Account.from_key(self.config.orchestrator_private_key.get_secret_value())
        lock_key = f"nonce:{account.address}"
        lock = secrets.token_hex(16)
        for _ in range(40):
            if await self.store.redis.set(lock_key, lock, nx=True, ex=120):
                break
            await asyncio.sleep(0.5)
        else:
            raise TimeoutError("Wallet is busy; transaction not submitted")
        try:
            if await asyncio.to_thread(lambda: self.web3.eth.chain_id) != 84532:
                raise ValueError("Base Sepolia only")
            existing = await self.store.query("SELECT * FROM chain_transactions WHERE id=%s", (operation,), one=True)
            if existing:
                raw, tx_hash = bytes.fromhex(existing["raw_tx"]), existing["tx_hash"]
            else:

                def sign():
                    tx = function.build_transaction(
                        {
                            "from": account.address,
                            "nonce": self.web3.eth.get_transaction_count(account.address, "pending"),
                            "chainId": 84532,
                        }
                    )
                    signed = account.sign_transaction(tx)
                    return bytes(signed.raw_transaction), Web3.to_hex(signed.hash)

                raw, tx_hash = await asyncio.to_thread(sign)
                await self.store.query(
                    "INSERT INTO chain_transactions(id,raw_tx,tx_hash) VALUES(%s,%s,%s)",
                    (operation, raw.hex(), tx_hash),
                )
            try:
                await asyncio.to_thread(self.web3.eth.send_raw_transaction, raw)
            except Exception:
                # The durable signed transaction is reused; never sign a replacement here.
                pass
            receipt = await asyncio.to_thread(self.web3.eth.wait_for_transaction_receipt, tx_hash, 45)
            if receipt["status"] != 1:
                raise ValueError(f"Transaction reverted: {tx_hash}")
            return receipt
        finally:
            await self.store.redis.eval(
                "if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0",
                [lock_key],
                [lock],
            )

    async def reputation(self, agent_id, amount, success, receipt_hash):
        receipt = Web3.keccak(text=receipt_hash)
        return await self.send(
            self.registry.functions.recordOutcome(agent_id, amount, success, receipt), f"rep:{receipt_hash}"
        )

    async def fund(self, agent_id, amount, operation):
        await self.send(self.token.functions.approve(self.config.escrow_address, amount), f"approve:{operation}")
        # Use a durable deadline from the latest chain block; reuse journaled tx on retries.
        block = await asyncio.to_thread(self.web3.eth.get_block, "latest")
        receipt = await self.send(
            self.escrow.functions.fund(agent_id, amount, block["timestamp"] + 3600), f"fund:{operation}"
        )
        logs = self.escrow.events.Funded().process_receipt(receipt)
        return Web3.to_hex(logs[0]["args"]["jobId"]), Web3.to_hex(receipt["transactionHash"])

    async def release(self, job_id, result_hash, operation):
        job = await asyncio.to_thread(self.escrow.functions.jobs(job_id).call)
        deadline = job[4] - 1
        digest = await asyncio.to_thread(self.escrow.functions.approvalDigest(job_id, result_hash, deadline).call)
        verifier = Account.from_key(self.config.verifier_private_key.get_secret_value())
        # The digest was produced by the deployed EIP-712 contract, including domain separation.
        sig = verifier.unsafe_sign_hash(digest).signature
        receipt = await self.send(
            self.escrow.functions.release(job_id, result_hash, deadline, sig), f"release:{operation}"
        )
        return Web3.to_hex(receipt["transactionHash"])
