#!/usr/bin/env python3
"""
Conservative Market Maker Agent

A cautious market making strategy focused on:
- Wide spreads (1-2%)
- Low leverage positions
- Strict position limits
- Only quoting stable markets

Use this as a starting point for more sophisticated strategies.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent-sdk', 'python'))

from ai_perp_dex.p2p import P2PClient, MarketMakerAgent, TradeRequest
from ai_perp_dex.types import MarketSymbol as Market


class ConservativeMMAgent(MarketMakerAgent):
    """
    Conservative Market Maker
    
    Parameters:
        spread_bps: Base spread in basis points (default: 100 = 1%)
        max_position_size: Maximum total position exposure (default: $5000)
        max_leverage: Maximum leverage to accept (default: 20x)
        allowed_markets: Markets to quote (default: BTC only)
    """
    
    def __init__(
        self,
        client: P2PClient,
        spread_bps: int = 100,
        max_position_size: float = 5000.0,
        max_leverage: int = 20,
        allowed_markets: Optional[list] = None
    ):
        super().__init__(
            client=client,
            spread_bps=spread_bps,
            max_position_size=max_position_size,
            min_collateral_ratio=0.8  # Conservative: 80% of required margin
        )
        self.max_leverage = max_leverage
        self.allowed_markets = allowed_markets or [Market.BTC_PERP]
    
    def should_quote(self, request: TradeRequest) -> bool:
        """Only quote for allowed markets and safe leverage."""
        # Base checks
        if not super().should_quote(request):
            return False
        
        # Market filter
        if request.market not in self.allowed_markets:
            print(f"Skipping {request.market}: not in allowed markets")
            return False
        
        # Leverage filter
        if request.leverage > self.max_leverage:
            print(f"Skipping request: leverage {request.leverage}x > max {self.max_leverage}x")
            return False
        
        return True
    
    def calculate_funding_rate(self, request: TradeRequest) -> float:
        """
        Conservative pricing:
        - Higher base spread
        - Aggressive size penalty
        - Leverage multiplier
        """
        base_rate = self.spread_bps / 10000
        
        # Leverage risk premium
        leverage_premium = (request.leverage / 10) * 0.005  # 0.5% per 10x
        
        # Size risk premium (exponential)
        size_ratio = request.size_usdc / self.max_position_size
        size_premium = (size_ratio ** 2) * 0.01  # Up to 1% for max size
        
        # Current exposure adjustment
        current_exposure = sum(p.size_usdc for p in self.positions.values())
        exposure_ratio = current_exposure / self.max_position_size
        exposure_premium = exposure_ratio * 0.005  # Wider spread when exposed
        
        total_rate = base_rate + leverage_premium + size_premium + exposure_premium
        
        return min(total_rate, 0.05)  # Cap at 5%
    
    async def handle_trade_request(self, request: TradeRequest):
        """Log and handle trade requests."""
        print(f"\n📩 New trade request:")
        print(f"   Market: {request.market.value}")
        print(f"   Side: {request.side.value}")
        print(f"   Size: ${request.size_usdc:.2f}")
        print(f"   Leverage: {request.leverage}x")
        print(f"   Max Rate: {request.max_funding_rate:.4f}")
        
        await super().handle_trade_request(request)


async def main():
    print("=" * 50)
    print("🤖 Conservative Market Maker Agent")
    print("=" * 50)
    
    agent_id = f"conservative_mm_{datetime.now().strftime('%H%M%S')}"
    
    async with P2PClient(
        ws_url=os.getenv("WS_URL", "ws://localhost:8080/ws"),
        rest_url=os.getenv("REST_URL", "http://localhost:8080"),
        agent_id=agent_id
    ) as client:
        agent = ConservativeMMAgent(
            client=client,
            spread_bps=100,          # 1% spread
            max_position_size=5000,  # $5k max exposure
            max_leverage=20,         # Max 20x leverage
            allowed_markets=[Market.BTC_PERP, Market.ETH_PERP]
        )
        
        print(f"\n📊 Configuration:")
        print(f"   Agent ID: {agent_id}")
        print(f"   Spread: {agent.spread_bps} bps")
        print(f"   Max Position: ${agent.max_position_size:.2f}")
        print(f"   Max Leverage: {agent.max_leverage}x")
        print(f"   Markets: {[m.value for m in agent.allowed_markets]}")
        print(f"\n🔄 Listening for trade requests...\n")
        
        try:
            await agent.run()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
