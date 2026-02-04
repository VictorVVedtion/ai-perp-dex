"""Type definitions for AI Perp DEX"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class Side(Enum):
    LONG = "long"
    SHORT = "short"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Market:
    """永续合约市场"""
    symbol: str          # e.g., "BTC-PERP"
    index: int           # 市场索引 (0=BTC, 1=ETH, 2=SOL)
    base_asset: str      # e.g., "BTC"
    price: float         # 当前价格
    index_price: float   # 指数价格
    funding_rate: float  # 资金费率
    open_interest: float # 未平仓量
    volume_24h: float    # 24h成交量
    

@dataclass
class Position:
    """Agent 持仓"""
    market: str
    side: Side
    size: float           # 仓位大小 (合约数量)
    size_usd: float       # 仓位价值 (USD)
    entry_price: float    # 开仓均价
    mark_price: float     # 标记价格
    liquidation_price: float  # 强平价格
    margin: float         # 保证金
    leverage: float       # 杠杆倍数
    unrealized_pnl: float # 未实现盈亏
    unrealized_pnl_percent: float  # 未实现盈亏百分比
    opened_at: datetime


@dataclass 
class Order:
    """订单"""
    id: str
    market: str
    side: Side
    order_type: OrderType
    size: float
    price: Optional[float]  # Limit/Stop 订单价格
    leverage: float
    status: OrderStatus
    filled_size: float
    filled_price: Optional[float]
    created_at: datetime
    updated_at: datetime


@dataclass
class TradeResult:
    """交易结果"""
    success: bool
    order_id: Optional[str]
    tx_signature: Optional[str]  # Solana 交易签名
    message: str
    position: Optional[Position]  # 交易后的持仓
    

@dataclass
class AccountInfo:
    """Agent 账户信息"""
    agent_id: str
    pubkey: str
    collateral: float      # 抵押品余额 (USDC)
    available_margin: float  # 可用保证金
    total_position_value: float  # 持仓总价值
    total_unrealized_pnl: float  # 总未实现盈亏
    total_realized_pnl: float    # 总已实现盈亏
    positions: list[Position]
    open_orders: list[Order]
