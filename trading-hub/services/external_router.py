"""
External Router Service
当内部无法匹配时，路由到外部 DEX

支持的外部 DEX:
- Hyperliquid (主要)
- dYdX (备用)
"""

import asyncio
import aiohttp
import json
import hashlib
import time
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class ExternalVenue(Enum):
    HYPERLIQUID = "hyperliquid"
    DYDX = "dydx"
    SIMULATION = "simulation"  # 测试用

@dataclass
class ExternalFill:
    """外部成交结果"""
    venue: str
    order_id: str
    asset: str
    side: str  # buy/sell
    size: float
    price: float
    fee: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "venue": self.venue,
            "order_id": self.order_id,
            "asset": self.asset,
            "side": self.side,
            "size": self.size,
            "price": self.price,
            "fee": self.fee,
            "timestamp": self.timestamp.isoformat(),
        }

@dataclass
class RoutingResult:
    """路由结果"""
    total_size: float
    internal_fill: float = 0.0
    external_fill: float = 0.0
    internal_match_id: Optional[str] = None
    external_fills: List[ExternalFill] = field(default_factory=list)
    
    @property
    def internal_rate(self) -> float:
        if self.total_size == 0:
            return 0
        return self.internal_fill / self.total_size
    
    @property
    def total_fee(self) -> float:
        return sum(f.fee for f in self.external_fills)
    
    @property
    def fee_saved(self) -> float:
        """内部匹配省下的费用"""
        # Hyperliquid taker fee: 0.025%
        return self.internal_fill * 0.00025
    
    def to_dict(self) -> dict:
        return {
            "total_size": self.total_size,
            "internal_fill": self.internal_fill,
            "external_fill": self.external_fill,
            "internal_rate": f"{self.internal_rate:.1%}",
            "internal_match_id": self.internal_match_id,
            "external_fills": [f.to_dict() for f in self.external_fills],
            "total_fee": self.total_fee,
            "fee_saved": self.fee_saved,
        }

