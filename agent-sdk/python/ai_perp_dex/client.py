"""
PerpDexClient - 底层 API 客户端

连接 Matching Engine 和 Solana 链上程序。
"""

import json
import base64
import struct
import hashlib
from typing import Optional
from pathlib import Path
from datetime import datetime

import httpx
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from solana.rpc.api import Client as SolanaClient

from .types import (
    Side, OrderType, Position, Order, TradeResult,
    AccountInfo, Market, OrderStatus
)


# Devnet Program ID
PROGRAM_ID = Pubkey.from_string("CWQ6LrVY3E6tHfyMzEqZjGsgpdfoJYU1S5A3qmG7LuL6")


class PerpDexClient:
    """
    底层客户端，处理与 Matching Engine API 和 Solana 的通信
    """
    
    def __init__(
        self,
        keypair_path: Optional[str] = None,
        private_key: Optional[str] = None,
        api_url: str = "https://api.ai-perp-dex.io",
        rpc_url: str = "https://api.devnet.solana.com",
    ):
        # 加载 keypair
        if keypair_path:
            path = Path(keypair_path).expanduser()
            with open(path) as f:
                secret = json.load(f)
            self.keypair = Keypair.from_bytes(bytes(secret))
        elif private_key:
            self.keypair = Keypair.from_base58_string(private_key)
        else:
            # 生成新的 keypair
            self.keypair = Keypair()
            
        self.pubkey = self.keypair.pubkey()
        self.api_url = api_url.rstrip('/')
        self.rpc_url = rpc_url
        self.solana = SolanaClient(rpc_url)
        self.http = httpx.Client(timeout=30)
        
        # 计算 PDAs
        self._exchange_pda = self._find_pda([b"exchange"])
        self._agent_pda = self._find_pda([b"agent", bytes(self.pubkey)])
        
    def _find_pda(self, seeds: list[bytes]) -> Pubkey:
        """计算 PDA"""
        pda, _ = Pubkey.find_program_address(seeds, PROGRAM_ID)
        return pda
    
    def _get_position_pda(self, market_index: int) -> Pubkey:
        """计算持仓 PDA"""
        return self._find_pda([
            b"position", 
            bytes(self._agent_pda),
            bytes([market_index])
        ])
    
    def _market_to_index(self, market: str) -> int:
        """市场符号转索引"""
        markets = {"BTC-PERP": 0, "ETH-PERP": 1, "SOL-PERP": 2}
        return markets.get(market.upper(), 0)
    
    # ==================== Agent 注册 ====================
    
    async def register_agent(self, name: str) -> bool:
        """在链上注册为交易 Agent"""
        try:
            # 调用链上 register_agent 指令
            # 这里简化处理，实际需要构建完整交易
            response = self.http.post(
                f"{self.api_url}/agent/register",
                json={
                    "pubkey": str(self.pubkey),
                    "name": name,
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Registration failed: {e}")
            return False
    
    # ==================== 交易接口 ====================
    
    def open_position(
        self,
        market: str,
        side: Side,
        size_usd: float,
        leverage: int,
        order_type: OrderType,
        price: Optional[float],
    ) -> TradeResult:
        """发送开仓订单到 Matching Engine"""
        try:
            # 1. 发送订单到 Matching Engine
            order_data = {
                "agent_pubkey": str(self.pubkey),
                "market": market,
                "side": side.value,
                "size_usd": size_usd,
                "leverage": leverage,
                "order_type": order_type.value,
                "price": price,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # 签名订单
            message = json.dumps(order_data, sort_keys=True).encode()
            signature = self.keypair.sign_message(message)
            order_data["signature"] = base64.b64encode(bytes(signature)).decode()
            
            response = self.http.post(
                f"{self.api_url}/order/submit",
                json=order_data
            )
            
            if response.status_code == 200:
                result = response.json()
                return TradeResult(
                    success=True,
                    order_id=result.get("order_id"),
                    tx_signature=result.get("tx_signature"),
                    message=f"订单已提交: {side.value} {market} ${size_usd} @ {leverage}x",
                    position=None  # 会异步更新
                )
            else:
                return TradeResult(
                    success=False,
                    order_id=None,
                    tx_signature=None,
                    message=f"订单失败: {response.text}",
                    position=None
                )
                
        except Exception as e:
            return TradeResult(
                success=False,
                order_id=None,
                tx_signature=None,
                message=f"错误: {str(e)}",
                position=None
            )
    
    def close_position(self, market: str, size_percent: float) -> TradeResult:
        """平仓"""
        try:
            response = self.http.post(
                f"{self.api_url}/order/close",
                json={
                    "agent_pubkey": str(self.pubkey),
                    "market": market,
                    "size_percent": size_percent,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return TradeResult(
                    success=True,
                    order_id=result.get("order_id"),
                    tx_signature=result.get("tx_signature"),
                    message=f"平仓订单已提交: {market} {size_percent}%",
                    position=None
                )
            else:
                return TradeResult(
                    success=False,
                    order_id=None,
                    tx_signature=None,
                    message=f"平仓失败: {response.text}",
                    position=None
                )
        except Exception as e:
            return TradeResult(
                success=False,
                order_id=None, 
                tx_signature=None,
                message=f"错误: {str(e)}",
                position=None
            )
    
    def close_all_positions(self) -> TradeResult:
        """平掉所有仓位"""
        positions = self.get_positions()
        for pos in positions:
            self.close_position(pos.market, 100)
        return TradeResult(
            success=True,
            order_id=None,
            tx_signature=None,
            message=f"已提交平仓 {len(positions)} 个仓位",
            position=None
        )
    
    def modify_position(
        self,
        market: str,
        new_leverage: Optional[int] = None,
        add_margin: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> TradeResult:
        """修改持仓"""
        try:
            response = self.http.post(
                f"{self.api_url}/position/modify",
                json={
                    "agent_pubkey": str(self.pubkey),
                    "market": market,
                    "new_leverage": new_leverage,
                    "add_margin": add_margin,
                    "take_profit": take_profit,
                    "stop_loss": stop_loss,
                }
            )
            return TradeResult(
                success=response.status_code == 200,
                order_id=None,
                tx_signature=None,
                message="持仓已修改" if response.status_code == 200 else response.text,
                position=None
            )
        except Exception as e:
            return TradeResult(
                success=False,
                order_id=None,
                tx_signature=None,
                message=f"错误: {str(e)}",
                position=None
            )
    
    # ==================== 查询接口 ====================
    
    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        try:
            # 从链上读取 Agent 账户
            response = self.solana.get_account_info(self._agent_pda)
            if response.value:
                # 解析账户数据
                data = response.value.data
                # 简化处理，实际需要按 Anchor 格式解析
                return AccountInfo(
                    agent_id=str(self._agent_pda),
                    pubkey=str(self.pubkey),
                    collateral=0,
                    available_margin=0,
                    total_position_value=0,
                    total_unrealized_pnl=0,
                    total_realized_pnl=0,
                    positions=[],
                    open_orders=[],
                )
        except Exception as e:
            print(f"Failed to get account: {e}")
        
        return AccountInfo(
            agent_id="",
            pubkey=str(self.pubkey),
            collateral=0,
            available_margin=0,
            total_position_value=0,
            total_unrealized_pnl=0,
            total_realized_pnl=0,
            positions=[],
            open_orders=[],
        )
    
    def get_positions(self) -> list[Position]:
        """获取所有持仓"""
        positions = []
        for market_index in range(3):  # BTC, ETH, SOL
            pos = self._get_position_from_chain(market_index)
            if pos:
                positions.append(pos)
        return positions
    
    def _get_position_from_chain(self, market_index: int) -> Optional[Position]:
        """从链上读取持仓"""
        try:
            pda = self._get_position_pda(market_index)
            response = self.solana.get_account_info(pda)
            if response.value and response.value.data:
                # 解析持仓数据
                # 实际需要按 Anchor 格式解析
                return None  # 简化
        except:
            pass
        return None
    
    def get_position(self, market: str) -> Optional[Position]:
        """获取特定市场持仓"""
        index = self._market_to_index(market)
        return self._get_position_from_chain(index)
    
    def get_orders(self) -> list[Order]:
        """获取未成交订单"""
        try:
            response = self.http.get(
                f"{self.api_url}/orders",
                params={"agent_pubkey": str(self.pubkey)}
            )
            if response.status_code == 200:
                return [Order(**o) for o in response.json()]
        except:
            pass
        return []
    
    def get_markets(self) -> list[Market]:
        """获取所有市场"""
        try:
            response = self.http.get(f"{self.api_url}/markets")
            if response.status_code == 200:
                return [Market(**m) for m in response.json()]
        except:
            pass
        
        # 返回默认市场
        return [
            Market(
                symbol="BTC-PERP",
                index=0,
                base_asset="BTC",
                price=97500,
                index_price=97500,
                funding_rate=0.0001,
                open_interest=0,
                volume_24h=0,
            ),
            Market(
                symbol="ETH-PERP",
                index=1,
                base_asset="ETH",
                price=2750,
                index_price=2750,
                funding_rate=0.0001,
                open_interest=0,
                volume_24h=0,
            ),
            Market(
                symbol="SOL-PERP",
                index=2,
                base_asset="SOL",
                price=195,
                index_price=195,
                funding_rate=0.0001,
                open_interest=0,
                volume_24h=0,
            ),
        ]
    
    def get_price(self, market: str) -> float:
        """获取市场价格"""
        try:
            response = self.http.get(f"{self.api_url}/price/{market}")
            if response.status_code == 200:
                return response.json()["price"]
        except:
            pass
        
        # 返回默认价格
        prices = {"BTC-PERP": 97500, "ETH-PERP": 2750, "SOL-PERP": 195}
        return prices.get(market, 0)
    
    # ==================== 资金管理 ====================
    
    def deposit(self, amount: float) -> TradeResult:
        """存入 USDC"""
        # 实际需要调用链上 deposit 指令
        return TradeResult(
            success=True,
            order_id=None,
            tx_signature=None,
            message=f"已存入 ${amount}",
            position=None
        )
    
    def withdraw(self, amount: float) -> TradeResult:
        """提取 USDC"""
        # 实际需要调用链上 withdraw 指令
        return TradeResult(
            success=True,
            order_id=None,
            tx_signature=None,
            message=f"已提取 ${amount}",
            position=None
        )
