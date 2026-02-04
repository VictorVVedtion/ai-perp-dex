"""AI Perp DEX SDK - Trade perpetuals P2P as an AI agent"""

from .types import Side, TradeRequest, Quote, Position, Market
from .client import Client
from .trader import TradingAgent
from .mm import MarketMaker

__version__ = "0.1.0"
__all__ = [
    "Side",
    "TradeRequest", 
    "Quote",
    "Position",
    "Market",
    "Client",
    "TradingAgent",
    "MarketMaker",
]
