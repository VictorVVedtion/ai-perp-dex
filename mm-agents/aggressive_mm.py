#!/usr/bin/env python3
"""
Aggressive Market Maker Agent

A high-frequency market making strategy focused on:
- Tight spreads (0.3-0.5%)
- High leverage tolerance
- Large position limits
- All markets

Higher risk, higher reward strategy.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent-sdk', 'python'))

from ai_perp_dex.p2p import P2PClient, MarketMakerAgent, TradeRequest, Position
from ai_perp_dex.types import MarketSymbol as Market, Side


class AggressiveMMAgent(MarketMakerAgent):
    """
    Aggressive Market Maker - Compete on price
    
    Strategy:
    - Tight spreads to win more quotes
    - Accept all markets and higher leverage
    - Hedge directional exposure
    """
    
    def __init__(
        self,
        client: P2PClient,
        spread_bps: int = 30,
        max_position_size: float = 50000.0,
    ):
        super().__init__(
            client=client,
            spread_bps=spread_bps,
            max_position_size=max_position_size,
            min_collateral_ratio=0.5
        )
        
        # Track directional exposure per market
        self.net_exposure: Dict[Market, float] = {
            Market.BTC_PERP: 0.0,
            Market.ETH_PERP: 0.0,
            Market.SOL_PERP: 0.0,
        }
    
    def calculate_funding_rate(self, request: TradeRequest) -> float:
        """
        Aggressive pricing:
        - Tight base spread
        - Incentivize positions that hedge our exposure
        """
        base_rate = self.spread_bps / 10000
        
        # Check current exposure in this market
        current_exposure = self.net_exposure.get(request.market, 0.0)
        
        # If their trade hedges our exposure, offer better rate
        if request.side == Side.LONG and current_exposure > 0:
            # We're net short, they go long = hedging
            hedge_discount = min(0.001, abs(current_exposure) / self.max_position_size * 0.002)
            base_rate -= hedge_discount
        elif request.side == Side.SHORT and current_exposure < 0:
            # We're net long, they go short = hedging
            hedge_discount = min(0.001, abs(current_exposure) / self.max_position_size * 0.002)
            base_rate -= hedge_discount
        else:
            # Increasing exposure, add premium
            exposure_premium = abs(current_exposure) / self.max_position_size * 0.001
            base_rate += exposure_premium
        
        # Leverage is fine, minimal adjustment
        base_rate += request.leverage * 0.0001
        
        # Size adjustment
        base_rate += (request.size_usdc / self.max_position_size) * 0.001
        
        return max(0.001, min(base_rate, 0.02))  # 0.1% - 2% range
    
    def should_quote(self, request: TradeRequest) -> bool:
        """Quote for everything within limits."""
        if request.agent_id == self.client.agent_id:
            return False
        
        # Check total exposure limit
        total_exposure = sum(abs(v) for v in self.net_exposure.values())
        if total_exposure + request.size_usdc > self.max_position_size:
            print(f"Skipping: would exceed max exposure ({total_exposure}/${self.max_position_size})")
            return False
        
        return True
    
    async def handle_position_opened(self, position: Position):
        """Track net exposure."""
        await super().handle_position_opened(position)
        
        if position.mm_agent == self.client.agent_id:
            # MM is always on opposite side of trader
            exposure_delta = position.size_usdc
            if position.side == Side.LONG:
                # Trader is long, we are short
                exposure_delta = -exposure_delta
            
            self.net_exposure[position.market] = \
                self.net_exposure.get(position.market, 0.0) + exposure_delta
            
            print(f"📊 Net exposure {position.market.value}: ${self.net_exposure[position.market]:.2f}")
    
    async def handle_position_closed(self, position_id: str, pnl_trader: float, pnl_mm: float):
        """Update exposure on close."""
        if position_id in self.positions:
            position = self.positions[position_id]
            
            # Reverse the exposure
            exposure_delta = position.size_usdc
            if position.side == Side.LONG:
                exposure_delta = -exposure_delta
            
            self.net_exposure[position.market] = \
                self.net_exposure.get(position.market, 0.0) - exposure_delta
        
        await super().handle_position_closed(position_id, pnl_trader, pnl_mm)
    
    async def handle_trade_request(self, request: TradeRequest):
        """Quick quoting - no delay."""
        if not self.should_quote(request):
            return
        
        funding_rate = self.calculate_funding_rate(request)
        
        if funding_rate > request.max_funding_rate:
            return
        
        collateral = request.size_usdc / request.leverage * self.min_collateral_ratio
        
        try:
            quote = await self.client.submit_quote(
                request_id=request.id,
                funding_rate=funding_rate,
                collateral_usdc=collateral,
                valid_for=5  # Shorter validity
            )
            print(f"⚡ Quote {quote.id[:8]}... @ {funding_rate:.4f} for ${request.size_usdc:.0f}")
        except Exception as e:
            print(f"❌ Quote failed: {e}")


async def main():
    print("=" * 50)
    print("⚡ Aggressive Market Maker Agent")
    print("=" * 50)
    
    agent_id = f"aggressive_mm_{datetime.now().strftime('%H%M%S')}"
    
    async with P2PClient(
        ws_url=os.getenv("WS_URL", "ws://localhost:8080/ws"),
        rest_url=os.getenv("REST_URL", "http://localhost:8080"),
        agent_id=agent_id
    ) as client:
        agent = AggressiveMMAgent(
            client=client,
            spread_bps=30,            # 0.3% spread
            max_position_size=50000,  # $50k max exposure
        )
        
        print(f"\n📊 Configuration:")
        print(f"   Agent ID: {agent_id}")
        print(f"   Spread: {agent.spread_bps} bps")
        print(f"   Max Position: ${agent.max_position_size:.2f}")
        print(f"\n🔄 Ready to compete...\n")
        
        try:
            await agent.run()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
