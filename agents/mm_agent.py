#!/usr/bin/env python3
"""
AI Market Maker Agent
真正的 AI Agent，自动做市赚取 funding 费用
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Optional

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from ai_perp_dex import MarketMaker
from ai_perp_dex.types import TradeRequest, Side


class AIMarketMaker:
    """
    AI 驱动的做市商
    
    策略:
    - 评估每个请求的风险
    - 根据市场波动性调整 funding rate
    - 控制总敞口
    - 对冲大单
    """
    
    def __init__(
        self,
        agent_id: str = "ai_mm_bot",
        max_exposure: float = 50000,  # 最大总敞口 $50k
        base_funding_rate: float = 0.01,  # 基础 funding 1%
        max_single_position: float = 5000,  # 单笔最大 $5k
        collateral_ratio: float = 0.2,  # 抵押比例 20%
    ):
        self.agent_id = agent_id
        self.max_exposure = max_exposure
        self.base_funding_rate = base_funding_rate
        self.max_single_position = max_single_position
        self.collateral_ratio = collateral_ratio
        
        self.mm = MarketMaker(agent_id)
        self.current_exposure = 0.0
        self.positions_count = 0
        self.total_earned = 0.0
        
        # 市场偏好 (可以学习调整)
        self.market_preferences = {
            "BTC-PERP": 1.0,   # 正常
            "ETH-PERP": 1.0,
            "SOL-PERP": 1.2,   # 稍高风险
            "DOGE-PERP": 1.5,  # 高波动
            "AVAX-PERP": 1.3,
            "LINK-PERP": 1.2,
        }
    
    def evaluate_request(self, request: TradeRequest) -> Optional[dict]:
        """
        评估交易请求，决定是否报价
        
        Returns:
            报价参数 dict 或 None (拒绝)
        """
        # 1. 检查单笔大小
        if request.size_usdc > self.max_single_position:
            print(f"  ❌ 拒绝: 单笔过大 ${request.size_usdc} > ${self.max_single_position}")
            return None
        
        # 2. 检查总敞口
        new_exposure = self.current_exposure + request.size_usdc
        if new_exposure > self.max_exposure:
            print(f"  ❌ 拒绝: 敞口超限 ${new_exposure} > ${self.max_exposure}")
            return None
        
        # 3. 检查杠杆
        if request.leverage > 10:
            print(f"  ❌ 拒绝: 杠杆过高 {request.leverage}x > 10x")
            return None
        
        # 4. 计算 funding rate
        market_name = request.market if isinstance(request.market, str) else request.market.value
        market_mult = self.market_preferences.get(market_name, 1.0)
        leverage_mult = 1 + (request.leverage - 1) * 0.1  # 杠杆越高，费率越高
        size_mult = 1 + (request.size_usdc / self.max_single_position) * 0.2
        
        funding_rate = self.base_funding_rate * market_mult * leverage_mult * size_mult
        funding_rate = min(funding_rate, request.max_funding_rate or 0.05)  # 不超过对方上限
        
        # 5. 计算抵押金
        collateral = request.size_usdc * self.collateral_ratio / request.leverage
        
        return {
            "funding_rate": round(funding_rate, 4),
            "collateral": round(collateral, 2),
        }
    
    async def on_request(self, request: TradeRequest):
        """处理新的交易请求"""
        print(f"\n📥 收到请求: {request.market.value} {request.side.value.upper()}")
        print(f"   大小: ${request.size_usdc} | 杠杆: {request.leverage}x")
        print(f"   请求方: {request.agent_id}")
        
        # 评估
        result = self.evaluate_request(request)
        
        if result is None:
            return
        
        # 报价
        print(f"  ✅ 报价: funding={result['funding_rate']*100:.2f}%, collateral=${result['collateral']}")
        
        try:
            quote = await self.mm.quote(
                request_id=request.id,
                funding_rate=result["funding_rate"],
                collateral_usdc=result["collateral"],
            )
            print(f"  📤 报价已发送: {quote.id[:8]}...")
            
            # 更新敞口 (报价阶段先预留)
            self.current_exposure += request.size_usdc
            
        except Exception as e:
            print(f"  ❌ 报价失败: {e}")
    
    async def on_position_opened(self, position):
        """仓位被接受时的回调"""
        print(f"\n✅ 仓位成交!")
        print(f"   {position.market.value} | 入场: ${position.entry_price:,.2f}")
        print(f"   Funding: {position.funding_rate*100:.2f}%")
        self.positions_count += 1
    
    async def on_position_closed(self, position, pnl: float):
        """仓位平仓时的回调"""
        print(f"\n📊 仓位平仓!")
        print(f"   PnL: ${pnl:,.2f}")
        self.total_earned += pnl
        self.current_exposure -= position.size_usdc
        print(f"   总收益: ${self.total_earned:,.2f}")
    
    def status(self):
        """打印状态"""
        print(f"\n{'='*50}")
        print(f"🤖 AI MM Bot Status")
        print(f"{'='*50}")
        print(f"Agent ID: {self.agent_id}")
        print(f"当前敞口: ${self.current_exposure:,.2f} / ${self.max_exposure:,.2f}")
        print(f"活跃仓位: {self.positions_count}")
        print(f"总收益: ${self.total_earned:,.2f}")
        print(f"{'='*50}\n")
    
    async def run(self):
        """启动 MM Agent"""
        print("🚀 AI Market Maker 启动中...")
        
        # 注册回调
        self.mm.on_request(self.on_request)
        
        # 显示状态
        self.status()
        
        print("👂 监听交易请求中...\n")
        print("按 Ctrl+C 停止\n")
        
        # 运行
        try:
            await self.mm.run()
        except KeyboardInterrupt:
            print("\n\n🛑 MM Agent 停止")
            self.status()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Market Maker Agent")
    parser.add_argument("--id", default="ai_mm_bot", help="Agent ID")
    parser.add_argument("--max-exposure", type=float, default=50000, help="最大敞口")
    parser.add_argument("--base-rate", type=float, default=0.01, help="基础 funding rate")
    parser.add_argument("--max-single", type=float, default=5000, help="单笔最大")
    
    args = parser.parse_args()
    
    mm = AIMarketMaker(
        agent_id=args.id,
        max_exposure=args.max_exposure,
        base_funding_rate=args.base_rate,
        max_single_position=args.max_single,
    )
    
    await mm.run()


if __name__ == "__main__":
    asyncio.run(main())
