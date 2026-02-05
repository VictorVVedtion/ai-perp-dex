"""
AI Perp DEX - Python SDK Examples

This shows how an AI Agent can use the DEX.
"""

from perp_dex import PerpDEX, quick_start
import time


def example_basic():
    """Basic: Get prices without authentication"""
    print("=" * 50)
    print("Example 1: Get Prices (No Auth)")
    print("=" * 50)
    
    dex = PerpDEX()
    
    # Get all prices
    prices = dex.get_prices()
    print("\nCurrent Prices:")
    for asset in ["BTC", "ETH", "SOL"]:
        if asset in prices:
            print(f"  {asset}: ${prices[asset]['price']:,.2f}")
    
    # Get single price
    btc = dex.get_price("BTC")
    print(f"\nBTC Price: ${btc:,.2f}")


def example_register_and_trade():
    """Full flow: Register, deposit, trade"""
    print("\n" + "=" * 50)
    print("Example 2: Register and Trade")
    print("=" * 50)
    
    # Quick start - registers, deposits, returns ready client
    dex = quick_start(
        display_name="DemoBot",
        wallet=f"0xDemo{int(time.time())}",
        deposit_amount=1000
    )
    
    # Check balance
    balance = dex.get_balance()
    print(f"\nBalance: ${balance.get('available', 0):.2f}")
    
    # Open a long position
    print("\nOpening BTC long...")
    result = dex.open_long(
        asset="BTC-PERP",
        size=50,
        leverage=3
    )
    print(f"Position: {result.get('position', {}).get('position_id', 'N/A')}")
    
    # Get positions
    positions = dex.get_positions()
    print(f"Open positions: {len(positions)}")
    
    # Close position
    if positions:
        pos_id = positions[0].get('position_id')
        print(f"\nClosing position {pos_id}...")
        close_result = dex.close_position(pos_id)
        print(f"PnL: ${close_result.get('pnl', 0):.2f}")


def example_signal_betting():
    """Signal Betting: Create and fade signals"""
    print("\n" + "=" * 50)
    print("Example 3: Signal Betting")
    print("=" * 50)
    
    # Create two agents for betting
    agent1 = quick_start("SignalBot1", f"0xSig1{int(time.time())}", 500)
    agent2 = quick_start("SignalBot2", f"0xSig2{int(time.time())}", 500)
    
    # Agent 1 creates a signal
    print("\nAgent1 creates signal: BTC > $100K in 24h")
    signal = agent1.create_signal(
        asset="BTC-PERP",
        signal_type="price_above",
        target_value=100000,
        stake_amount=25,
        duration_hours=24
    )
    signal_id = signal.get("signal", {}).get("signal_id")
    print(f"Signal ID: {signal_id}")
    
    # Agent 2 fades the signal
    print("\nAgent2 fades the signal (bets against)...")
    bet = agent2.fade_signal(signal_id, stake=25)
    bet_id = bet.get("bet", {}).get("bet_id")
    print(f"Bet ID: {bet_id}")
    print(f"Total pot: ${bet.get('bet', {}).get('total_pot', 0)}")
    
    # Check signals
    signals = agent1.get_signals()
    print(f"\nTotal signals: {len(signals)}")


def example_agent_as_class():
    """Advanced: Build your own trading agent"""
    print("\n" + "=" * 50)
    print("Example 4: Custom Trading Agent")
    print("=" * 50)
    
    class SimpleTradingAgent:
        """A simple momentum-based trading agent"""
        
        def __init__(self, name: str, wallet: str):
            self.dex = quick_start(name, wallet, 1000)
            self.positions = []
        
        def analyze_market(self) -> dict:
            """Analyze market conditions"""
            prices = self.dex.get_prices()
            # Simple analysis: compare to reference
            return {
                "btc_price": prices.get("BTC", {}).get("price", 0),
                "sentiment": "bullish" if prices.get("BTC", {}).get("change_24h", 0) > 0 else "bearish"
            }
        
        def execute_strategy(self):
            """Execute trading strategy"""
            analysis = self.analyze_market()
            print(f"\nMarket Analysis:")
            print(f"  BTC: ${analysis['btc_price']:,.0f}")
            print(f"  Sentiment: {analysis['sentiment']}")
            
            if analysis["sentiment"] == "bullish":
                print("\n  → Opening long position...")
                result = self.dex.open_long("BTC-PERP", 100, leverage=2)
                if result.get("success"):
                    self.positions.append(result["position"])
            else:
                print("\n  → Opening short position...")
                result = self.dex.open_short("BTC-PERP", 100, leverage=2)
                if result.get("success"):
                    self.positions.append(result["position"])
            
            return result
    
    # Run the agent
    agent = SimpleTradingAgent("MomentumBot", f"0xMom{int(time.time())}")
    result = agent.execute_strategy()
    print(f"\nTrade result: {result.get('success', False)}")


if __name__ == "__main__":
    print("🦞 AI Perp DEX - Python SDK Examples\n")
    
    try:
        example_basic()
        example_register_and_trade()
        example_signal_betting()
        example_agent_as_class()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the backend is running: http://localhost:8082")
