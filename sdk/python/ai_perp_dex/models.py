"""
AI Perp DEX - 数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class Direction(Enum):
    """交易方向"""
    LONG = "long"
    SHORT = "short"


class IntentStatus(Enum):
    """Intent 状态"""
    OPEN = "open"
    MATCHED = "matched"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"


class SignalType(Enum):
    """信号类型"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CHANGE = "price_change"


class SignalStatus(Enum):
    """信号状态"""
    OPEN = "open"
    MATCHED = "matched"
    SETTLED = "settled"
    CANCELLED = "cancelled"


@dataclass
class Intent:
    """交易意图"""
    intent_id: str
    agent_id: str
    direction: Direction
    asset: str
    size: float
    leverage: int
    status: IntentStatus
    created_at: Optional[datetime] = None
    matched_with: Optional[str] = None
    execution_price: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Intent":
        return cls(
            intent_id=data["intent_id"],
            agent_id=data["agent_id"],
            direction=Direction(data["intent_type"]),
            asset=data["asset"],
            size=data["size_usdc"],
            leverage=data["leverage"],
            status=IntentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            matched_with=data.get("matched_with"),
            execution_price=data.get("execution_price"),
        )


@dataclass
class Match:
    """匹配结果"""
    match_id: str
    my_intent_id: str
    counterparty_id: str
    asset: str
    size: float
    price: float
    executed_at: Optional[datetime] = None
    tx_signature: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict, my_agent_id: str) -> "Match":
        # 判断自己是哪一方
        is_agent_a = data.get("agent_a_id") == my_agent_id
        return cls(
            match_id=data["match_id"],
            my_intent_id=data["intent_a_id"] if is_agent_a else data["intent_b_id"],
            counterparty_id=data["agent_b_id"] if is_agent_a else data["agent_a_id"],
            asset=data["asset"],
            size=data["size_usdc"],
            price=data["price"],
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
            tx_signature=data.get("tx_signature"),
        )


@dataclass
class Position:
    """持仓"""
    position_id: str
    agent_id: str
    asset: str
    side: PositionSide
    size: float
    entry_price: float
    current_price: float
    leverage: int
    margin: float
    margin_ratio: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    liquidation_price: float
    is_open: bool = True
    created_at: Optional[datetime] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    realized_pnl: Optional[float] = None
    close_price: Optional[float] = None
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        # created_at: API 返回 "created_at" 字段
        created_at_str = data.get("created_at") or data.get("opened_at")
        closed_at_str = data.get("closed_at")
        return cls(
            position_id=data["position_id"],
            agent_id=data["agent_id"],
            asset=data["asset"],
            side=PositionSide(data["side"]),
            size=data["size_usdc"],
            entry_price=data["entry_price"],
            current_price=data.get("current_price", data["entry_price"]),
            leverage=data["leverage"],
            margin=data.get("margin", 0),
            margin_ratio=data.get("margin_ratio", 0),
            unrealized_pnl=data.get("unrealized_pnl", 0),
            unrealized_pnl_pct=data.get("unrealized_pnl_pct", 0),
            liquidation_price=data.get("liquidation_price", 0),
            is_open=data.get("is_open", True),
            created_at=datetime.fromisoformat(created_at_str) if created_at_str else None,
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            realized_pnl=data.get("realized_pnl"),
            close_price=data.get("close_price"),
            closed_at=datetime.fromisoformat(closed_at_str) if closed_at_str else None,
            close_reason=data.get("close_reason"),
        )
    
    @property
    def is_long(self) -> bool:
        return self.side == PositionSide.LONG
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0


