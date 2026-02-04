#!/usr/bin/env python3
"""
Demo: Two AI agents trading with each other.

This script runs:
1. A simple Market Maker that quotes all requests
2. A Trader that opens and closes positions

Run with: python examples/demo.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from ai_perp_dex import TradingAgent, MarketMaker, SimpleMarketMaker


async def run_mm():
    """Run a simple market maker"""
    print("🏦 Starting Market Maker...")
    
    mm = SimpleMarketMaker(
        agent_id="Demo_MM",
        spread_bps=15,  # 0.15% spread
        max_position=100000,
    )
    
    await mm.connect()
    print("🏦 MM connected, waiting for requests...")
    
    # Run for 60 seconds
    try:
        await asyncio.wait_for(mm.run(), timeout=60)
    except asyncio.TimeoutError:
        pass
    
    await mm.disconnect()
    print("🏦 MM stopped")


async def run_trader():
    """Run a trader that makes some trades"""
    # Wait for MM to start
    await asyncio.sleep(2)
    
    print("🤖 Starting Trader...")
    
    trader = TradingAgent(
        agent_id="Demo_Trader",
    )
    
    await trader.connect()
    print("🤖 Trader connected")
    
    # Get markets
    markets = await trader.get_markets()
    print(f"📊 Available markets: {[m.symbol for m in markets]}")
    
    # Open a long position on BTC
    print("\n🤖 Opening long BTC position...")
    try:
        position = await trader.open_long(
            market="BTC-PERP",
            size=500,
            leverage=5,
            timeout=10,
        )
        print(f"✅ Position opened: {position}")
    except TimeoutError:
        print("❌ No quotes received (MM might not be running)")
        await trader.disconnect()
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        await trader.disconnect()
        return
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Check positions
    positions = await trader.get_positions()
    print(f"\n📈 Current positions: {len(positions)}")
    for p in positions:
        print(f"   {p.market} {p.side.value.upper()} ${p.size_usdc} @ ${p.entry_price}")
    
    # Close all positions
    print("\n🤖 Closing all positions...")
    await trader.close_all()
    print("✅ All positions closed")
    
    await trader.disconnect()
    print("🤖 Trader stopped")


async def main():
    print("=" * 50)
    print("AI Perp DEX - Demo")
    print("=" * 50)
    print()
    
    # Run MM and Trader concurrently
    await asyncio.gather(
        run_mm(),
        run_trader(),
    )
    
    print()
    print("=" * 50)
    print("Demo complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
