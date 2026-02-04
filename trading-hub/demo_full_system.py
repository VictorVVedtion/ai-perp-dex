#!/usr/bin/env python3
"""
Trading Hub - Full System Demo
展示完整的 AI Agent 交易闭环
"""

import asyncio
import sys
sys.path.insert(0, '.')

from sdk.tradinghub import TradingHub
from agents.autonomous_trader import AutonomousTrader
from agents.intent_aggregator import IntentAggregator

async def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🔄 TRADING HUB - AI Agent Intent Exchange                   ║
║                                                               ║
║   The future of trading is not orderbooks.                    ║
║   It's AI agents expressing intents and finding each other.   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # === Part 1: SDK Demo ===
    print("\n" + "=" * 60)
    print("📦 PART 1: SDK - One-liner Trading")
    print("=" * 60)
    
    async with TradingHub("0xSDK_Demo") as hub:
        print(f"\nAgent ID: {hub.agent_id}")
        
        # 一行做多
        print("\n>>> await hub.long('BTC', 100, leverage=10)")
        await hub.long("BTC", 100, leverage=10)
        print("    ✅ Intent created")
        
        # 自然语言下注
        print("\n>>> await hub.bet('ETH will pump', 50)")
        await hub.bet("ETH will pump", 50)
        print("    ✅ Intent created")
        
        # 决策辅助
        print("\n>>> await hub.should_trade('BTC')")
        advice = await hub.should_trade("BTC-PERP")
        print(f"    Recommendation: {advice['recommendation']}")
        print(f"    Confidence: {advice['confidence']:.0%}")
        print(f"    Reason: {advice['reason']}")
    
    # === Part 2: Autonomous Agent ===
    print("\n\n" + "=" * 60)
    print("🤖 PART 2: Autonomous Trader")
    print("=" * 60)
    
    agent = AutonomousTrader("DemoBot", personality="balanced")
    
    # 手动初始化
    agent.hub = TradingHub(agent.wallet)
    await agent.hub.connect()
    agent._running = True
    
    print(f"\nAgent: {agent.name}")
    print(f"Personality: {agent.personality}")
    print(f"Agent ID: {agent.hub.agent_id}")
    
    # 运行一轮思考
    print("\n--- Agent Thinking ---")
    
    obs = await agent._observe()
    print(f"📊 Observed {len(obs['orderbooks'])} markets")
    
    analysis = await agent._analyze(obs)
    print(f"🔍 Found {len(analysis['opportunities'])} opportunities")
    
    for opp in analysis['opportunities'][:2]:
        print(f"   • {opp['asset']}: {opp['signal']} ({opp['strength']:.0%})")
    
    decision = await agent._decide(analysis)
    print(f"🎯 Decision: {decision['action']}")
    
    if decision['action'] != 'hold':
        print(f"   {decision['direction']} {decision['asset']} ${decision['size']}")
        await agent._execute(decision)
    
    await agent.hub.disconnect()
    
    # === Part 3: Intent Aggregator ===
    print("\n\n" + "=" * 60)
    print("🔍 PART 3: Intent Aggregator")
    print("=" * 60)
    
    aggregator = IntentAggregator()
    await aggregator.start()
    
    # 模拟外部帖子
    test_posts = [
        {"id": "1", "content": "Going long BTC 10x, feeling bullish!", "author": "@CryptoWhale"},
        {"id": "2", "content": "Shorting ETH here, chart looks weak", "author": "@BearTrader"},
        {"id": "3", "content": "SOL will pump to 200, mark my words", "author": "@AltCoinKing"},
    ]
    
    print("\n📝 Parsing external posts:")
    for post in test_posts:
        intent = aggregator._parse_intent(post["content"], "moltbook", post)
        if intent:
            print(f"\n   From: {intent.author}")
            print(f"   Intent: {intent.intent_type} {intent.asset}")
            print(f"   → Ready to forward to Trading Hub")
    
    await aggregator.stop()
    
    # === Summary ===
    print("\n\n" + "=" * 60)
    print("📊 SYSTEM ARCHITECTURE")
    print("=" * 60)
    
    print("""
    ┌─────────────────────────────────────────────────────────┐
    │                    External Platforms                    │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
    │  │Moltbook │  │ MoltX   │  │ Twitter │  ...            │
    │  └────┬────┘  └────┬────┘  └────┬────┘                 │
    │       │            │            │                       │
    │       └────────────┴─────┬──────┘                       │
    │                          │                              │
    │              ┌───────────▼───────────┐                  │
    │              │  Intent Aggregator    │                  │
    │              │  (Parse & Forward)    │                  │
    │              └───────────┬───────────┘                  │
    │                          │                              │
    │              ┌───────────▼───────────┐                  │
    │              │     Trading Hub       │                  │
    │              │  ┌─────────────────┐  │                  │
    │              │  │ Intent Matching │  │                  │
    │              │  │   Long ↔ Short  │  │                  │
    │              │  └─────────────────┘  │                  │
    │              └───────────┬───────────┘                  │
    │                          │                              │
    │    ┌─────────────────────┼─────────────────────┐       │
    │    │                     │                     │       │
    │    ▼                     ▼                     ▼       │
    │ ┌──────┐           ┌──────────┐         ┌──────────┐  │
    │ │ SDK  │           │Autonomous│         │ Dashboard│  │
    │ │      │           │  Agents  │         │  (Web)   │  │
    │ └──────┘           └──────────┘         └──────────┘  │
    │                                                        │
    │              ┌───────────────────────┐                 │
    │              │   Settlement Layer    │                 │
    │              │   (Solana / Base)     │                 │
    │              └───────────────────────┘                 │
    └─────────────────────────────────────────────────────────┘
    """)
    
    print("\n✅ All components working!")
    print("\n📚 Quick Start:")
    print("   1. Start API:  cd trading-hub && ./run.sh")
    print("   2. Open Dashboard: web/index.html")
    print("   3. Use SDK:")
    print("      async with TradingHub(wallet) as hub:")
    print("          await hub.long('BTC', 100)")
    print("")

if __name__ == "__main__":
    asyncio.run(main())
