"""
PnL Tracker Service
实时追踪 Agent 的盈亏

功能:
- 根据实时价格计算未实现盈亏
- 追踪已实现盈亏
- 风险指标 (敞口, 杠杆)
"""

from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field

from services.price_feed import price_feed, Price
from db.store import store
from api.models import Match

@dataclass
class PositionPnL:
    """单个持仓的盈亏"""
    match_id: str
    agent_id: str
    asset: str
    direction: str  # long/short
    size_usdc: float
    entry_price: float
    current_price: float
    leverage: int = 1
    
    @property
    def notional_value(self) -> float:
        """名义价值"""
        return self.size_usdc * self.leverage
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        price_change_pct = (self.current_price - self.entry_price) / self.entry_price
        
        if self.direction == "short":
            price_change_pct = -price_change_pct
        
        return self.notional_value * price_change_pct
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏百分比 (相对于保证金)"""
        if self.size_usdc == 0:
            return 0
        return (self.unrealized_pnl / self.size_usdc) * 100
    
    @property
    def liquidation_price(self) -> float:
        """预估强平价格 (简化计算)"""
        # 假设 80% 损失触发强平
        max_loss_pct = 0.8 / self.leverage
        
        if self.direction == "long":
            return self.entry_price * (1 - max_loss_pct)
        else:
            return self.entry_price * (1 + max_loss_pct)
    
    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "agent_id": self.agent_id,
            "asset": self.asset,
            "direction": self.direction,
            "size_usdc": self.size_usdc,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "leverage": self.leverage,
            "notional_value": self.notional_value,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2),
            "liquidation_price": round(self.liquidation_price, 2),
        }

@dataclass
class AgentPnL:
    """Agent 的总体盈亏"""
    agent_id: str
    positions: List[PositionPnL] = field(default_factory=list)
    realized_pnl: float = 0.0
    
    @property
    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions)
    
    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.total_unrealized_pnl
    
    @property
    def total_exposure(self) -> float:
        return sum(p.notional_value for p in self.positions)
    
    @property
    def total_margin(self) -> float:
        return sum(p.size_usdc for p in self.positions)
    
    @property
    def average_leverage(self) -> float:
        if self.total_margin == 0:
            return 0
        return self.total_exposure / self.total_margin
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "positions": [p.to_dict() for p in self.positions],
            "realized_pnl": round(self.realized_pnl, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_exposure": round(self.total_exposure, 2),
            "total_margin": round(self.total_margin, 2),
            "average_leverage": round(self.average_leverage, 2),
            "position_count": len(self.positions),
        }

class PnLTracker:
    """PnL 追踪器"""
    
    def __init__(self):
        # 缓存: agent_id -> realized_pnl
        self.realized_pnl: Dict[str, float] = {}
    
    async def get_agent_pnl(self, agent_id: str) -> AgentPnL:
        """获取 Agent 的完整盈亏"""
        agent_pnl = AgentPnL(
            agent_id=agent_id,
            realized_pnl=self.realized_pnl.get(agent_id, 0.0),
        )
        
        # 获取所有匹配 (作为持仓)
        matches = store.list_recent_matches(limit=1000)
        
        for match in matches:
            # 检查是否涉及这个 Agent
            if match.agent_a_id != agent_id and match.agent_b_id != agent_id:
                continue
            
            # 确定方向
            # Agent A 创建的 Intent 和 Agent B 的是相反的
            # 需要从原始 Intent 获取方向
            intent_id = match.intent_a_id if match.agent_a_id == agent_id else match.intent_b_id
            intent = store.get_intent(intent_id)
            
            if not intent:
                continue
            
            direction = intent.intent_type.value
            
            # 获取当前价格
            current_price = price_feed.get_cached_price(match.asset)
            
            position = PositionPnL(
                match_id=match.match_id,
                agent_id=agent_id,
                asset=match.asset,
                direction=direction,
                size_usdc=match.size_usdc,
                entry_price=match.price,
                current_price=current_price,
                leverage=intent.leverage if intent else 1,
            )
            
            agent_pnl.positions.append(position)
        
        return agent_pnl
    
    def record_realized_pnl(self, agent_id: str, pnl: float):
        """记录已实现盈亏"""
        current = self.realized_pnl.get(agent_id, 0.0)
        self.realized_pnl[agent_id] = current + pnl
    
    async def get_leaderboard_with_pnl(self, limit: int = 20) -> List[dict]:
        """获取带 PnL 的排行榜"""
        agents = store.list_agents(limit=100)
        
        results = []
        for agent in agents:
            pnl = await self.get_agent_pnl(agent.agent_id)
            results.append({
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "total_pnl": pnl.total_pnl,
                "total_exposure": pnl.total_exposure,
                "position_count": len(pnl.positions),
                "reputation_score": agent.reputation_score,
            })
        
        # 按 PnL 排序
        results.sort(key=lambda x: x["total_pnl"], reverse=True)
        return results[:limit]


# 全局实例
pnl_tracker = PnLTracker()


async def demo():
    """演示 PnL 追踪"""
    print("=" * 50)
    print("💰 PNL TRACKER DEMO")
    print("=" * 50)
    
    # 初始化价格源
    await price_feed.start()
    
    # 模拟一些匹配数据
    print("\n📊 Creating test positions...")
    
    # 先 seed 数据
    import aiohttp
    async with aiohttp.ClientSession() as session:
        await session.post("http://localhost:8082/demo/seed")
        
        # 创建一些匹配
        await session.post(
            "http://localhost:8082/intents",
            json={"agent_id": "agent_0001", "intent_type": "short", "asset": "BTC-PERP", "size_usdc": 500, "leverage": 10}
        )
        await session.post(
            "http://localhost:8082/intents",
            json={"agent_id": "agent_0002", "intent_type": "long", "asset": "BTC-PERP", "size_usdc": 500, "leverage": 10}
        )
    
    # 获取 PnL
    print("\n💰 Agent PnL:")
    
    for agent_id in ["agent_0001", "agent_0002"]:
        pnl = await pnl_tracker.get_agent_pnl(agent_id)
        print(f"\n{agent_id}:")
        print(f"  Positions: {len(pnl.positions)}")
        print(f"  Total Exposure: ${pnl.total_exposure:,.2f}")
        print(f"  Unrealized PnL: ${pnl.total_unrealized_pnl:,.2f}")
        
        for pos in pnl.positions:
            print(f"    {pos.direction.upper()} {pos.asset}")
            print(f"      Entry: ${pos.entry_price:,.2f} → Current: ${pos.current_price:,.2f}")
            print(f"      PnL: ${pos.unrealized_pnl:,.2f} ({pos.unrealized_pnl_pct:+.2f}%)")
    
    await price_feed.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
