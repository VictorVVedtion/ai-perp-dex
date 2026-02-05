"""
Autonomous Trading Agent
一个会自己思考的交易 Agent

它会：
1. 监控市场情绪
2. 分析其他 Agent 的行为
3. 自己做决策
4. 管理风险
"""

import asyncio
import aiohttp
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from sdk.tradinghub import TradingHub, Match

@dataclass
class Position:
    """持仓"""
    asset: str
    direction: str  # long/short
    size: float
    entry_price: float
    entry_time: datetime
    match_id: str

@dataclass
class AgentState:
    """Agent 状态"""
    balance: float = 1000.0  # 初始资金
    max_position_pct: float = 0.2  # 单笔最大仓位比例
    max_total_exposure: float = 0.5  # 最大总敞口
    stop_loss_pct: float = 0.05  # 止损比例
    take_profit_pct: float = 0.1  # 止盈比例
    
    positions: Dict[str, Position] = field(default_factory=dict)
    total_pnl: float = 0.0
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    
    @property
    def win_rate(self) -> float:
        if self.trades_count == 0:
            return 0.5
        return self.wins / self.trades_count
    
    @property
    def current_exposure(self) -> float:
        return sum(p.size for p in self.positions.values())
    
    @property
    def available_balance(self) -> float:
        return self.balance - self.current_exposure

