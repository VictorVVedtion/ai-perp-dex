"""
AI Perp DEX - Python SDK

AI-Native 永续合约交易接口，让 Agent 一行代码接入交易。

Usage:
    from ai_perp_dex import TradingHub
    
    async with TradingHub(api_key="th_xxx") as hub:
        match = await hub.long("BTC", size=100, leverage=5)
"""

from .client import TradingHub, quick_long, quick_short
from .models import (
    Intent,
    Match,
    Position,
    Signal,
    Agent,
    Balance,
    Direction,
    IntentStatus,
    PositionSide,
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
    "Direction",
    "IntentStatus",
    "PositionSide",
    # Exceptions
    "TradingHubError",
    "AuthenticationError",
    "RateLimitError",
    "InsufficientBalanceError",
    "PositionNotFoundError",
    "InvalidParameterError",
    "NetworkError",
]
