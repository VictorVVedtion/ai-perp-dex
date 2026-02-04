"""
AI Perp DEX - Agent SDK

让 AI Agent 直接交易永续合约，无需人工干预。

Usage:
    from ai_perp_dex import TradingAgent
    
    agent = TradingAgent(keypair_path="~/.config/solana/agent.json")
    
    # 自然语言下单
    result = agent.execute("开 BTC 多单 $100, 10倍杠杆")
    
    # 或者结构化调用
    result = agent.open_position(
        market="BTC-PERP",
        side="long",
        size_usd=100,
        leverage=10
    )
"""

from .agent import TradingAgent
from .client import PerpDexClient
from .types import Position, Order, Market, Side, OrderType

__version__ = "0.1.0"
__all__ = [
    "TradingAgent",
    "PerpDexClient", 
    "Position",
    "Order",
    "Market",
    "Side",
    "OrderType",
]
