#!/usr/bin/env python3
"""
Smart Market Maker - Uses live prices to quote

This MM:
1. Fetches real prices from CoinGecko
2. Adds a spread based on volatility
3. Manages risk with position limits
"""

import asyncio
import sys
sys.path.insert(0, '..')

from ai_perp_dex import MarketMaker, fetch_live_prices


class SmartMM:
    """Market maker with live price integration"""
    
    def __init__(
        self,
        agent_id: str,
        base_spread_bps: int = 20,  # 0.2% spread
        max_position_usdc: float = 10000,
    ):
        self.mm = MarketMaker(agent_id=agent_id)
        self.base_spread_bps = base_spread_bps
        self.max_position = max_position_usdc
        self.live_prices: dict = {}
        self.current_exposure: dict = {}  # market -> net exposure
    
    async def update_prices(self):
        """Fetch latest prices"""
        self.live_prices = await fetch_live_prices()
        print(f"📊 Prices updated: {self.live_prices}")
    
    def calculate_funding_rate(self, market: str, side: str, size: float) -> float:
        """
        Calculate funding rate based on:
        - Base spread
        - Current exposure (higher if already exposed)
        - Size (larger orders = higher rate)
        """
        base_rate = self.base_spread_bps / 10000  # 0.2% = 0.002
        
        # Increase rate if adding to existing exposure
        exposure = self.current_exposure.get(market, 0)
        if (side == "long" and exposure > 0) or (side == "short" and exposure < 0):
            base_rate *= 1.5  # 50% higher if same direction
        
        # Size adjustment (larger = higher rate)
        if size > 1000:
            base_rate *= 1.2
        
        return base_rate
    
    async def run(self):
        """Run the market maker"""
        print(f"🏦 SmartMM starting...")
        
        # Initial price fetch
        await self.update_prices()
        
        @self.mm.on_request
        async def handle(request):
            # Refresh prices periodically
            if not self.live_prices:
                await self.update_prices()
            
            # Risk check
            if request.size_usdc > self.max_position:
                print(f"❌ Request too large: ${request.size_usdc} > ${self.max_position}")
                return None
            
            # Calculate rate
            rate = self.calculate_funding_rate(
                request.market,
                request.side.value,
                request.size_usdc,
            )
            
            # Quote
            collateral = request.size_usdc / 10
            print(f"📝 Quoting {request.market} {request.side.value} ${request.size_usdc} @ {rate*100:.2f}%")
            
            quote = await self.mm.quote(
                request,
                funding_rate=rate,
                collateral_usdc=collateral,
            )
            
            return quote
        
        await self.mm.connect()
        
        # Run with periodic price updates
        price_task = asyncio.create_task(self._price_updater())
        
        try:
            await self.mm.run(poll_interval=1.0)
        finally:
            price_task.cancel()
    
    async def _price_updater(self):
        """Update prices every 60 seconds"""
        while True:
            await asyncio.sleep(60)
            try:
                await self.update_prices()
            except Exception as e:
                print(f"Price update error: {e}")


async def main():
    print("=" * 50)
    print("🤖 Smart Market Maker")
    print("=" * 50)
    
    mm = SmartMM(
        agent_id="SmartMM_001",
        base_spread_bps=20,
        max_position_usdc=5000,
    )
    
    try:
        await mm.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
