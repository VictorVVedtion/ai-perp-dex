#!/usr/bin/env python3
"""
AI Perp DEX - Full Trading Demo

This demonstrates the complete trading flow:
1. Trader creates a trade request
2. Market Maker provides a quote
3. Trader accepts the quote (position opens)
4. Trader closes the position
"""

import asyncio
import sys
sys.path.insert(0, '..')

from ai_perp_dex import TradingAgent, MarketMaker


async def main():
    print("=" * 50)
    print("🤖 AI Perp DEX - Full Trading Demo")
    print("=" * 50)
    
    # Initialize agents
    trader = TradingAgent(agent_id="Demo_Trader")
    mm_client = trader._client  # Share client for demo (normally separate)
    
    # 1. Get available markets
    print("\n📊 Available Markets:")
    markets = await trader.get_markets()
    for m in markets:
        print(f"   • {m.symbol}: ${m.price:,.2f}")
    
    # 2. Create a trade request
    print("\n📝 Creating Trade Request...")
    request = await trader._client.create_request(
        market="BTC-PERP",
        side="long",
        size_usdc=500,
        leverage=5,
    )
    print(f"   Request ID: {request.id[:8]}...")
    print(f"   Market: {request.market}")
    print(f"   Side: {request.side.value}")
    print(f"   Size: ${request.size_usdc}")
    print(f"   Leverage: {request.leverage}x")
    
    # 3. Market Maker provides quote
    print("\n🏦 Market Maker Quoting...")
    mm_client.agent_id = "Demo_MM"
    quote = await mm_client.create_quote(
        request_id=request.id,
        funding_rate=0.01,  # 1% per day
        collateral_usdc=50,
    )
    print(f"   Quote ID: {quote.id[:8]}...")
    print(f"   Funding Rate: {quote.funding_rate * 100}%")
    print(f"   Collateral: ${quote.collateral_usdc}")
    
    # 4. Trader accepts quote
    print("\n✅ Accepting Quote...")
    mm_client.agent_id = "Demo_Trader"
    position = await mm_client.accept_quote(quote.id, request_id=request.id)
    print(f"   Position ID: {position.id[:8]}...")
    print(f"   Entry Price: ${position.entry_price:,.2f}")
    print(f"   Size: ${position.size_usdc}")
    
    # 5. Check positions
    print("\n📈 Current Positions:")
    positions = await trader.get_positions()
    for p in positions:
        print(f"   • {p.market} {p.side.value.upper()} ${p.size_usdc} @ ${p.entry_price:,.2f}")
    
    # 6. Close position
    print("\n🔒 Closing Position...")
    result = await trader.close(position.id)
    data = result.get("data", {})
    print(f"   Status: {data.get('status')}")
    print(f"   Trader PnL: ${data.get('pnl_trader', 0):.2f}")
    print(f"   MM PnL: ${data.get('pnl_mm', 0):.2f}")
    
    # Cleanup
    await trader._client.close()
    
    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