@dataclass
class Signal:
    """预测信号"""
    signal_id: str
    creator_id: str
    asset: str
    signal_type: SignalType
    target_value: float
    stake_amount: float
    status: SignalStatus
    expires_at: datetime
    description: Optional[str] = None
    fader_id: Optional[str] = None
    settlement_price: Optional[float] = None
    winner_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        return cls(
            signal_id=data["signal_id"],
            creator_id=data["creator_id"],
            asset=data["asset"],
            signal_type=SignalType(data["signal_type"]),
            target_value=data["target_value"],
            stake_amount=data["stake_amount"],
            status=SignalStatus(data["status"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            description=data.get("description"),
            fader_id=data.get("fader_id"),
            settlement_price=data.get("settlement_price"),
            winner_id=data.get("winner_id"),
        )


@dataclass
class Agent:
    """Agent 账户"""
    agent_id: str
    wallet_address: str
    display_name: Optional[str] = None
    twitter_handle: Optional[str] = None
    total_trades: int = 0
    total_volume: float = 0
    pnl: float = 0
    reputation_score: float = 0.5
    bio: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        return cls(
            agent_id=data["agent_id"],
            wallet_address=data["wallet_address"],
            display_name=data.get("display_name"),
            twitter_handle=data.get("twitter_handle"),
            total_trades=data.get("total_trades", 0),
            total_volume=data.get("total_volume", 0),
            pnl=data.get("pnl", 0),
            reputation_score=data.get("reputation_score", 0.5),
            bio=data.get("bio"),
        )


@dataclass
class Balance:
    """账户余额"""
    agent_id: str
    total: float
    available: float
    locked: float
    margin_used: float = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> "Balance":
        return cls(
            agent_id=data["agent_id"],
            total=data["total"],
            available=data["available"],
            locked=data["locked"],
            margin_used=data.get("margin_used", 0),
        )
    
    @property
    def free(self) -> float:
        """可用余额 (别名)"""
        return self.available


@dataclass
class OrderBook:
    """订单簿"""
    asset: str
    longs: List[Dict[str, Any]]
    shorts: List[Dict[str, Any]]
    total_long_size: float
    total_short_size: float
    sentiment: str  # "bullish" | "bearish"
    
    @classmethod
    def from_dict(cls, data: dict) -> "OrderBook":
        return cls(
            asset=data["asset"],
            longs=data.get("longs", []),
            shorts=data.get("shorts", []),
            total_long_size=data.get("total_long_size", 0),
            total_short_size=data.get("total_short_size", 0),
            sentiment=data.get("sentiment", "neutral"),
        )


@dataclass
class Price:
    """价格数据"""
    asset: str
    price: float
    change_24h: float = 0
    volume_24h: float = 0
    last_update: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Price":
        return cls(
            asset=data.get("asset", ""),
            price=data["price"],
            change_24h=data.get("change_24h", 0),
            volume_24h=data.get("volume_24h", 0),
            last_update=datetime.fromisoformat(data["last_update"]) if data.get("last_update") else None,
        )


@dataclass
class TradeAdvice:
    """交易建议"""
    recommendation: str  # "long" | "short" | "wait"
    confidence: float    # 0-1
    reason: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "TradeAdvice":
        return cls(
            recommendation=data["recommendation"],
            confidence=data["confidence"],
            reason=data["reason"],
        )


@dataclass
class RoutingResult:
    """路由结果"""
    total_size: float
    internal_filled: float
    external_filled: float
    internal_rate: str
    fee_saved: float
    total_fee: float
    
    @classmethod
    def from_dict(cls, data: dict) -> "RoutingResult":
        return cls(
            total_size=data["total_size"],
            internal_filled=data["internal_filled"],
            external_filled=data["external_filled"],
            internal_rate=data["internal_rate"],
            fee_saved=data["fee_saved"],
            total_fee=data["total_fee"],
        )


@dataclass
class TradeResult:
    """交易结果"""
    intent: Intent
    routing: RoutingResult
    match: Optional[Match] = None
    position: Optional[Position] = None
    
    @property
    def is_matched(self) -> bool:
        return self.match is not None
    
    @property
    def was_internal(self) -> bool:
        return self.routing.internal_filled > 0
