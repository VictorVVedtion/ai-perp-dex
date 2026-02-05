"""
Hyperliquid Client
真实的 Hyperliquid 交易客户端

使用官方 SDK: hyperliquid-python-sdk
支持 Builder Code 收取手续费
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from eth_account import Account

logger = logging.getLogger(__name__)

# Hyperliquid SDK
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

@dataclass
class HLPosition:
    """Hyperliquid 持仓"""
    coin: str
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: int
    liquidation_price: Optional[float] = None

@dataclass
class HLOrderResult:
    """Hyperliquid 订单结果"""
    success: bool
    order_id: Optional[str] = None
    filled_size: float = 0.0
    avg_price: float = 0.0
    fee: float = 0.0
    error: Optional[str] = None

class HyperliquidClient:
    """
    Hyperliquid 交易客户端
    
    用法:
        client = HyperliquidClient(private_key="0x...")
        client.connect()
        
        # 市价开多
        result = client.market_open("ETH", is_buy=True, size=0.1)
        
        # 市价平仓
        result = client.market_close("ETH")
        
        # 查询持仓
        positions = client.get_positions()
    """
    
    # Builder 地址 (用于收取额外手续费)
    # 可以设置成我们自己的地址来收取 builder fee
    BUILDER_ADDRESS = None  # 设置后可以收费
    BUILDER_FEE_BPS = 1     # 0.01% = 1 bps
    
    def __init__(
        self,
        private_key: str = None,
        testnet: bool = True,
        builder_address: str = None,
    ):
        """
        Args:
            private_key: 钱包私钥 (0x...)
            testnet: True = 测试网, False = 主网
            builder_address: Builder 地址 (可选，用于收费)
        """
        self.private_key = private_key or os.environ.get("HL_PRIVATE_KEY")
        self.testnet = testnet
        self.builder_address = builder_address or self.BUILDER_ADDRESS
        
        self.base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        
        self.info: Optional[Info] = None
        self.exchange: Optional[Exchange] = None
        self.address: Optional[str] = None
        
        self._connected = False
    
    def connect(self) -> bool:
        """连接到 Hyperliquid"""
        try:
            # 初始化 Info (不需要私钥)
            self.info = Info(self.base_url, skip_ws=True)
            
            if self.private_key:
                # 从私钥获取地址
                account = Account.from_key(self.private_key)
                self.address = account.address
                
                # 初始化 Exchange (需要私钥)
                self.exchange = Exchange(
                    account,
                    self.base_url,
                    account_address=self.address,
                )
                
                print(f"🔗 Hyperliquid connected: {self.address[:10]}...")
            else:
                print(f"🔗 Hyperliquid info-only mode (no private key)")
            
            self._connected = True
            return True
            
        except Exception as e:
            print(f"❌ Hyperliquid connection failed: {e}")
            return False
    
    def get_price(self, coin: str) -> float:
        """获取实时价格"""
        if not self.info:
            return 0
        
        try:
            mids = self.info.all_mids()
            return float(mids.get(coin, 0))
        except:
            return 0
    
    def get_all_prices(self) -> Dict[str, float]:
        """获取所有价格"""
        if not self.info:
            return {}
        
        try:
            mids = self.info.all_mids()
            return {k: float(v) for k, v in mids.items()}
        except:
            return {}
    
    def get_positions(self) -> list[HLPosition]:
        """获取所有持仓"""
        if not self.info or not self.address:
            return []
        
        try:
            user_state = self.info.user_state(self.address)
            positions = []
            
            for pos in user_state.get("assetPositions", []):
                p = pos.get("position", {})
                if float(p.get("szi", 0)) != 0:
                    positions.append(HLPosition(
                        coin=p.get("coin", ""),
                        size=float(p.get("szi", 0)),
                        entry_price=float(p.get("entryPx", 0)),
                        unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                        leverage=int(p.get("leverage", {}).get("value", 1)),
                        liquidation_price=float(p.get("liquidationPx", 0)) if p.get("liquidationPx") else None,
                    ))
            
            return positions
        except Exception as e:
            print(f"⚠️ Get positions error: {e}")
            return []
    
    def get_balance(self) -> Dict[str, float]:
        """获取账户余额"""
        if not self.info or not self.address:
            return {}
        
        try:
            user_state = self.info.user_state(self.address)
            margin = user_state.get("marginSummary", {})
            
            return {
                "account_value": float(margin.get("accountValue", 0)),
                "total_margin_used": float(margin.get("totalMarginUsed", 0)),
                "withdrawable": float(margin.get("withdrawable", 0)),
            }
        except:
            return {}
    
    def market_open(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        slippage: float = 0.01,
    ) -> HLOrderResult:
        """
        市价开仓
        
        Args:
            coin: 币种 (BTC, ETH, SOL, etc.)
            is_buy: True = 做多, False = 做空
            size: 数量 (币的数量，不是 USDC)
            slippage: 滑点容忍度 (0.01 = 1%)
        """
        if not self.exchange:
            return HLOrderResult(success=False, error="Not connected or no private key")
        
        try:
            # 构建 builder 参数
            builder = None
            if self.builder_address:
                builder = {"b": self.builder_address, "f": self.BUILDER_FEE_BPS}
            
            # 下单
            result = self.exchange.market_open(
                coin,
                is_buy,
                size,
                None,  # px (市价单不需要)
                slippage,
                builder=builder,
            )
            
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses:
                    status = statuses[0]
                    filled = status.get("filled", {})
                    return HLOrderResult(
                        success=True,
                        order_id=str(filled.get("oid", "")),
                        filled_size=float(filled.get("totalSz", 0)),
                        avg_price=float(filled.get("avgPx", 0)),
                        fee=0,  # 费用在后续查询
                    )
            
            return HLOrderResult(
                success=False,
                error=result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("error", "Unknown error"),
            )
            
        except Exception as e:
            return HLOrderResult(success=False, error=str(e))
    
    def market_close(self, coin: str, slippage: float = 0.01) -> HLOrderResult:
        """市价平仓"""
        if not self.exchange:
            return HLOrderResult(success=False, error="Not connected or no private key")
        
        try:
            result = self.exchange.market_close(coin, None, slippage)
            
            if result.get("status") == "ok":
                return HLOrderResult(success=True)
            
            return HLOrderResult(success=False, error=str(result))
            
        except Exception as e:
            return HLOrderResult(success=False, error=str(e))
    
    def limit_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        reduce_only: bool = False,
    ) -> HLOrderResult:
        """限价单"""
        if not self.exchange:
            return HLOrderResult(success=False, error="Not connected or no private key")
        
        try:
            order_type = {"limit": {"tif": "Gtc"}}
            if reduce_only:
                order_type["limit"]["reduce_only"] = True
            
            result = self.exchange.order(coin, is_buy, size, price, order_type)
            
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses and "resting" in statuses[0]:
                    return HLOrderResult(
                        success=True,
                        order_id=str(statuses[0]["resting"]["oid"]),
                    )
            
            return HLOrderResult(success=False, error=str(result))
            
        except Exception as e:
            return HLOrderResult(success=False, error=str(e))
    
    def cancel_order(self, coin: str, order_id: int) -> bool:
        """取消订单"""
        if not self.exchange:
            return False
        
        try:
            result = self.exchange.cancel(coin, order_id)
            return result.get("status") == "ok"
        except:
            return False


# 便捷函数
def get_hl_prices() -> Dict[str, float]:
    """快速获取所有价格 (不需要私钥)"""
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    return {k: float(v) for k, v in info.all_mids().items()}


async def demo():
    """演示 Hyperliquid 客户端"""
    print("=" * 50)
    print("🔗 HYPERLIQUID CLIENT DEMO")
    print("=" * 50)
    
    # Info-only 模式 (不需要私钥)
    client = HyperliquidClient(testnet=False)  # 主网获取价格
    client.connect()
    
    # 获取价格
    print("\n📊 Current Prices (Mainnet):")
    prices = client.get_all_prices()
    for coin in ["BTC", "ETH", "SOL"]:
        if coin in prices:
            print(f"   {coin}: ${prices[coin]:,.2f}")
    
    # 如果有私钥，可以查询持仓
    if client.address:
        print(f"\n👤 Account: {client.address}")
        
        balance = client.get_balance()
        print(f"   Value: ${balance.get('account_value', 0):,.2f}")
        print(f"   Withdrawable: ${balance.get('withdrawable', 0):,.2f}")
        
        positions = client.get_positions()
        if positions:
            print(f"\n📈 Positions:")
            for pos in positions:
                print(f"   {pos.coin}: {pos.size} @ ${pos.entry_price:,.2f} (PnL: ${pos.unrealized_pnl:,.2f})")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
