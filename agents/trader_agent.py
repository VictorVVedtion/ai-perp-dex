#!/usr/bin/env python3
"""
AI Trader Agent
真正的 AI Agent，自动交易
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Optional
import random

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from ai_perp_dex import TradingAgent
from ai_perp_dex.types import Market, Side
from ai_perp_dex.prices import fetch_live_prices


class AITrader:
    """
    AI 驱动的交易者
    
    策略:
    - 获取实时价格
    - 简单动量策略
    - 风险管理
    """
    
    def __init__(
        self,
        agent_id: str = "ai_trader_bot",
        max_position_size: float = 1000,
        max_leverage: int = 5,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.10,
    ):
        self.agent_id = agent_id
        self.max_position_size = max_position_size
        self.max_leverage = max_leverage
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.trader = TradingAgent(agent_id)
        self.positions = []
        self.total_pnl = 0.0
        self.trades_count = 0
    
    async def analyze_market(self, market: str) -> Optional[dict]:
        """
        分析市场，返回交易信号
        
        简单策略: 随机方向 (实际应该用技术指标)
        """
        prices = await fetch_live_prices()
        price = prices.get(market, 0)
        
        if price == 0:
            return None
        
        # 模拟分析 (实际应该更复杂)
        signal = random.choice(["long", "short", None])
        
        if signal is None:
            return None
        
        # 计算仓位大小
        size = min(self.max_position_size, 500)  # 简单固定
        leverage = min(self.max_leverage, 3)
        
        return {
            "market": market,
            "side": signal,
            "size": size,
            "leverage": leverage,
            "price": price,
            "confidence": random.uniform(0.6, 0.9),
        }
    
    async def execute_trade(self, signal: dict):
        """执行交易"""
        print(f"\n📊 交易信号:")
        print(f"   {signal['market']} {signal['side'].upper()}")
        print(f"   价格: ${signal['price']:,.2f}")
        print(f"   大小: ${signal['size']} | 杠杆: {signal['leverage']}x")
        print(f"   置信度: {signal['confidence']*100:.0f}%")
        
        try:
            if signal['side'] == 'long':
                pos = await self.trader.long(
                    signal['market'],
                    signal['size'],
                    leverage=signal['leverage'],
                    max_wait_secs=10,
                )
            else:
                pos = await self.trader.short(
                    signal['market'],
                    signal['size'],
                    leverage=signal['leverage'],
                    max_wait_secs=10,
                )
            
            print(f"\n✅ 成交!")
            print(f"   Position ID: {pos.id[:8]}...")
            print(f"   入场价: ${pos.entry_price:,.2f}")
            
            self.positions.append(pos)
            self.trades_count += 1
            
            return pos
            
        except TimeoutError:
            print(f"\n❌ 超时: 没有 MM 报价")
            return None
        except Exception as e:
            print(f"\n❌ 交易失败: {e}")
            return None
    
    async def check_positions(self):
        """检查持仓，执行止盈止损"""
        positions = await self.trader.get_positions()
        
        for pos in positions:
            if pos.status != "active":
                continue
            
            # 获取当前价格
            prices = await fetch_live_prices()
            current_price = prices.get(pos.market.value, pos.entry_price)
            
            # 计算 PnL
            if pos.side == Side.Long:
                pnl_pct = (current_price - pos.entry_price) / pos.entry_price
            else:
                pnl_pct = (pos.entry_price - current_price) / pos.entry_price
            
            pnl_pct *= pos.leverage
            
            # 检查止盈止损
            if pnl_pct >= self.take_profit_pct:
                print(f"\n🎯 止盈! {pos.market.value} PnL: {pnl_pct*100:.1f}%")
                await self.trader.close(pos.id)
                self.total_pnl += pnl_pct * pos.size_usdc
                
            elif pnl_pct <= -self.stop_loss_pct:
                print(f"\n🛑 止损! {pos.market.value} PnL: {pnl_pct*100:.1f}%")
                await self.trader.close(pos.id)
                self.total_pnl += pnl_pct * pos.size_usdc
    
    def status(self):
        """打印状态"""
        print(f"\n{'='*50}")
        print(f"🤖 AI Trader Status")
        print(f"{'='*50}")
        print(f"Agent ID: {self.agent_id}")
        print(f"交易次数: {self.trades_count}")
        print(f"活跃仓位: {len(self.positions)}")
        print(f"总 PnL: ${self.total_pnl:,.2f}")
        print(f"{'='*50}\n")
    
    async def run_once(self, market: str = "BTC-PERP"):
        """执行一次交易"""
        print(f"🔍 分析 {market}...")
        
        signal = await self.analyze_market(market)
        
        if signal:
            await self.execute_trade(signal)
        else:
            print("  没有交易信号")
        
        self.status()
    
    async def run_loop(self, interval: int = 60):
        """循环运行"""
        print("🚀 AI Trader 启动...")
        self.status()
        
        markets = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
        
        while True:
            try:
                # 随机选择市场
                market = random.choice(markets)
                
                # 分析并可能交易
                signal = await self.analyze_market(market)
                if signal and signal['confidence'] > 0.7:
                    await self.execute_trade(signal)
                
                # 检查现有仓位
                await self.check_positions()
                
                # 等待
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Trader 停止")
                self.status()
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
                await asyncio.sleep(10)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Trader Agent")
    parser.add_argument("--id", default="ai_trader_bot", help="Agent ID")
    parser.add_argument("--once", action="store_true", help="只执行一次")
    parser.add_argument("--market", default="BTC-PERP", help="交易市场")
    
    args = parser.parse_args()
    
    trader = AITrader(agent_id=args.id)
    
    if args.once:
        await trader.run_once(args.market)
    else:
        await trader.run_loop()


if __name__ == "__main__":
    asyncio.run(main())
