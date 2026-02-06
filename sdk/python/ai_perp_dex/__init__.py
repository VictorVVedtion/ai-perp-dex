"""
AI Perp DEX - Python SDK (Async, Production)

这是推荐的生产级 SDK，提供异步接口、类型化模型和完整异常处理。
简单脚本可使用同步版: `from perp_dex import PerpDEX`

Usage:
    from ai_perp_dex import TradingHub

    async with TradingHub(api_key="th_xxx") as hub:
        await hub.long("BTC-PERP", size=100, leverage=5)
        positions = await hub.get_positions()
        signal = await hub.create_signal("BTC-PERP", "price_above", 70000, stake=50)
"""

from .client import TradingHub, quick_long, quick_short
from .models import (
    Intent,
    Match,
    Position,
    Signal,
    Agent,
    Balance,
    OrderBook,
    Price,
    TradeAdvice,
    RoutingResult,
    TradeResult,
    Direction,
    IntentStatus,
    PositionSide,
    SignalType,
    SignalStatus,
)
from .exceptions import (
    TradingHubError,
    AuthenticationError,
    RateLimitError,
    InsufficientBalanceError,
    PositionNotFoundError,
    InvalidParameterError,
    NetworkError,
)

__version__ = "0.1.0"
__all__ = [
    # Client
    "TradingHub",
    "quick_long",
    "quick_short",
    # Models
    "Intent",
    "Match",
    "Position",
    "Signal",
    "Agent",
    "Balance",
    "OrderBook",
    "Price",
    "TradeAdvice",
    "RoutingResult",
    "TradeResult",
    "Direction",
    "IntentStatus",
    "PositionSide",
    "SignalType",
    "SignalStatus",
    # Exceptions
    "TradingHubError",
    "AuthenticationError",
    "RateLimitError",
    "InsufficientBalanceError",
    "PositionNotFoundError",
    "InvalidParameterError",
    "NetworkError",
]
