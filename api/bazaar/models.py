from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Capability = Literal["web-research", "on-chain-analyst", "summarizer", "code-writer", "image-gen", "verifier"]


class Task(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    capability: Capability
    instruction: str = Field(min_length=3, max_length=4000)
    dependencies: list[str] = Field(default_factory=list, max_length=8)


class Plan(BaseModel):
    tasks: list[Task] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def dag(self):
        ids = {t.id for t in self.tasks}
        if len(ids) != len(self.tasks):
            raise ValueError("Duplicate task ID")
        done = set()
        while len(done) < len(ids):
            ready = {t.id for t in self.tasks if t.id not in done and set(t.dependencies) <= done}
            if not ready:
                raise ValueError("Plan contains a cycle or unknown dependency")
            done.update(ready)
        return self


class Agent(BaseModel):
    id: int
    owner: str
    pay_to: str
    price: int = Field(gt=0)
    endpoint: str
    capability: Capability
    reputation: int = Field(ge=0, le=10000)
    active: bool


class Bid(BaseModel):
    agent_id: int
    price: int = Field(gt=0, le=100_000_000)
    eta_seconds: int = Field(ge=1, le=120)
    confidence: float = Field(ge=0, le=1)
    score: float = 0


class GoalInput(BaseModel):
    goal: str = Field(min_length=8, max_length=2000)


class AgentInput(BaseModel):
    instruction: str = Field(min_length=3, max_length=12000)
    context: str = Field(default="", max_length=24000)


class SessionInput(BaseModel):
    address: str
    signature: str = Field(max_length=160)
    nonce: str = Field(max_length=100)
    budget: Decimal = Field(gt=0, le=100, decimal_places=6)


class VerifyResult(BaseModel):
    approved: bool
    reason: str = Field(max_length=1000)
