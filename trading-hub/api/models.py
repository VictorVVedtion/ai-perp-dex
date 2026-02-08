"""
Trading Hub - 数据模型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import hashlib

class AgentStatus(Enum):
    PENDING = "pending"      # 等待验证
    ACTIVE = "active"        # 已激活
    SUSPENDED = "suspended"  # 已暂停

class IntentType(Enum):
    LONG = "long"
    SHORT = "short"
    SWAP = "swap"
    SIGNAL = "signal"

class IntentStatus(Enum):
    OPEN = "open"           # 开放匹配
    MATCHED = "matched"     # 已匹配
    EXECUTED = "executed"   # 已执行
    CANCELLED = "cancelled" # 已取消
    EXPIRED = "expired"     # 已过期

@dataclass
class Agent:
    """Agent 账户"""
    agent_id: str
    wallet_address: str
    created_at: datetime = field(default_factory=datetime.now)
    status: AgentStatus = AgentStatus.PENDING
    
    # 可选身份
    twitter_handle: Optional[str] = None
    twitter_verified: bool = False
    moltbook_handle: Optional[str] = None
    
    # 统计
    total_trades: int = 0
    total_volume: float = 0
    pnl: float = 0
    reputation_score: float = 0.5  # 0-1

    # 元数据
    display_name: Optional[str] = None
    bio: Optional[str] = None

    # 社交验证
    verified: bool = False
    verification_nonce: Optional[str] = None
    nonce_created_at: Optional[str] = None  # ISO timestamp for nonce expiry check
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "wallet_address": self.wallet_address,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "twitter_handle": self.twitter_handle,
            "twitter_verified": self.twitter_verified,
            "moltbook_handle": self.moltbook_handle,
            "total_trades": self.total_trades,
            "total_volume": self.total_volume,
            "pnl": self.pnl,
            "reputation_score": self.reputation_score,
            "display_name": self.display_name,
            "bio": self.bio,
            "verified": self.verified,
            "nonce_created_at": self.nonce_created_at,
        }

@dataclass
class TradingIntent:
    """交易意图"""
    intent_id: str = field(default_factory=lambda: f"int_{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    
    # 交易参数
    intent_type: IntentType = IntentType.LONG
    asset: str = "BTC-PERP"
    size_usdc: float = 100
    leverage: int = 1
    
    # 约束
    max_slippage: float = 0.005  # 0.5%
    min_counterparty_reputation: float = 0.3
    expires_at: Optional[datetime] = None
    
    # 状态
    status: IntentStatus = IntentStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    
    # 匹配信息
    matched_with: Optional[str] = None  # 对手 intent_id
    matched_at: Optional[datetime] = None
    
    # 执行信息
    execution_price: Optional[float] = None
    tx_signature: Optional[str] = None
    
    # 来源
    source_platform: str = "trading_hub"  # trading_hub | moltbook | moltx
    source_post_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "agent_id": self.agent_id,
            "intent_type": self.intent_type.value,
            "asset": self.asset,
            "size_usdc": self.size_usdc,
            "leverage": self.leverage,
            "max_slippage": self.max_slippage,
            "min_counterparty_reputation": self.min_counterparty_reputation,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "matched_with": self.matched_with,
            "matched_at": self.matched_at.isoformat() if self.matched_at else None,
            "execution_price": self.execution_price,
            "tx_signature": self.tx_signature,
            "source_platform": self.source_platform,
        }
    
    def is_compatible_with(self, other: "TradingIntent") -> bool:
        """检查两个 Intent 是否可以匹配"""
        # 同一个 Agent 不能自己匹配
        if self.agent_id == other.agent_id:
            return False
        
        # 必须是相反方向
        if self.intent_type == other.intent_type:
            return False
        
        # 必须是同一个资产
        if self.asset != other.asset:
            return False
        
        # 都必须是 OPEN 状态
        if self.status != IntentStatus.OPEN or other.status != IntentStatus.OPEN:
            return False
        
        return True

@dataclass
class Match:
    """匹配记录"""
    match_id: str = field(default_factory=lambda: f"match_{uuid.uuid4().hex[:12]}")
    
    intent_a_id: str = ""
    intent_b_id: str = ""
    agent_a_id: str = ""
    agent_b_id: str = ""
    
    asset: str = "BTC-PERP"
    size_usdc: float = 0
    price: float = 0
    
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    tx_signature: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "intent_a_id": self.intent_a_id,
            "intent_b_id": self.intent_b_id,
            "agent_a_id": self.agent_a_id,
            "agent_b_id": self.agent_b_id,
            "asset": self.asset,
            "size_usdc": self.size_usdc,
            "price": self.price,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "tx_signature": self.tx_signature,
        }
