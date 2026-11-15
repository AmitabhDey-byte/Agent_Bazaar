import asyncio
import hashlib
import ipaddress
import re
import socket
from urllib.parse import urlparse


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def session_message(address, nonce, budget):
    return f"Agent Bazaar session\nWallet: {address.lower()}\nNetwork: Base Sepolia (84532)\nBudget: {budget} USDC\nNonce: {nonce}\nAuthorize one hour of sponsored agent calls within this budget."


def filter_output(value: str) -> str:
    if len(value) > 48000:
        raise ValueError("Agent output exceeds size limit")
    if re.search(
        r"ignore (all |the )?(previous|prior) instructions|reveal.{0,20}(private key|api key|system prompt)|<\|(?:system|assistant)",
        value,
        re.IGNORECASE,
    ):
        raise ValueError("Agent output rejected by injection filter")
    return value.replace("\x00", "")


async def allowed_endpoint(url: str, allowed_hosts: str):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Agent endpoint must be an HTTPS URL without credentials")
    if parsed.hostname not in {h.strip().lower() for h in allowed_hosts.split(",")}:
        raise ValueError("Agent host is not allowlisted")
    addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Agent endpoint resolves to a non-public address")
    return url
