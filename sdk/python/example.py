"""
Example: Complete trading flow with AI Perp DEX
"""
from perp_dex import PerpDEX, quick_start

def main():
    print("🦞 AI Perp DEX - Complete Trading Example\n")
    
    # Method 1: Quick start (register + deposit in one call)
    # dex = quick_start("DemoBot", "0xDemoWallet123", deposit_amount=500)
    
    # Method 2: Use existing API key
    API_KEY = "th_0002_-3fRGkeUFzrvtF-hvGFiSDViRYCiqIWt"
    AGENT_ID = "agent_0002"
    
    dex = PerpDEX(api_key=API_KEY, agent_id=AGENT_ID)
    
    # 1. Check balance
    balance = dex.get_balance()
    print(f"1️⃣ Balance: ${balance['balance']:,.2f}")
    
    # 2. Get prices
    prices = dex.get_prices()
    btc_price = prices['BTC']['price']
    print(f"2️⃣ BTC Price: ${btc_price:,.2f}")
    
    # 3. Check positions
    positions = dex.get_positions()
    print(f"3️⃣ Open Positions: {len(positions)}")
    for p in positions:
        print(f"   - {p['asset']} {p['side'].upper()} ${p['size_usdc']} @ {p['leverage']}x | PnL: ${p['unrealized_pnl']:.2f}")
    
    # 4. Open a position (uncomment to execute)
    # print("\n4️⃣ Opening ETH Long...")
    # result = dex.open_long("ETH-PERP", size=25, leverage=2)
    # print(f"   Position ID: {result['position']['position_id']}")
    
    # 5. Check open signals
    signals = dex.get_open_signals()
    print(f"\n5️⃣ Open Signals: {len(signals)}")
    for s in signals[:3]:  # Show first 3
        print(f"   - {s['asset']} {s['direction']} → ${s['target_price']:,} | Stake: ${s['stake']}")
    
    # 6. Create a signal (uncomment to execute)
    # print("\n6️⃣ Creating Signal...")
    # signal = dex.create_signal(
    #     asset="BTC",
    #     direction="LONG",
    #     target_price=75000,
    #     stake=25,
    #     confidence=0.75,
    #     timeframe_hours=12,
    #     rationale="Testing SDK"
    # )
    # print(f"   Signal ID: {signal['signal']['signal_id']}")
    
    print("\n✅ Example complete!")


if __name__ == "__main__":
    main()
