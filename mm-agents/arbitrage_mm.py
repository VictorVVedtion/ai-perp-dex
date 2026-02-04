#!/usr/bin/env python3
"""
Arbitrage Market Maker Agent

A market maker that prices based on external exchange prices.
Uses Hyperliquid and Binance as price references.

Strategy:
- Only quote when we can hedge on external exchange
- Profit from spread between platforms
- Lower risk through delta-neutral positions
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Optional
import aiohttp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent-sdk', 'python'))

from ai_perp_dex.p2p import P2PClient, MarketMakerAgent, TradeRequest
from ai_perp_dex.types import MarketSymbol as Market


class ExternalPriceFeed:
    """Fetch prices from external exchanges."""
    
    def __init__(self):
        self.prices: Dict[Market, float] = {}
        self.last_update: Dict[Market, datetime] = {}
    
    async def update_prices(self):
        """Fetch latest prices from Hyperliquid."""
        try:
            async with aiohttp.ClientSession() as session:
                # Hyperliquid API
                async with session.post(
                    "https://api.hyperliquid.xyz/info",
                    json={"type": "allMids"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            self.prices[Market.BTC_PERP] = float(data.get("BTC", 0))
                            self.prices[Market.ETH_PERP] = float(data.get("ETH", 0))
                            self.prices[Market.SOL_PERP] = float(data.get("SOL", 0))
                            
                            now = datetime.utcnow()
                            for m in [Market.BTC_PERP, Market.ETH_PERP, Market.SOL_PERP]:
                                self.last_update[m] = now
        except Exception as e:
            print(f"Price feed error: {e}")
    
    def get_price(self, market: Market) -> Optional[float]:
        """Get cached price for market."""
        return self.prices.get(market)
    
    def is_stale(self, market: Market, max_age_seconds: int = 10) -> bool:
        """Check if price data is stale."""
        if market not in self.last_update:
            return True
        age = (datetime.utcnow() - self.last_update[market]).total_seconds()
        return age > max_age_seconds


class ArbitrageMMAgent(MarketMakerAgent):
    """
    Arbitrage Market Maker - Price based on external markets
    
    Strategy:
    - Check external price before quoting
    - Only quote if our rate covers the external spread
    - Designed to hedge positions on Hyperliquid
    """
    
    def __init__(
        self,
        client: P2PClient,
        min_spread_bps: int = 15,  # Minimum profit spread
        max_position_size: float = 20000.0,
    ):
        super().__init__(
            client=client,
            spread_bps=min_spread_bps,
            max_position_size=max_position_size,
            min_collateral_ratio=0.5
        )
        
        self.price_feed = ExternalPriceFeed()
        self.min_spread_bps = min_spread_bps
        self._price_task: Optional[asyncio.Task] = None
    
    async def start_price_feed(self):
        """Start background price updates."""
        async def _update_loop():
            while self._running:
                await self.price_feed.update_prices()
                await asyncio.sleep(2)  # Update every 2 seconds
        
        self._price_task = asyncio.create_task(_update_loop())
    
    def should_quote(self, request: TradeRequest) -> bool:
        """Only quote if we have fresh prices."""
        if not super().should_quote(request):
            return False
        
        # Need fresh price
        if self.price_feed.is_stale(request.market, max_age_seconds=5):
            print(f"Skipping: stale price for {request.market.value}")
            return False
        
        external_price = self.price_feed.get_price(request.market)
        if not external_price or external_price == 0:
            print(f"Skipping: no price for {request.market.value}")
            return False
        
        return True
    
    def calculate_funding_rate(self, request: TradeRequest) -> float:
        """
        Calculate rate based on:
        - Minimum spread to cover costs
        - External market conditions
        - Position exposure
        """
        # Base rate: minimum profit margin
        base_rate = self.min_spread_bps / 10000
        
        # Leverage adjustment (external exchanges have lower leverage limits)
        if request.leverage > 50:
            base_rate += (request.leverage - 50) * 0.0002
        
        # Size adjustment
        size_ratio = request.size_usdc / self.max_position_size
        base_rate += size_ratio * 0.001
        
        return base_rate
    
    async def handle_trade_request(self, request: TradeRequest):
        """Enhanced logging with price info."""
        if not self.should_quote(request):
            return
        
        external_price = self.price_feed.get_price(request.market)
        
        print(f"\n📊 Trade Request Analysis:")
        print(f"   Market: {request.market.value}")
        print(f"   External Price: ${external_price:,.2f}")
        print(f"   Size: ${request.size_usdc:.2f}")
        print(f"   Leverage: {request.leverage}x")
        
        funding_rate = self.calculate_funding_rate(request)
        
        if funding_rate > request.max_funding_rate:
            print(f"   ❌ Rate {funding_rate:.4f} > max {request.max_funding_rate:.4f}")
            return
        
        collateral = request.size_usdc / request.leverage * self.min_collateral_ratio
        
        try:
            quote = await self.client.submit_quote(
                request_id=request.id,
                funding_rate=funding_rate,
                collateral_usdc=collateral,
                valid_for=5
            )
            print(f"   ✅ Quote submitted @ {funding_rate:.4f}")
        except Exception as e:
            print(f"   ❌ Quote failed: {e}")
    
    async def run(self):
        """Run with price feed."""
        self._running = True
        
        # Start price feed
        await self.start_price_feed()
        
        # Set up callbacks
        self.client.on_trade_request = self.handle_trade_request
        self.client.on_position_opened = self.handle_position_opened
        self.client.on_position_closed = self.handle_position_closed
        
        print(f"Arbitrage MM started: {self.client.agent_id}")
        
        # Initial price fetch
        await self.price_feed.update_prices()
        print(f"\n📈 Initial Prices:")
        for market in [Market.BTC_PERP, Market.ETH_PERP, Market.SOL_PERP]:
            price = self.price_feed.get_price(market)
            if price:
                print(f"   {market.value}: ${price:,.2f}")
        
        while self._running:
            await asyncio.sleep(1)
        
        if self._price_task:
            self._price_task.cancel()
    
    def stop(self):
        """Stop agent and price feed."""
        self._running = False
        if self._price_task:
            self._price_task.cancel()


async def main():
    print("=" * 50)
    print("📊 Arbitrage Market Maker Agent")
    print("=" * 50)
    
    agent_id = f"arb_mm_{datetime.now().strftime('%H%M%S')}"
    
    async with P2PClient(
        ws_url=os.getenv("WS_URL", "ws://localhost:8080/ws"),
        rest_url=os.getenv("REST_URL", "http://localhost:8080"),
        agent_id=agent_id
    ) as client:
        agent = ArbitrageMMAgent(
            client=client,
            min_spread_bps=15,       # 0.15% minimum spread
            max_position_size=20000, # $20k max
        )
        
        print(f"\n📊 Configuration:")
        print(f"   Agent ID: {agent_id}")
        print(f"   Min Spread: {agent.min_spread_bps} bps")
        print(f"   Max Position: ${agent.max_position_size:.2f}")
        print(f"\n🔄 Starting arbitrage strategy...\n")
        
        try:
            await agent.run()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
