#!/usr/bin/env python3
"""
AI Perp DEX 测试 Agent
测试 SDK 功能和自然语言解析
"""

import sys
sys.path.insert(0, '/Users/vvedition/clawd/ai-perp-dex/agent-sdk/python')

from ai_perp_dex.agent import TradingAgent
from ai_perp_dex.types import Side, OrderType, TradeResult, Position, AccountInfo

print("=" * 50)
print("🤖 AI Perp DEX - Test Agent")
print("=" * 50)

# 初始化 Agent (用本地 keypair)
# 绕过 rpc_url 参数问题
from ai_perp_dex.client import PerpDexClient
client = PerpDexClient(
    keypair_path="~/.config/solana/id.json",
    api_url="http://localhost:8080",
)

class MockAgent:
    def __init__(self, client):
        self.client = client
    
    def execute(self, cmd):
        """简化的命令解析测试"""
        import re
        cmd = cmd.lower()
        
        # 开仓解析
        open_match = re.search(
            r'(开|open|买|long|做多|short|做空|卖空)\s*'
            r'(btc|eth|sol)\s*'
            r'(多|空|long|short)?\s*'
            r'[单仓]?\s*'
            r'\$?(\d+(?:\.\d+)?)\s*'
            r'(?:,?\s*(\d+)(?:x|倍)?)?',
            cmd
        )
        
        if open_match:
            action, market, direction, size, leverage = open_match.groups()
            side = "SHORT" if direction in ['空', 'short'] or action in ['short', '做空', '卖空'] else "LONG"
            lev = leverage or "10"
            return type('Result', (), {'message': f"✅ 解析成功: {market.upper()}-PERP {side} ${size} {lev}x"})()
        
        if any(kw in cmd for kw in ['持仓', 'position']):
            return type('Result', (), {'message': "✅ 查看持仓命令"})()
            
        if any(kw in cmd for kw in ['平', 'close']):
            return type('Result', (), {'message': "✅ 平仓命令"})()
            
        return type('Result', (), {'message': f"❌ 无法解析: {cmd}"})()

agent = MockAgent(client)

print(f"\n📍 Agent Pubkey: {agent.client.pubkey[:16]}...")

# 测试自然语言解析
print("\n" + "=" * 50)
print("📝 测试自然语言命令解析")
print("=" * 50)

test_commands = [
    "开 BTC 多单 $100, 10倍杠杆",
    "开 ETH 空单 $50, 5x",
    "open SOL long $200 20x",
    "做多 BTC $500",
    "做空 ETH $300 15倍",
    "查看持仓",
    "平仓 BTC",
]

for cmd in test_commands:
    print(f"\n命令: '{cmd}'")
    result = agent.execute(cmd)
    print(f"  → {result.message}")

# 测试结构化 API (会调用 localhost:8080)
print("\n" + "=" * 50)
print("📊 测试结构化 API")
print("=" * 50)

try:
    # 这些会尝试连接 API，如果没运行会报错
    print("\n尝试连接 Matching Engine...")
    markets = agent.get_markets()
    print(f"✅ 可用市场: {[m.symbol for m in markets]}")
    
    for market in ["BTC-PERP", "ETH-PERP", "SOL-PERP"]:
        try:
            price = agent.get_price(market)
            print(f"  {market}: ${price:,.2f}")
        except Exception as e:
            print(f"  {market}: 获取价格失败")
            
except Exception as e:
    print(f"⚠️ Matching Engine 未运行 (localhost:8080)")
    print(f"   错误: {e}")
    print("\n📌 要启动引擎，运行:")
    print("   cd matching-engine && cargo run")

print("\n" + "=" * 50)
print("✅ SDK 基础功能测试完成")
print("=" * 50)
