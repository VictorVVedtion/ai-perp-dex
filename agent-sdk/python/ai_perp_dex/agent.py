"""
TradingAgent - AI Agent 交易接口

让 AI Agent 用自然语言或结构化 API 交易永续合约。
"""

import re
import json
from typing import Optional, Union
from pathlib import Path

from .client import PerpDexClient
from .types import (
    Side, OrderType, Position, Order, TradeResult, 
    AccountInfo, Market
)


class TradingAgent:
    """
    AI Agent 的交易接口
    
    Example:
        agent = TradingAgent(keypair_path="~/.config/solana/agent.json")
        
        # 自然语言
        agent.execute("开 BTC 多单 $100, 10x")
        
        # 结构化
        agent.open_position("BTC-PERP", "long", 100, leverage=10)
    """
    
    def __init__(
        self,
        keypair_path: Optional[str] = None,
        private_key: Optional[str] = None,
        api_url: str = "https://api.ai-perp-dex.io",
        rpc_url: str = "https://api.devnet.solana.com",
    ):
        """
        初始化 Trading Agent
        
        Args:
            keypair_path: Solana keypair JSON 文件路径
            private_key: 或者直接传私钥 (base58)
            api_url: Matching Engine API URL
            rpc_url: Solana RPC URL
        """
        self.client = PerpDexClient(
            keypair_path=keypair_path,
            private_key=private_key,
            api_url=api_url,
            rpc_url=rpc_url,
        )
        self._registered = False
        
    async def register(self, name: str = "AI Agent") -> bool:
        """注册为交易 Agent"""
        result = await self.client.register_agent(name)
        self._registered = result
        return result
    
    # ==================== 自然语言接口 ====================
    
    def execute(self, command: str) -> TradeResult:
        """
        执行自然语言交易命令
        
        Examples:
            "开 BTC 多单 $100, 10倍杠杆"
            "平掉 ETH 空单"
            "查看持仓"
            "BTC 止损 $95000"
        """
        command = command.lower().strip()
        
        # 解析开仓命令
        open_match = re.search(
            r'(开|open|买|long|做多|short|做空|卖空)\s*'
            r'(btc|eth|sol)\s*'
            r'(多|空|long|short)?\s*'
            r'[单仓]?\s*'
            r'\$?(\d+(?:\.\d+)?)\s*'
            r'(?:,?\s*(\d+)(?:x|倍)?)?',
            command
        )
        
        if open_match:
            action, market, direction, size, leverage = open_match.groups()
            
            # 判断方向
            if direction in ['空', 'short'] or action in ['short', '做空', '卖空']:
                side = Side.SHORT
            else:
                side = Side.LONG
                
            market_symbol = f"{market.upper()}-PERP"
            size_usd = float(size)
            lev = int(leverage) if leverage else 10
            
            return self.open_position(
                market=market_symbol,
                side=side,
                size_usd=size_usd,
                leverage=lev
            )
        
        # 解析平仓命令
        close_match = re.search(
            r'(平|close|平仓)\s*(btc|eth|sol)?',
            command
        )
        
        if close_match:
            _, market = close_match.groups()
            if market:
                return self.close_position(f"{market.upper()}-PERP")
            else:
                return self.close_all_positions()
        
        # 查看持仓
        if any(kw in command for kw in ['持仓', 'position', '仓位', '查看']):
            positions = self.get_positions()
            return TradeResult(
                success=True,
                order_id=None,
                tx_signature=None,
                message=f"当前持仓: {len(positions)} 个",
                position=positions[0] if positions else None
            )
        
        return TradeResult(
            success=False,
            order_id=None,
            tx_signature=None,
            message=f"无法理解命令: {command}",
            position=None
        )
    
    # ==================== 结构化 API ====================
    
    def open_position(
        self,
        market: str,
        side: Union[Side, str],
        size_usd: float,
        leverage: int = 10,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
    ) -> TradeResult:
        """
        开仓
        
        Args:
            market: 市场 (e.g., "BTC-PERP")
            side: 方向 ("long" 或 "short")
            size_usd: 仓位大小 (USD)
            leverage: 杠杆倍数 (1-50)
            order_type: 订单类型
            price: 限价单价格
        """
        if isinstance(side, str):
            side = Side.LONG if side.lower() == "long" else Side.SHORT
            
        return self.client.open_position(
            market=market,
            side=side,
            size_usd=size_usd,
            leverage=leverage,
            order_type=order_type,
            price=price,
        )
    
    def close_position(
        self,
        market: str,
        size_percent: float = 100,
    ) -> TradeResult:
        """
        平仓
        
        Args:
            market: 市场
            size_percent: 平仓比例 (0-100)
        """
        return self.client.close_position(market, size_percent)
    
    def close_all_positions(self) -> TradeResult:
        """平掉所有仓位"""
        return self.client.close_all_positions()
    
    def modify_position(
        self,
        market: str,
        new_leverage: Optional[int] = None,
        add_margin: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> TradeResult:
        """修改持仓"""
        return self.client.modify_position(
            market=market,
            new_leverage=new_leverage,
            add_margin=add_margin,
            take_profit=take_profit,
            stop_loss=stop_loss,
        )
    
    # ==================== 查询接口 ====================
    
    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        return self.client.get_account()
    
    def get_positions(self) -> list[Position]:
        """获取所有持仓"""
        return self.client.get_positions()
    
    def get_position(self, market: str) -> Optional[Position]:
        """获取特定市场持仓"""
        return self.client.get_position(market)
    
    def get_orders(self) -> list[Order]:
        """获取未成交订单"""
        return self.client.get_orders()
    
    def get_markets(self) -> list[Market]:
        """获取所有市场"""
        return self.client.get_markets()
    
    def get_price(self, market: str) -> float:
        """获取市场价格"""
        return self.client.get_price(market)
    
    # ==================== 资金管理 ====================
    
    def deposit(self, amount: float) -> TradeResult:
        """存入抵押品 (USDC)"""
        return self.client.deposit(amount)
    
    def withdraw(self, amount: float) -> TradeResult:
        """提取抵押品"""
        return self.client.withdraw(amount)
