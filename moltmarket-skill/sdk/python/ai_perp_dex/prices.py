"""Real-time price feeds for AI Perp DEX"""

import asyncio
from typing import Dict, Optional
import httpx


class PriceFeed:
    """Fetch real-time crypto prices from CoinGecko"""
    
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    
    # Map our market symbols to CoinGecko IDs
    MARKET_MAP = {
        "BTC-PERP": "bitcoin",
        "ETH-PERP": "ethereum",
        "SOL-PERP": "solana",
    }
    
    def __init__(self, timeout: float = 10.0):
        self._http = httpx.AsyncClient(timeout=timeout)
        self._cache: Dict[str, float] = {}
        self._last_update: Optional[float] = None
    
    async def close(self):
        await self._http.aclose()
    
    async def get_price(self, market: str) -> Optional[float]:
        """Get current price for a market"""
        coin_id = self.MARKET_MAP.get(market)
        if not coin_id:
            return None
        
        try:
            r = await self._http.get(
                f"{self.COINGECKO_URL}/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"}
            )
            data = r.json()
            return data.get(coin_id, {}).get("usd")
        except Exception:
            return self._cache.get(market)
    
    async def get_all_prices(self) -> Dict[str, float]:
        """Get prices for all supported markets"""
        coin_ids = ",".join(self.MARKET_MAP.values())
        
        try:
            r = await self._http.get(
                f"{self.COINGECKO_URL}/simple/price",
                params={"ids": coin_ids, "vs_currencies": "usd"}
            )
            data = r.json()
            
            prices = {}
            for market, coin_id in self.MARKET_MAP.items():
                if coin_id in data:
                    prices[market] = data[coin_id]["usd"]
                    self._cache[market] = prices[market]
            
            return prices
        except Exception:
            return self._cache


async def fetch_live_prices() -> Dict[str, float]:
    """Quick helper to fetch current prices"""
    feed = PriceFeed()
    try:
        return await feed.get_all_prices()
    finally:
        await feed.close()


if __name__ == "__main__":
    async def main():
        print("Fetching live prices...")
        prices = await fetch_live_prices()
        for market, price in prices.items():
            print(f"  {market}: ${price:,.2f}")
    
    asyncio.run(main())
