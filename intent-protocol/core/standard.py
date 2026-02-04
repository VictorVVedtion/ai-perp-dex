"""
AIP-1: Agent Intent Protocol Standard
标准数据结构定义
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import hashlib

class IntentType(Enum):
    TRADE = "trade"
    SERVICE = "service"
    SIGNAL = "signal"
    COLLAB = "collab"
    SWAP = "swap"

class SettlementType(Enum):
    ATOMIC_SWAP = "atomic_swap"
    ESCROW = "escrow"
    PERP_DEX = "perp_dex"
    EXTERNAL_DEX = "external_dex"
    ORACLE_SETTLE = "oracle_settle"
    REVENUE_SHARE = "revenue_share"

class CommitmentStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

@dataclass
class Wallet:
    chain: str
    address: str

@dataclass
class AgentIdentity:
    """Agent 身份"""
    platform: str
    platform_id: str
    platform_handle: Optional[str] = None
    onchain_id: Optional[str] = None  # ERC-8004
    wallets: List[Wallet] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "platformId": self.platform_id,
            "platformHandle": self.platform_handle,
            "onchainId": self.onchain_id,
            "wallets": [{"chain": w.chain, "address": w.address} for w in self.wallets],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentIdentity":
        wallets = [Wallet(w["chain"], w["address"]) for w in data.get("wallets", [])]
        return cls(
            platform=data["platform"],
            platform_id=data["platformId"],
            platform_handle=data.get("platformHandle"),
            onchain_id=data.get("onchainId"),
            wallets=wallets,
        )

@dataclass
class Collateral:
    """抵押金"""
    amount: str
    token: str
    chain: str
    
    def to_dict(self) -> dict:
        return {"amount": self.amount, "token": self.token, "chain": self.chain}

@dataclass
class Constraints:
    """约束条件"""
    min_reputation: Optional[float] = None
    min_history: Optional[int] = None
    max_cost: Optional[str] = None
    deadline: Optional[int] = None
    preferred_venues: List[str] = field(default_factory=list)
    blocklist: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "counterparty": {
                "minReputation": self.min_reputation,
                "minHistory": self.min_history,
                "blocklist": self.blocklist,
            },
            "execution": {
                "maxCost": self.max_cost,
                "deadline": self.deadline,
                "preferredVenues": self.preferred_venues,
            },
        }

@dataclass
class AgentIntent:
    """AIP-1 标准 Intent"""
    
    agent: AgentIdentity
    type: IntentType
    description: str
    params: Dict[str, Any]
    
    intent_id: str = field(default_factory=lambda: f"intent_{uuid.uuid4().hex[:12]}")
    version: str = "1.0"
    constraints: Optional[Constraints] = None
    acceptable_settlements: List[SettlementType] = field(default_factory=list)
    collateral: Optional[Collateral] = None
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    expires_at: Optional[int] = None
    signature: Optional[str] = None
    
    # 来源信息 (用于追踪)
    source_platform: Optional[str] = None
    source_post_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "intentId": self.intent_id,
            "agent": self.agent.to_dict(),
            "type": self.type.value,
            "description": self.description,
            "params": self.params,
            "constraints": self.constraints.to_dict() if self.constraints else None,
            "acceptableSettlements": [s.value for s in self.acceptable_settlements],
            "collateral": self.collateral.to_dict() if self.collateral else None,
            "createdAt": self.created_at,
            "expiresAt": self.expires_at,
            "signature": self.signature,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    def hash(self) -> str:
        """生成 Intent 的唯一哈希"""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentIntent":
        return cls(
            version=data.get("version", "1.0"),
            intent_id=data.get("intentId", f"intent_{uuid.uuid4().hex[:12]}"),
            agent=AgentIdentity.from_dict(data["agent"]),
            type=IntentType(data["type"]),
            description=data["description"],
            params=data["params"],
            acceptable_settlements=[SettlementType(s) for s in data.get("acceptableSettlements", [])],
            created_at=data.get("createdAt", int(datetime.now().timestamp())),
            expires_at=data.get("expiresAt"),
            signature=data.get("signature"),
        )

@dataclass
class Commitment:
    """双方达成的承诺"""
    
    commitment_id: str
    party1_agent: AgentIdentity
    party1_intent_id: str
    party2_agent: AgentIdentity
    party2_intent_id: str
    terms: Dict[str, Any]
    settlement: SettlementType
    status: CommitmentStatus = CommitmentStatus.PENDING
    party1_signature: Optional[str] = None
    party2_signature: Optional[str] = None
    tx_hash: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    def to_dict(self) -> dict:
        return {
            "commitmentId": self.commitment_id,
            "party1": {
                "agent": self.party1_agent.to_dict(),
                "intentId": self.party1_intent_id,
            },
            "party2": {
                "agent": self.party2_agent.to_dict(),
                "intentId": self.party2_intent_id,
            },
            "terms": self.terms,
            "settlement": self.settlement.value,
            "status": self.status.value,
            "signatures": {
                "party1": self.party1_signature,
                "party2": self.party2_signature,
            },
            "txHash": self.tx_hash,
            "createdAt": self.created_at,
        }
    
    def is_fully_signed(self) -> bool:
        return self.party1_signature is not None and self.party2_signature is not None


# 便捷构造函数

def create_trade_intent(
    agent: AgentIdentity,
    action: str,
    asset: str,
    size: str,
    leverage: int = 1,
    description: str = "",
) -> AgentIntent:
    """创建交易意图"""
    return AgentIntent(
        agent=agent,
        type=IntentType.TRADE,
        description=description or f"{action} {asset} {size}",
        params={
            "action": action,
            "asset": asset,
            "size": size,
            "leverage": leverage,
        },
        acceptable_settlements=[SettlementType.PERP_DEX, SettlementType.EXTERNAL_DEX],
    )

def create_service_intent(
    agent: AgentIdentity,
    offering: str,
    price: str,
    description: str = "",
) -> AgentIntent:
    """创建服务意图"""
    return AgentIntent(
        agent=agent,
        type=IntentType.SERVICE,
        description=description or f"Offering: {offering} for {price}",
        params={
            "offering": offering,
            "price": price,
        },
        acceptable_settlements=[SettlementType.ESCROW],
    )

def create_signal_intent(
    agent: AgentIdentity,
    prediction: str,
    confidence: float,
    stake: str,
    timeframe: str = "24h",
) -> AgentIntent:
    """创建信号意图"""
    return AgentIntent(
        agent=agent,
        type=IntentType.SIGNAL,
        description=f"Prediction: {prediction} ({confidence*100}% confidence)",
        params={
            "prediction": prediction,
            "confidence": confidence,
            "stake": stake,
            "timeframe": timeframe,
        },
        acceptable_settlements=[SettlementType.ORACLE_SETTLE],
    )

def create_collab_intent(
    agent: AgentIdentity,
    proposal: str,
    split: Dict[str, float],
    duration: str = "30d",
) -> AgentIntent:
    """创建协作意图"""
    return AgentIntent(
        agent=agent,
        type=IntentType.COLLAB,
        description=f"Collab: {proposal}",
        params={
            "proposal": proposal,
            "split": split,
            "duration": duration,
        },
        acceptable_settlements=[SettlementType.REVENUE_SHARE],
    )