class AutonomousTrader:
    """
    自主交易 Agent
    
    思考过程：
    1. 观察：收集市场数据、其他 Agent 行为
    2. 分析：判断市场情绪、寻找机会
    3. 决策：根据策略和风险管理做决定
    4. 执行：下单或持有
    5. 反思：记录结果、调整策略
    """
    
    def __init__(
        self,
        name: str = "AutonomousTrader",
        wallet: str = None,
        personality: str = "balanced",  # aggressive/balanced/conservative
    ):
        self.name = name
        self.wallet = wallet or f"0x{name}_{random.randint(1000,9999)}"
        self.personality = personality
        
        self.hub: Optional[TradingHub] = None
        self.state = AgentState()
        
        # 根据性格调整参数
        if personality == "aggressive":
            self.state.max_position_pct = 0.3
            self.state.max_total_exposure = 0.7
            self.state.stop_loss_pct = 0.08
        elif personality == "conservative":
            self.state.max_position_pct = 0.1
            self.state.max_total_exposure = 0.3
            self.state.stop_loss_pct = 0.03
        
        # 内部状态
        self._running = False
        self._last_trade_time: Optional[datetime] = None
        self._cooldown = timedelta(seconds=10)  # 交易冷却
        
        # 记忆
        self.observations: List[dict] = []
        self.decisions: List[dict] = []
    
    async def start(self):
        """启动 Agent"""
        print(f"🤖 [{self.name}] Starting... (personality: {self.personality})")
        
        self.hub = TradingHub(self.wallet)
        await self.hub.connect()
        
        # 注册回调
        @self.hub.on_match
        async def on_match(match: Match):
            await self._handle_match(match)
        
        self._running = True
        print(f"🤖 [{self.name}] Agent ID: {self.hub.agent_id}")
        print(f"🤖 [{self.name}] Balance: ${self.state.balance}")
        
        # 启动主循环
        await self._main_loop()
    
    async def stop(self):
        """停止 Agent"""
        self._running = False
        if self.hub:
            await self.hub.disconnect()
        print(f"🤖 [{self.name}] Stopped. Total PnL: ${self.state.total_pnl:.2f}")
    
    async def _main_loop(self):
        """主循环：观察 → 分析 → 决策 → 执行"""
        while self._running:
            try:
                # 1. 观察
                observation = await self._observe()
                self.observations.append(observation)
                
                # 2. 分析
                analysis = await self._analyze(observation)
                
                # 3. 决策
                decision = await self._decide(analysis)
                self.decisions.append(decision)
                
                # 4. 执行
                if decision["action"] != "hold":
                    await self._execute(decision)
                
                # 5. 风险检查
                await self._check_risk()
                
                # 等待下一轮
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"🤖 [{self.name}] Error: {e}")
                await asyncio.sleep(5)
    
    async def _observe(self) -> dict:
        """观察市场"""
        # 获取各资产的订单簿
        assets = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
        orderbooks = {}
        
        for asset in assets:
            try:
                ob = await self.hub.get_orderbook(asset)
                orderbooks[asset] = ob
            except Exception as e:
                logger.warning(f"Failed to get orderbook for {asset}: {e}")
        
        # 获取排行榜
        try:
            leaderboard = await self.hub.get_leaderboard()
        except Exception as e:
            logger.warning(f"Failed to get leaderboard: {e}")
            leaderboard = []
        
        return {
            "timestamp": datetime.now(),
            "orderbooks": orderbooks,
            "leaderboard": leaderboard[:5],
            "my_positions": list(self.state.positions.keys()),
            "my_exposure": self.state.current_exposure,
        }
    
    async def _analyze(self, observation: dict) -> dict:
        """分析市场"""
        analysis = {
            "timestamp": datetime.now(),
            "opportunities": [],
            "risks": [],
        }
        
        for asset, ob in observation["orderbooks"].items():
            long_size = ob.get("total_long_size", 0)
            short_size = ob.get("total_short_size", 0)
            total = long_size + short_size
            
            if total == 0:
                continue
            
            long_ratio = long_size / total
            
            # 寻找极端情绪
            if long_ratio > 0.7:
                analysis["opportunities"].append({
                    "asset": asset,
                    "signal": "contrarian_short",
                    "strength": long_ratio,
                    "reason": f"Too many longs ({long_ratio:.0%}), consider short",
                })
            elif long_ratio < 0.3:
                analysis["opportunities"].append({
                    "asset": asset,
                    "signal": "contrarian_long",
                    "strength": 1 - long_ratio,
                    "reason": f"Too many shorts ({1-long_ratio:.0%}), consider long",
                })
            
            # 检查是否已有仓位
            if asset in self.state.positions:
                pos = self.state.positions[asset]
                if pos.direction == "long" and long_ratio > 0.8:
                    analysis["risks"].append({
                        "asset": asset,
                        "type": "crowded_trade",
                        "reason": "Your long is now crowded",
                    })
        
        return analysis
    
    async def _decide(self, analysis: dict) -> dict:
        """做出决策"""
        decision = {
            "timestamp": datetime.now(),
            "action": "hold",
            "asset": None,
            "direction": None,
            "size": 0,
            "reason": "No clear opportunity",
        }
        
        # 检查冷却
        if self._last_trade_time:
            if datetime.now() - self._last_trade_time < self._cooldown:
                decision["reason"] = "In cooldown period"
                return decision
        
        # 检查敞口
        if self.state.current_exposure >= self.state.balance * self.state.max_total_exposure:
            decision["reason"] = "Max exposure reached"
            return decision
        
        # 找最好的机会
        best_opportunity = None
        best_strength = 0.6  # 最低门槛
        
        for opp in analysis["opportunities"]:
            # 跳过已有仓位的资产
            if opp["asset"] in self.state.positions:
                continue
            
            if opp["strength"] > best_strength:
                best_strength = opp["strength"]
                best_opportunity = opp
        
        if best_opportunity:
            # 计算仓位大小
            max_size = self.state.balance * self.state.max_position_pct
            
            # 根据信号强度调整
            size = max_size * best_opportunity["strength"]
            
            # 根据性格调整
            if self.personality == "conservative":
                size *= 0.5
            elif self.personality == "aggressive":
                size *= 1.5
            
            # 确保不超过可用余额
            size = min(size, self.state.available_balance * 0.9)
            
            if size < 10:  # 最小交易额
                decision["reason"] = "Size too small"
                return decision
            
            direction = "short" if "short" in best_opportunity["signal"] else "long"
            
            decision.update({
                "action": "open",
                "asset": best_opportunity["asset"],
                "direction": direction,
                "size": round(size, 2),
                "reason": best_opportunity["reason"],
                "confidence": best_opportunity["strength"],
            })
        
        return decision
    
    async def _execute(self, decision: dict):
        """执行决策"""
        print(f"\n🤖 [{self.name}] EXECUTING:")
        print(f"   Action: {decision['action']}")
        print(f"   Asset: {decision['asset']}")
        print(f"   Direction: {decision['direction']}")
        print(f"   Size: ${decision['size']}")
        print(f"   Reason: {decision['reason']}")
        
        if decision["action"] == "open":
            if decision["direction"] == "long":
                match = await self.hub.long(
                    decision["asset"].replace("-PERP", ""),
                    decision["size"],
                )
            else:
                match = await self.hub.short(
                    decision["asset"].replace("-PERP", ""),
                    decision["size"],
                )
            
            if match:
                # 记录持仓
                self.state.positions[decision["asset"]] = Position(
                    asset=decision["asset"],
                    direction=decision["direction"],
                    size=decision["size"],
                    entry_price=match.price,
                    entry_time=datetime.now(),
                    match_id=match.match_id,
                )
                print(f"   ✅ Matched! Price: ${match.price:,}")
            else:
                print(f"   ⏳ Intent created, waiting for match...")
            
            self._last_trade_time = datetime.now()
    
    async def _handle_match(self, match: Match):
        """处理匹配回调"""
        print(f"\n🤖 [{self.name}] MATCH RECEIVED:")
        print(f"   Match ID: {match.match_id}")
        print(f"   Asset: {match.asset}")
        print(f"   Size: ${match.size}")
        print(f"   Counterparty: {match.counterparty}")
    
    async def _check_risk(self):
        """风险检查 (简化版)"""
        # 在真实环境中，这里会检查价格变动并执行止损/止盈
        pass
    
    def get_status(self) -> dict:
        """获取 Agent 状态"""
        return {
            "name": self.name,
            "personality": self.personality,
            "agent_id": self.hub.agent_id if self.hub else None,
            "balance": self.state.balance,
            "exposure": self.state.current_exposure,
            "positions": len(self.state.positions),
            "total_pnl": self.state.total_pnl,
            "trades": self.state.trades_count,
            "win_rate": f"{self.state.win_rate:.0%}",
        }


async def demo():
    """运行多个性格不同的 Agent"""
    print("=" * 60)
    print("🤖 AUTONOMOUS TRADING AGENTS DEMO")
    print("=" * 60)
    
    # 创建不同性格的 Agent
    agents = [
        AutonomousTrader("AggressiveBot", personality="aggressive"),
        AutonomousTrader("BalancedBot", personality="balanced"),
        AutonomousTrader("ConservativeBot", personality="conservative"),
    ]
    
    # 启动所有 Agent
    tasks = []
    for agent in agents:
        task = asyncio.create_task(agent.start())
        tasks.append(task)
    
    # 运行一段时间
    try:
        await asyncio.sleep(30)  # 运行 30 秒
    except KeyboardInterrupt:
        pass
    
    # 停止所有 Agent
    for agent in agents:
        await agent.stop()
        print(f"\n{agent.name} Status:")
        for k, v in agent.get_status().items():
            print(f"  {k}: {v}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(demo())