class ExternalRouter:
    """
    外部路由器
    
    职责:
    1. 当内部无法匹配时，路由到外部 DEX
    2. 支持部分匹配：内部匹配一部分，剩余外发
    3. 选择最优执行场所
    """
    
    # Hyperliquid API
    HL_API = "https://api.hyperliquid.xyz"
    HL_INFO = "https://api.hyperliquid.xyz/info"
    
    # 资产映射 (AI Perp DEX -> Hyperliquid)
    ASSET_MAP = {
        "BTC-PERP": "BTC", "ETH-PERP": "ETH", "SOL-PERP": "SOL",
        "DOGE-PERP": "DOGE", "PEPE-PERP": "PEPE", "WIF-PERP": "WIF",
        "ARB-PERP": "ARB", "OP-PERP": "OP", "SUI-PERP": "SUI",
        "AVAX-PERP": "AVAX", "LINK-PERP": "LINK", "AAVE-PERP": "AAVE",
    }
    
    # 费率
    FEES = {
        "hyperliquid": 0.00025,  # 0.025% taker
        "dydx": 0.0005,          # 0.05% taker
    }
    
    def __init__(self, simulation_mode: bool = None):
        """
        Args:
            simulation_mode: True = 模拟执行，False = 真实执行
                           None = 从环境变量 TRADING_MODE 读取
        """
        if simulation_mode is None:
            # 从环境变量读取
            mode = os.environ.get("TRADING_MODE", "sim").lower()
            self.simulation_mode = mode != "live"
        else:
            self.simulation_mode = simulation_mode
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 统计
        self.stats = {
            "total_routed": 0,
            "total_volume": 0.0,
            "total_fees": 0.0,
            "by_venue": {},
        }
    
    async def start(self):
        """启动路由器"""
        # 使用连接池优化并发性能
        connector = aiohttp.TCPConnector(
            limit=100,           # 总连接数限制
            limit_per_host=30,   # 每个主机连接限制
            ttl_dns_cache=300,   # DNS 缓存 5 分钟
        )
        self.session = aiohttp.ClientSession(connector=connector)
        print(f"🔀 External Router started (simulation={self.simulation_mode})")
    
    async def stop(self):
        """停止路由器"""
        if self.session:
            await self.session.close()
    
    async def route(
        self,
        asset: str,
        side: str,  # "long" or "short"
        size_usdc: float,
        leverage: int = 1,
        price: float = None,
    ) -> ExternalFill:
        """
        路由订单到外部 DEX
        
        Args:
            asset: 资产 (BTC-PERP, ETH-PERP, etc.)
            side: 方向 (long/short)
            size_usdc: 保证金大小 (USDC)
            leverage: 杠杆
            price: 限价 (None = 市价)
        
        Returns:
            ExternalFill: 成交结果
        """
        # 标准化
        hl_asset = self.ASSET_MAP.get(asset, asset.replace("-PERP", ""))
        hl_side = "buy" if side == "long" else "sell"
        notional = size_usdc * leverage
        
        if self.simulation_mode:
            return await self._simulate_fill(hl_asset, hl_side, notional, size_usdc)
        else:
            return await self._execute_hyperliquid(hl_asset, hl_side, notional, size_usdc, leverage, price)
    
    async def _simulate_fill(
        self,
        asset: str,
        side: str,
        notional: float,
        margin: float,
    ) -> ExternalFill:
        """模拟成交 (用于测试)"""
        
        # 获取真实价格
        price = await self._get_hl_price(asset)
        
        # 计算费用
        fee = notional * self.FEES["hyperliquid"]
        
        # 生成订单 ID
        order_id = f"sim_{int(time.time() * 1000)}"
        
        fill = ExternalFill(
            venue="hyperliquid_sim",
            order_id=order_id,
            asset=f"{asset}-PERP",
            side=side,
            size=margin,
            price=price,
            fee=fee,
        )
        
        # 更新统计
        self._update_stats("hyperliquid_sim", margin, fee)
        
        print(f"🔀 [Simulated] {side.upper()} {asset} ${margin:.2f} @ ${price:,.2f} (fee: ${fee:.4f})")
        
        return fill
    
    async def _execute_hyperliquid(
        self,
        asset: str,
        side: str,
        notional: float,
        margin: float,
        leverage: int,
        price: float = None,
    ) -> ExternalFill:
        """
        真实执行到 Hyperliquid
        
        需要设置环境变量: HL_PRIVATE_KEY
        """
        from services.hyperliquid_client import HyperliquidClient
        
        private_key = os.environ.get("HL_PRIVATE_KEY")
        if not private_key:
            raise ValueError("HL_PRIVATE_KEY not set. Use simulation_mode=True for testing.")
        
        # 创建客户端
        client = HyperliquidClient(
            private_key=private_key,
            testnet=False,  # 主网
        )
        client.connect()
        
        # 获取价格计算数量
        current_price = client.get_price(asset)
        if current_price == 0:
            raise ValueError(f"Could not get price for {asset}")
        
        # 计算币的数量 (notional / price)
        size = notional / current_price
        
        # 处理精度问题 - 每个币有最小精度
        size_precision = {
            "BTC": 4,  # 0.0001 BTC
            "ETH": 3,  # 0.001 ETH
            "SOL": 1,  # 0.1 SOL
        }
        decimals = size_precision.get(asset, 2)
        size = round(size, decimals)
        
        # 最小订单大小
        min_size = {
            "BTC": 0.001,
            "ETH": 0.01,
            "SOL": 0.1,
        }
        if size < min_size.get(asset, 0.01):
            size = min_size.get(asset, 0.01)
        
        # 下单
        is_buy = (side == "buy")
        result = client.market_open(asset, is_buy, size, slippage=0.01)
        
        if not result.success:
            raise Exception(f"Order failed: {result.error}")
        
        # 计算费用
        fee = notional * self.FEES["hyperliquid"]
        
        fill = ExternalFill(
            venue="hyperliquid",
            order_id=result.order_id or f"hl_{int(time.time() * 1000)}",
            asset=f"{asset}-PERP",
            side=side,
            size=margin,
            price=result.avg_price or current_price,
            fee=fee,
        )
        
        # 更新统计
        self._update_stats("hyperliquid", margin, fee)
        
        print(f"🔀 [REAL] {side.upper()} {asset} ${margin:.2f} @ ${fill.price:,.2f} (fee: ${fee:.4f})")
        
        return fill
    
    # 价格缓存 (类级别)
    _price_cache = {}
    _cache_time = 0
    _cache_ttl = 5  # 5秒缓存
    
    async def _get_hl_price(self, asset: str) -> float:
        """从 Hyperliquid 获取实时价格 (使用多级缓存)"""
        import time as _time
        now = _time.time()
        
        # 1. 检查本地缓存 (5秒有效)
        if asset in self._price_cache and now - self._cache_time < self._cache_ttl:
            return self._price_cache[asset]
        
        # 2. 尝试用全局 price_feed 缓存
        try:
            from services.price_feed import price_feed
            if price_feed and price_feed._prices:
                asset_perp = f"{asset}-PERP"
                if asset_perp in price_feed._prices:
                    price = price_feed._prices[asset_perp].get("price", 0)
                    if price > 0:
                        self._price_cache[asset] = price
                        self._cache_time = now
                        return price
        except Exception:
            pass
        
        # 3. 缓存未命中时才调用 API (并更新缓存)
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            mids = info.all_mids()
            
            # 更新所有价格缓存
            for k, v in mids.items():
                self._price_cache[k] = float(v)
            self._cache_time = now
            
            if asset in mids:
                return float(mids[asset])
        except Exception as e:
            print(f"⚠️ HL price error: {e}")
        
        # 4. 备用价格
        defaults = {"BTC": 65000, "ETH": 1900, "SOL": 90}
        return defaults.get(asset, 100)
    
    def _update_stats(self, venue: str, volume: float, fee: float):
        """更新统计"""
        self.stats["total_routed"] += 1
        self.stats["total_volume"] += volume
        self.stats["total_fees"] += fee
        
        if venue not in self.stats["by_venue"]:
            self.stats["by_venue"][venue] = {"count": 0, "volume": 0, "fees": 0}
        
        self.stats["by_venue"][venue]["count"] += 1
        self.stats["by_venue"][venue]["volume"] += volume
        self.stats["by_venue"][venue]["fees"] += fee
    
    def get_stats(self) -> dict:
        """获取路由统计"""
        return self.stats.copy()


# 全局实例
external_router = ExternalRouter(simulation_mode=True)


async def demo():
    """演示外部路由"""
    print("=" * 50)
    print("🔀 EXTERNAL ROUTER DEMO")
    print("=" * 50)
    
    router = ExternalRouter(simulation_mode=True)
    await router.start()
    
    # 测试路由
    test_orders = [
        ("BTC-PERP", "long", 100, 10),
        ("ETH-PERP", "short", 200, 5),
        ("SOL-PERP", "long", 50, 3),
    ]
    
    print("\n📤 Routing orders to external DEX:")
    for asset, side, size, leverage in test_orders:
        fill = await router.route(asset, side, size, leverage)
        print(f"   ✅ {fill.order_id}: {fill.side} {fill.asset} ${fill.size} @ ${fill.price:,.2f}")
    
    print("\n📊 Router Stats:")
    stats = router.get_stats()
    print(f"   Total routed: {stats['total_routed']}")
    print(f"   Total volume: ${stats['total_volume']:,.2f}")
    print(f"   Total fees: ${stats['total_fees']:.4f}")
    
    await router.stop()

if __name__ == "__main__":
    asyncio.run(demo())
