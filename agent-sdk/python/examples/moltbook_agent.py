#!/usr/bin/env python3
"""
Moltbook AI Agent 集成示例

展示 Moltbook 上的 AI Agent 如何接入 AI Perp DEX 交易。
"""

import asyncio
from ai_perp_dex import TradingAgent


class MoltbookTradingAgent:
    """
    一个在 Moltbook 社交网络上活跃的 AI Agent，
    同时具备交易永续合约的能力。
    """
    
    def __init__(self, name: str, keypair_path: str):
        self.name = name
        self.trader = TradingAgent(
            keypair_path=keypair_path,
            api_url="http://localhost:8080",
        )
        
    async def setup(self):
        """初始化 Agent"""
        await self.trader.register(self.name)
        print(f"🦞 {self.name} 已连接到 AI Perp DEX")
        
    def process_message(self, message: str) -> str:
        """
        处理来自 Moltbook 的消息
        
        其他 Agent 或人类可以向这个 Agent 发送交易请求。
        """
        message = message.lower()
        
        # 识别交易意图
        if any(word in message for word in ["trade", "交易", "开仓", "做多", "做空"]):
            result = self.trader.execute(message)
            return f"✅ {result.message}"
            
        if any(word in message for word in ["持仓", "position", "仓位"]):
            positions = self.trader.get_positions()
            if not positions:
                return "📭 当前没有持仓"
            
            lines = ["📊 当前持仓:"]
            for pos in positions:
                emoji = "🟢" if pos.unrealized_pnl >= 0 else "🔴"
                lines.append(
                    f"  • {pos.market} {pos.side.value} "
                    f"${pos.size_usd:.0f} @ {pos.leverage}x "
                    f"{emoji} {pos.unrealized_pnl_percent:+.1f}%"
                )
            return "\n".join(lines)
            
        if any(word in message for word in ["价格", "price", "行情"]):
            lines = ["📈 市场行情:"]
            for market in ["BTC-PERP", "ETH-PERP", "SOL-PERP"]:
                price = self.trader.get_price(market)
                lines.append(f"  • {market}: ${price:,.2f}")
            return "\n".join(lines)
            
        return "🤖 我是交易 Agent，你可以让我：\n" \
               "  • 开 BTC 多单 $100\n" \
               "  • 查看持仓\n" \
               "  • 查看价格"


async def simulate_moltbook_interaction():
    """模拟 Moltbook 上的 Agent 交互"""
    
    # 创建一个交易 Agent
    agent = MoltbookTradingAgent(
        name="TradingMaster",
        keypair_path="~/.config/solana/agent.json"
    )
    await agent.setup()
    
    print("\n" + "="*50)
    print("🦞 模拟 Moltbook Agent 交互")
    print("="*50 + "\n")
    
    # 模拟收到的消息
    messages = [
        "hey, what can you do?",
        "开 BTC 多单 $500, 10倍杠杆",
        "做空 ETH $200, 5x",
        "查看持仓",
        "查看价格",
        "平掉所有仓位",
    ]
    
    for msg in messages:
        print(f"📨 收到消息: \"{msg}\"")
        response = agent.process_message(msg)
        print(f"💬 回复:\n{response}\n")
        print("-" * 40 + "\n")
        await asyncio.sleep(0.5)  # 模拟延迟


async def main():
    """
    这个示例展示了 AI Perp DEX 的 AI-native 设计：
    
    1. Agent 通过 SDK 直接交易，不需要人工点击按钮
    2. Agent 可以集成到社交网络 (Moltbook) 
    3. Agent 可以接收自然语言指令
    4. Agent 可以自主执行交易策略
    """
    await simulate_moltbook_interaction()


if __name__ == "__main__":
    asyncio.run(main())
