"""Core types for AI Perp DEX"""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class Market(BaseModel):
    """Market information"""
    symbol: str
    base_asset: str
    quote_asset: str = "USD"
    price: float
    volume_24h: float = 0
    open_interest: float = 0
    funding_rate: float = 0
    max_leverage: int = 50


class TradeRequest(BaseModel):
    """A request from a trader seeking quotes from MMs"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    market: str
    side: Side
    size_usdc: float
    leverage: int = 1
    max_slippage_bps: int = 100  # 1% default
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    quotes_count: int = 0


class Quote(BaseModel):
    """A quote from an MM responding to a trade request"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    agent_id: str  # MM's agent ID
    funding_rate: float
    collateral_usdc: float
    valid_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Aliases for convenience
    @property
    def mm_id(self) -> str:
        return self.agent_id


class Position(BaseModel):
    """An open position between a trader and MM"""
    id: str
    trader_id: str
    mm_id: str
    market: str
    side: Side
    size_usdc: float
    entry_price: float
    mark_price: Optional[float] = None
    leverage: int = 1
    unrealized_pnl: float = 0
    created_at: datetime
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0


class AgentInfo(BaseModel):
    """Information about an agent on the network"""
    id: str
    agent_type: str  # "trader" or "mm"
    is_online: bool = False
    total_volume: float = 0
    total_pnl: float = 0
    trade_count: int = 0


class WebSocketMessage(BaseModel):
    """Message received via WebSocket"""
    type: str  # "request", "quote", "fill", "close", "heartbeat"
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
