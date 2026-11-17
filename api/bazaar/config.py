from decimal import Decimal
from functools import lru_cache
from urllib.parse import urlsplit

from eth_account import Account
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    anthropic_api_key: SecretStr
    database_url: SecretStr
    upstash_redis_rest_url: str
    upstash_redis_rest_token: SecretStr
    base_sepolia_rpc_url: str
    orchestrator_private_key: SecretStr
    verifier_private_key: SecretStr
    registry_address: str
    escrow_address: str
    agent_pay_to: str
    session_invite_token: SecretStr
    api_public_url: str
    agent_allowed_hosts: str
    allowed_origins: str = "http://localhost:3000"
    usdc_address: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    facilitator_url: str = "https://x402.org/facilitator"
    claude_routing_model: str = "claude-haiku-5-5"
    claude_synthesis_model: str = "claude-sonnet-5-5"
    image_api_url: str = "https://api.openai.com/v1/images/generations"
    image_api_key: SecretStr
    image_model: str = "gpt-image-1"
    max_session_usdc: Decimal = Decimal(2)
    max_agent_usdc: Decimal = Decimal("0.5")
    escrow_threshold_usdc: Decimal = Decimal("0.10")

    @field_validator("registry_address", "escrow_address", "usdc_address", "agent_pay_to")
    @classmethod
    def address(cls, value):
        from web3 import Web3

        if not Web3.is_address(value) or int(value, 16) == 0:
            raise ValueError("A nonzero EVM address is required")
        return Web3.to_checksum_address(value)

    @field_validator("orchestrator_private_key", "verifier_private_key")
    @classmethod
    def private_key(cls, value):
        Account.from_key(value.get_secret_value())
        return value

    @field_validator(
        "anthropic_api_key", "database_url", "upstash_redis_rest_token", "session_invite_token", "image_api_key"
    )
    @classmethod
    def required_secret(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError("Required secret is empty")
        return value

    @field_validator("max_session_usdc", "max_agent_usdc", "escrow_threshold_usdc")
    @classmethod
    def positive_budget(cls, value):
        if value <= 0 or value > 100 or value * 1_000_000 != int(value * 1_000_000):
            raise ValueError("Budget must be positive, at most 100 USDC and have at most six decimal places")
        return value

    @property
    def payer(self):
        return Account.from_key(self.orchestrator_private_key.get_secret_value()).address

    @field_validator(
        "api_public_url", "upstash_redis_rest_url", "base_sepolia_rpc_url", "facilitator_url", "image_api_url"
    )
    @classmethod
    def secure_url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("A credential-free HTTPS URL is required")
        return value.rstrip("/")

    @field_validator("allowed_origins")
    @classmethod
    def origins(cls, value):
        for origin in value.split(","):
            parsed = urlsplit(origin.strip())
            local = parsed.hostname in ("localhost", "127.0.0.1") and parsed.scheme == "http"
            if (
                (parsed.scheme != "https" and not local)
                or not parsed.hostname
                or parsed.hostname == "*"
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS requires exact HTTPS origins (HTTP localhost allowed)")
        return value

    @field_validator("agent_allowed_hosts")
    @classmethod
    def hosts(cls, value):
        hosts = [host.strip().lower() for host in value.split(",")]
        if not hosts or any(not host or any(c in host for c in "/:@* ") for host in hosts):
            raise ValueError("Agent allowlist requires exact hostnames")
        return ",".join(hosts)


@lru_cache
def settings():
    return Settings()
