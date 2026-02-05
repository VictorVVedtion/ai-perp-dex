"""
Price Feed Service
实时价格源，让 Agent 的决策基于真实市场

数据源:
- CoinGecko (免费)
- Hyperliquid (实时)
- Binance (备用)
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

@dataclass
class Price:
    """价格数据"""
    asset: str
    price: float
    change_24h: float = 0.0
    volume_24h: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    
    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "price": self.price,
            "change_24h": self.change_24h,
            "volume_24h": self.volume_24h,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

class PriceFeed:
    """
    实时价格源
    
    用法:
        feed = PriceFeed()
        await feed.start()
        
        # 获取价格
        btc = await feed.get_price("BTC")
        
        # 订阅价格更新
        @feed.on_price_update
        async def handle(price):
            print(f"{price.asset}: ${price.price}")
    """
    
    # 资产映射
    ASSET_MAP = {
        "BTC": {"coingecko": "bitcoin", "symbol": "BTC"},
        "BTC-PERP": {"coingecko": "bitcoin", "symbol": "BTC"},
        "ETH": {"coingecko": "ethereum", "symbol": "ETH"},
        "ETH-PERP": {"coingecko": "ethereum", "symbol": "ETH"},
        "SOL": {"coingecko": "solana", "symbol": "SOL"},
        "SOL-PERP": {"coingecko": "solana", "symbol": "SOL"},
    }
    
    def __init__(self, update_interval: int = 30):
        self.update_interval = update_interval
        self.session: Optional[aiohttp.ClientSession] = None
        self._running = False
        
        # 价格缓存
        self.prices: Dict[str, Price] = {}
        self._last_update: Optional[datetime] = None
        
        # 回调
        self._callbacks: List[Callable] = []
        
        # 数据源 URL
        self.sources = {
            "coingecko": "https://api.coingecko.com/api/v3",
            "hyperliquid": "https://api.hyperliquid.xyz/info",
            "binance": "https://api.binance.com/api/v3",
        }
    
    async def start(self):
        """启动价格源"""
        self.session = aiohttp.ClientSession()
        self._running = True
        
        # 立即获取一次价格
        await self._update_all_prices()
        
        # 启动后台更新
        asyncio.create_task(self._update_loop())
        
        print(f"📈 Price Feed started (update every {self.update_interval}s)")
    
    async def stop(self):
        """停止价格源"""
        self._running = False
        if self.session:
            await self.session.close()
    
    async def _update_loop(self):
        """后台更新循环"""
        while self._running:
            await asyncio.sleep(self.update_interval)
            await self._update_all_prices()
    
    async def _update_all_prices(self):
        """更新所有价格"""
        try:
            # 确保 session 存在
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # 优先使用 Hyperliquid (无频率限制)
            prices = await self._fetch_hyperliquid()
            
            # 如果 Hyperliquid 失败，用 CoinGecko
            if not prices:
                prices = await self._fetch_coingecko()
            
            # 如果都失败，用默认价格
            if not prices:
                prices = {
                    "BTC": Price(asset="BTC", price=73000, source="default"),
                    "ETH": Price(asset="ETH", price=2150, source="default"),
                    "SOL": Price(asset="SOL", price=92, source="default"),
                }
            
            # 更新缓存
            for asset, price in prices.items():
                self.prices[asset] = price
                self.prices[f"{asset}-PERP"] = Price(
                    asset=f"{asset}-PERP",
                    price=price.price,
                    change_24h=price.change_24h,
                    volume_24h=price.volume_24h,
                    timestamp=price.timestamp,
                    source=price.source,
                )
            
            self._last_update = datetime.now()
            
            # 触发回调
            for callback in self._callbacks:
                for price in self.prices.values():
                    try:
                        await callback(price)
                    except:
                        pass
                        
        except Exception as e:
            print(f"⚠️ Price update error: {e}")
            # 使用默认价格
            for asset, default_price in [("BTC", 73000), ("ETH", 2150), ("SOL", 92)]:
                self.prices[asset] = Price(asset=asset, price=default_price, source="fallback")
                self.prices[f"{asset}-PERP"] = Price(asset=f"{asset}-PERP", price=default_price, source="fallback")
    
    async def _fetch_coingecko(self) -> Dict[str, Price]:
        """从 CoinGecko 获取价格"""
        prices = {}
        
        # 确保 session 存在
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        ids = ["bitcoin", "ethereum", "solana"]
        url = f"{self.sources['coingecko']}/simple/price"
        params = {
            "ids": ",".join(ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    mapping = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
                    
                    for cg_id, symbol in mapping.items():
                        if cg_id in data:
                            d = data[cg_id]
                            prices[symbol] = Price(
                                asset=symbol,
                                price=d.get("usd", 0),
                                change_24h=d.get("usd_24h_change", 0),
                                volume_24h=d.get("usd_24h_vol", 0),
                                source="coingecko",
                            )
                    print(f"✅ Prices updated from CoinGecko: BTC=${prices.get('BTC', Price('BTC',0)).price:,.0f}")
                else:
                    print(f"⚠️ CoinGecko returned status {resp.status}")
        except Exception as e:
            print(f"⚠️ CoinGecko error: {e}")
            # 使用备用数据
            await self._fetch_fallback(prices)
        
        return prices
    
    async def _fetch_hyperliquid(self) -> Dict[str, Price]:
        """主要价格源 (Hyperliquid - 无频率限制)"""
        prices = {}
        
        # 确保 session 存在
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                self.sources["hyperliquid"],
                json={"type": "allMids"},
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for symbol in ["BTC", "ETH", "SOL"]:
                        if symbol in data:
                            prices[symbol] = Price(
                                asset=symbol,
                                price=float(data[symbol]),
                                source="hyperliquid",
                            )
                    
                    if prices:
                        print(f"✅ Prices from Hyperliquid: BTC=${prices.get('BTC', Price('BTC',0)).price:,.0f}")
        except Exception as e:
            print(f"⚠️ Hyperliquid error: {e}")
        
        return prices
    
    async def _fetch_fallback(self, prices: Dict[str, Price]):
        """备用价格源"""
        await self._fetch_hyperliquid()  # 不再需要，但保留兼容性
    
    async def get_price(self, asset: str) -> Optional[Price]:
        """获取单个资产价格"""
        # 标准化资产名
        asset = asset.upper().replace("-PERP", "")
        
        if asset in self.prices:
            return self.prices[asset]
        
        # 如果缓存中没有，尝试获取
        await self._update_all_prices()
        return self.prices.get(asset)
    
    async def get_all_prices(self) -> Dict[str, Price]:
        """获取所有价格"""
        return self.prices.copy()
    
    def on_price_update(self, callback: Callable):
        """注册价格更新回调"""
        self._callbacks.append(callback)
        return callback
    
    def get_cached_price(self, asset: str) -> float:
        """同步获取缓存价格 (用于快速访问)"""
        asset = asset.upper().replace("-PERP", "")
        if asset in self.prices:
            return self.prices[asset].price
        # 默认价格
        defaults = {"BTC": 72000, "ETH": 2500, "SOL": 100}
        return defaults.get(asset, 0)


# 全局价格源实例
price_feed = PriceFeed()


async def demo():
    """演示价格源"""
    print("=" * 50)
    print("📈 PRICE FEED DEMO")
    print("=" * 50)
    
    feed = PriceFeed(update_interval=10)
    await feed.start()
    
    # 获取所有价格
    print("\n📊 Current Prices:")
    prices = await feed.get_all_prices()
    for asset, price in prices.items():
        if not asset.endswith("-PERP"):  # 避免重复显示
            print(f"   {asset}: ${price.price:,.2f} ({price.change_24h:+.2f}%)")
    
    # 订阅更新
    @feed.on_price_update
    async def on_update(price: Price):
        if not price.asset.endswith("-PERP"):
            print(f"   🔄 {price.asset}: ${price.price:,.2f}")
    
    print("\n⏳ Waiting for updates (10s)...")
    await asyncio.sleep(12)
    
    await feed.stop()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(demo())
