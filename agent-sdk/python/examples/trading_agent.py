#!/usr/bin/env python3
"""
AI Trading Agent 示例

展示如何让 AI Agent 自主交易永续合约。
"""

import asyncio
from ai_perp_dex import TradingAgent


async def main():
    # 初始化 Agent (使用 Solana keypair)
    agent = TradingAgent(
        keypair_path="~/.config/solana/agent.json",
        api_url="http://localhost:8080",  # Matching Engine API
        rpc_url="https://api.devnet.solana.com",
    )
    
    # 注册为交易 Agent
    await agent.register("MyTradingBot")
    
    print("=== AI Trading Agent 启动 ===\n")
    
    # 方式 1: 自然语言交易
    print("📝 自然语言命令:")
    
    result = agent.execute("开 BTC 多单 $100, 10倍杠杆")
    print(f"  {result.message}")
    
    result = agent.execute("开 ETH 空单 $50, 5x")
    print(f"  {result.message}")
    
    result = agent.execute("查看持仓")
    print(f"  {result.message}")
    
    # 方式 2: 结构化 API
    print("\n📊 结构化 API:")
    
    result = agent.open_position(
        market="SOL-PERP",
        side="long",
        size_usd=200,
        leverage=20,
    )
    print(f"  {result.message}")
    
    # 查询账户状态
    print("\n💰 账户信息:")
    account = agent.get_account()
    print(f"  抵押品: ${account.collateral:.2f}")
    print(f"  可用保证金: ${account.available_margin:.2f}")
    print(f"  未实现盈亏: ${account.total_unrealized_pnl:.2f}")
    
    # 查看持仓
    print("\n📈 当前持仓:")
    positions = agent.get_positions()
    for pos in positions:
        pnl_emoji = "🟢" if pos.unrealized_pnl >= 0 else "🔴"
        print(f"  {pos.market}: {pos.side.value} ${pos.size_usd:.2f} @ {pos.leverage}x")
        print(f"    入场: ${pos.entry_price:.2f} | 现价: ${pos.mark_price:.2f}")
        print(f"    {pnl_emoji} PnL: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_percent:.1f}%)")
    
    # 获取市场价格
    print("\n📉 市场价格:")
    for market in ["BTC-PERP", "ETH-PERP", "SOL-PERP"]:
        price = agent.get_price(market)
        print(f"  {market}: ${price:,.2f}")


if __name__ == "__main__":
    asyncio.run(main())
