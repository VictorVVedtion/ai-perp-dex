"""
Agent Runtime System - 让 Agent 真正"活"起来

核心功能：
1. Agent 心跳循环 - 定期唤醒 agent 做决策
2. 自主决策引擎 - 基于市场状态做交易决策  
3. 思考广播 - 自动分享 agent 的思考过程
4. 生命周期管理 - 启动/暂停/停止 agent
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any, Awaitable
from enum import Enum
import random

from services.agent_comms import chat_db
from services.price_feed import price_feed
from db.database import get_connection

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent 生命周期状态"""
    DORMANT = "dormant"       # 休眠 - 余额不足或手动暂停
    ACTIVE = "active"         # 活跃 - 正在运行
    THINKING = "thinking"     # 思考中 - 正在分析
    EXECUTING = "executing"   # 执行中 - 正在交易
    STOPPED = "stopped"       # 已停止


@dataclass
class AgentConfig:
    """Agent 运行配置"""
    agent_id: str
    heartbeat_interval: int = 60        # 心跳间隔（秒）
    min_confidence: float = 0.6         # 最低交易信心
    max_position_size: float = 100      # 最大仓位 (USDC)
    risk_per_trade: float = 0.02        # 单笔风险比例
    markets: List[str] = field(default_factory=lambda: ["BTC-PERP", "ETH-PERP"])
    strategy: str = "momentum"          # 策略类型
    auto_broadcast: bool = True         # 自动广播思考
    exploration_rate: float = 0.1       # 无强信号时的探索下单概率


@dataclass
class MarketAnalysis:
    """市场分析结果"""
    market: str
    price: float
    trend: str              # "bullish", "bearish", "neutral"
    strength: float         # 0-1 趋势强度
    signal: str             # "long", "short", "wait"
    confidence: float       # 0-1 信心度
    reasoning: str          # 分析理由


@dataclass  
class TradeDecision:
    """交易决策"""
    action: str             # "open_long", "open_short", "close", "hold"
    market: str
    size: float
    confidence: float
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)


class AgentBrain:
    """
    Agent 决策引擎
    
    简单的动量策略实现，可扩展为更复杂的策略
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.price_history: Dict[str, List[float]] = {}
        
    async def analyze_market(self, market: str) -> MarketAnalysis:
        """分析单个市场"""
        try:
            # 获取当前价格
            prices = price_feed.get_all_prices()
            if asyncio.iscoroutine(prices):
                prices = await prices

            raw_price = prices.get(market) if isinstance(prices, dict) else None
            if isinstance(raw_price, dict):
                current_price = float(raw_price.get("price", 0) or 0)
            else:
                current_price = float(getattr(raw_price, "price", 0) or 0)
            
            if current_price == 0:
                return MarketAnalysis(
                    market=market,
                    price=0,
                    trend="neutral",
                    strength=0,
                    signal="wait",
                    confidence=0,
                    reasoning="No price data available"
                )
            
            # 记录价格历史
            if market not in self.price_history:
                self.price_history[market] = []
            self.price_history[market].append(current_price)
            
            # 保留最近 20 个价格点
            if len(self.price_history[market]) > 20:
                self.price_history[market] = self.price_history[market][-20:]
            
            # 简单动量分析
            history = self.price_history[market]
            if len(history) < 3:
                return MarketAnalysis(
                    market=market,
                    price=current_price,
                    trend="neutral",
                    strength=0.3,
                    signal="wait",
                    confidence=0.3,
                    reasoning="Insufficient price history, waiting for more data"
                )
            
            # 计算短期动量
            short_ma = sum(history[-3:]) / 3
            price_change = (current_price - history[-3]) / history[-3] * 100
            
            # 判断趋势
            if price_change > 0.5:
                trend = "bullish"
                strength = min(abs(price_change) / 2, 1.0)
                signal = "long"
                reasoning = f"Price up {price_change:.2f}% in recent periods, momentum is bullish"
            elif price_change < -0.5:
                trend = "bearish"
                strength = min(abs(price_change) / 2, 1.0)
                signal = "short"
                reasoning = f"Price down {price_change:.2f}% in recent periods, momentum is bearish"
            else:
                trend = "neutral"
                strength = 0.3
                signal = "wait"
                reasoning = f"Price stable ({price_change:.2f}%), no clear direction"
            
            confidence = strength * 0.7 + random.uniform(0, 0.3)  # 加点随机性
            
            return MarketAnalysis(
                market=market,
                price=current_price,
                trend=trend,
                strength=strength,
                signal=signal,
                confidence=min(confidence, 0.95),
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Market analysis error for {market}: {e}")
            return MarketAnalysis(
                market=market,
                price=0,
                trend="neutral",
                strength=0,
                signal="wait",
                confidence=0,
                reasoning=f"Analysis error: {str(e)}"
            )
    
    async def make_decision(self, analyses: List[MarketAnalysis]) -> Optional[TradeDecision]:
        """基于市场分析做出交易决策"""
        
        # 找到最高信心的信号
        best_signal = None
        for analysis in analyses:
            # 仅将可执行方向信号纳入候选；wait 不应阻塞探索分支
            if analysis.signal in {"long", "short"} and analysis.confidence >= self.config.min_confidence:
                if best_signal is None or analysis.confidence > best_signal.confidence:
                    best_signal = analysis
        
        if best_signal is None:
            # Agent-only 模式下保持低频探索，避免长期只“思考不执行”。
            candidates = [a for a in analyses if a.price > 0]
            if candidates and random.random() < self.config.exploration_rate:
                probe = max(candidates, key=lambda a: a.strength)
                if probe.trend == "bullish":
                    side = "long"
                elif probe.trend == "bearish":
                    side = "short"
                else:
                    side = random.choice(["long", "short"])

                return TradeDecision(
                    action=f"open_{side}",
                    market=probe.market,
                    size=max(10.0, self.config.max_position_size * 0.2),
                    confidence=min(0.95, self.config.min_confidence + 0.05),
                    reasoning=(
                        f"Exploratory {side} entry on {probe.market}. "
                        f"No dominant signal; keeping market presence with limited size."
                    ),
                )

            return TradeDecision(
                action="hold",
                market="",
                size=0,
                confidence=0,
                reasoning="No signals meet confidence threshold"
            )
        
        # 计算仓位大小
        size = min(
            self.config.max_position_size * best_signal.confidence,
            self.config.max_position_size
        )
        
        action = f"open_{best_signal.signal}" if best_signal.signal in ["long", "short"] else "hold"
        
        return TradeDecision(
            action=action,
            market=best_signal.market,
            size=size,
            confidence=best_signal.confidence,
            reasoning=best_signal.reasoning
        )


MIN_SOCIAL_BALANCE = 100.0   # 余额低于此值的 Agent 不参与社交
SOCIAL_TICK_INTERVAL = 10    # 每 10 个心跳执行一次社交检查


class AgentRuntime:
    """
    Agent 运行时管理器

    管理多个 agent 的生命周期，协调心跳和决策
    """

    def __init__(self):
        self.agents: Dict[str, AgentConfig] = {}
        self.states: Dict[str, AgentState] = {}
        self.brains: Dict[str, AgentBrain] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._realtime_message_hook: Optional[Callable[[dict], Awaitable[None]]] = None
        self._trade_executor_hook: Optional[
            Callable[[str, str, str, float, float, str], Awaitable[dict]]
        ] = None
        self._heartbeat_counts: Dict[str, int] = {}
        self._last_social_tick: Dict[str, datetime] = {}

    def set_realtime_message_hook(
        self,
        hook: Optional[Callable[[dict], Awaitable[None]]]
    ) -> None:
        """
        Set an async hook for runtime-generated chat messages.
        The API layer uses this to bridge runtime thoughts/signals into WebSocket.
        """
        self._realtime_message_hook = hook

    def set_trade_executor_hook(
        self,
        hook: Optional[Callable[[str, str, str, float, float, str], Awaitable[dict]]]
    ) -> None:
        """
        Set an async hook to execute runtime trade decisions.
        Signature: (agent_id, market, side, size_usdc, confidence, reasoning) -> result dict.
        """
        self._trade_executor_hook = hook

    async def _emit_realtime_message(
        self,
        sender_id: str,
        content: str,
        message_type: str,
        metadata: Optional[dict] = None,
        channel: str = "public",
        message_id: Optional[str] = None,
    ) -> None:
        if not self._realtime_message_hook:
            return

        payload = {
            "id": message_id or f"runtime_{datetime.now().timestamp()}",
            "sender_id": sender_id,
            "sender_name": sender_id,
            "channel": channel,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self._realtime_message_hook(payload)
        except Exception as e:
            logger.warning(f"Failed to emit runtime realtime message: {e}")
    
    def register_agent(self, config: AgentConfig) -> bool:
        """注册一个 agent 到运行时"""
        if config.agent_id in self.agents:
            logger.warning(f"Agent {config.agent_id} already registered")
            return False
        
        self.agents[config.agent_id] = config
        self.states[config.agent_id] = AgentState.DORMANT
        self.brains[config.agent_id] = AgentBrain(config)
        
        logger.info(f"Agent {config.agent_id} registered with {config.strategy} strategy")
        return True
    
    async def start_agent(self, agent_id: str) -> bool:
        """启动一个 agent 的心跳循环"""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not registered")
            return False
        
        if agent_id in self.tasks and not self.tasks[agent_id].done():
            logger.warning(f"Agent {agent_id} already running")
            return False
        
        self.states[agent_id] = AgentState.ACTIVE
        self.tasks[agent_id] = asyncio.create_task(self._heartbeat_loop(agent_id))
        
        # 广播启动消息
        config = self.agents[agent_id]
        if config.auto_broadcast:
            start_content = f"Agent activated. Strategy: {config.strategy}. Monitoring: {', '.join(config.markets)}"
            msg_id = chat_db.save_message(
                sender_id=agent_id,
                content=start_content,
                message_type="system"
            )
            await self._emit_realtime_message(
                sender_id=agent_id,
                content=start_content,
                message_type="system",
                message_id=msg_id,
            )
        
        logger.info(f"Agent {agent_id} started")
        return True
    
    async def stop_agent(self, agent_id: str) -> bool:
        """停止一个 agent"""
        if agent_id not in self.tasks:
            return False
        
        self.states[agent_id] = AgentState.STOPPED
        self.tasks[agent_id].cancel()
        
        try:
            await self.tasks[agent_id]
        except asyncio.CancelledError:
            pass
        
        del self.tasks[agent_id]
        
        # 广播停止消息
        config = self.agents[agent_id]
        if config.auto_broadcast:
            stop_content = "Agent deactivated. Going offline."
            msg_id = chat_db.save_message(
                sender_id=agent_id,
                content=stop_content,
                message_type="system"
            )
            await self._emit_realtime_message(
                sender_id=agent_id,
                content=stop_content,
                message_type="system",
                message_id=msg_id,
            )
        
        logger.info(f"Agent {agent_id} stopped")
        return True
    
    async def _heartbeat_loop(self, agent_id: str):
        """Agent 心跳循环"""
        config = self.agents[agent_id]
        brain = self.brains[agent_id]
        
        logger.info(f"Starting heartbeat loop for {agent_id}")
        
        while self.states[agent_id] == AgentState.ACTIVE:
            try:
                # 更新状态为思考中
                self.states[agent_id] = AgentState.THINKING
                
                # 分析所有关注的市场
                analyses = []
                for market in config.markets:
                    analysis = await brain.analyze_market(market)
                    analyses.append(analysis)
                
                # 做出决策
                decision = await brain.make_decision(analyses)
                
                # 广播思考过程
                if config.auto_broadcast and decision:
                    thought = self._format_thought(analyses, decision)
                    msg_id = chat_db.save_message(
                        sender_id=agent_id,
                        content=thought,
                        message_type="thought",
                        metadata={
                            "markets": [a.market for a in analyses],
                            "decision": decision.action,
                            "confidence": decision.confidence
                        }
                    )
                    await self._emit_realtime_message(
                        sender_id=agent_id,
                        content=thought,
                        message_type="thought",
                        metadata={
                            "markets": [a.market for a in analyses],
                            "decision": decision.action,
                            "confidence": decision.confidence,
                        },
                        message_id=msg_id,
                    )
                
                # 如果有交易决策，执行它
                if decision and decision.action.startswith("open_"):
                    self.states[agent_id] = AgentState.EXECUTING
                    await self._execute_trade(agent_id, decision)

                # 社交 tick — 每 SOCIAL_TICK_INTERVAL 个心跳检查一次
                self._heartbeat_counts[agent_id] = self._heartbeat_counts.get(agent_id, 0) + 1
                if self._heartbeat_counts[agent_id] % SOCIAL_TICK_INTERVAL == 0:
                    await self._social_tick(agent_id)

                # 恢复活跃状态
                self.states[agent_id] = AgentState.ACTIVE

                # 等待下一个心跳
                await asyncio.sleep(config.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error for {agent_id}: {e}")
                await asyncio.sleep(config.heartbeat_interval)
        
        logger.info(f"Heartbeat loop ended for {agent_id}")
    
    def _format_thought(self, analyses: List[MarketAnalysis], decision: TradeDecision) -> str:
        """格式化思考过程为可读文本"""
        parts = []
        
        # 市场分析摘要
        for a in analyses:
            if a.price > 0:
                emoji = "📈" if a.trend == "bullish" else "📉" if a.trend == "bearish" else "➡️"
                parts.append(f"{a.market}: ${a.price:,.0f} {emoji} ({a.trend}, {a.confidence:.0%} conf)")
        
        # 决策
        if decision.action != "hold":
            parts.append(f"Decision: {decision.action.upper()} {decision.market} (${decision.size:.0f})")
            parts.append(f"Reasoning: {decision.reasoning}")
        else:
            parts.append("Holding positions. No strong signals detected.")
        
        return " | ".join(parts)
    
    async def _execute_trade(self, agent_id: str, decision: TradeDecision):
        """执行交易决策"""
        logger.info(f"Agent {agent_id} executing decision: {decision.action} {decision.market} ${decision.size}")

        config = self.agents[agent_id]
        side = "LONG" if "long" in decision.action else "SHORT"

        if not self._trade_executor_hook:
            if config.auto_broadcast:
                signal_content = (
                    f"[SIMULATED] Opening {side} {decision.market} | "
                    f"Size: ${decision.size:.0f} | Confidence: {decision.confidence:.0%}"
                )
                metadata = {
                    "asset": decision.market,
                    "direction": side.lower(),
                    "confidence": decision.confidence,
                    "size": decision.size,
                    "simulated": True,
                }
                msg_id = chat_db.save_message(
                    sender_id=agent_id,
                    content=signal_content,
                    message_type="signal",
                    metadata=metadata
                )
                await self._emit_realtime_message(
                    sender_id=agent_id,
                    content=signal_content,
                    message_type="signal",
                    metadata=metadata,
                    message_id=msg_id,
                )
            return

        try:
            result = await self._trade_executor_hook(
                agent_id,
                decision.market,
                side.lower(),
                float(decision.size),
                float(decision.confidence),
                decision.reasoning,
            )
        except Exception as e:
            logger.error(f"Runtime trade execution failed for {agent_id}: {e}")
            if config.auto_broadcast:
                failure_content = f"Trade execution failed: {e}"
                msg_id = chat_db.save_message(
                    sender_id=agent_id,
                    content=failure_content,
                    message_type="system",
                    metadata={"event": "trade_failed"}
                )
                await self._emit_realtime_message(
                    sender_id=agent_id,
                    content=failure_content,
                    message_type="system",
                    metadata={"event": "trade_failed"},
                    message_id=msg_id,
                )
            return

        if config.auto_broadcast:
            success = bool(result.get("success")) if isinstance(result, dict) else True
            intent = result.get("intent", {}) if isinstance(result, dict) else {}
            if success:
                signal_content = (
                    f"Executed {side} {decision.market} | Size: ${decision.size:.0f} | "
                    f"Confidence: {decision.confidence:.0%}"
                )
                if intent.get("intent_id"):
                    signal_content += f" | Intent: {intent['intent_id']}"
                message_type = "signal"
                extra = {"event": "trade_executed"}
            else:
                signal_content = f"Execution rejected: {result.get('error', 'unknown error')}"
                message_type = "system"
                extra = {"event": "trade_rejected"}

            metadata = {
                "asset": decision.market,
                "direction": side.lower(),
                "confidence": decision.confidence,
                "size": decision.size,
                "result": result if isinstance(result, dict) else {"success": success},
                **extra,
            }
            msg_id = chat_db.save_message(
                sender_id=agent_id,
                content=signal_content,
                message_type=message_type,
                metadata=metadata
            )
            await self._emit_realtime_message(
                sender_id=agent_id,
                content=signal_content,
                message_type=message_type,
                metadata=metadata,
                message_id=msg_id,
            )
    
    async def _social_tick(self, agent_id: str):
        """
        Proof-of-Trade 社交行为 — 只在有交易可以背书时才发帖。

        规则:
        - 余额 < MIN_SOCIAL_BALANCE → 沉默
        - 最近没有交易 → 没有资格发帖
        - 频率 ∝ reputation (Sharpe 高的 Agent 可以更频繁)
        """
        try:
            # 惰性导入，避免循环依赖
            from services.settlement import settlement_engine
            from services.circles import circle_service
            from services.position_manager import position_manager

            # 余额检查 — 穷 Agent 沉默
            balance_info = settlement_engine.get_balance(agent_id)
            if not balance_info or balance_info.available < MIN_SOCIAL_BALANCE:
                return

            # 检查最近交易 — 没交易 = 没资格发帖
            last_tick = self._last_social_tick.get(agent_id, datetime.min)
            open_positions = position_manager.get_positions(agent_id)
            if not open_positions:
                return

            # 找到最近一笔仓位
            latest = max(open_positions, key=lambda p: p.get("opened_at", ""))
            if not latest:
                return

            # 找相关 Circle 并发帖
            asset = latest.get("asset", "")
            circle = circle_service.find_relevant_circle(asset)
            if not circle:
                return

            # 检查是否是 Circle 成员
            members = circle_service.get_members(circle["circle_id"])
            member_ids = [m["agent_id"] for m in members] if isinstance(members, list) else []
            if agent_id not in member_ids:
                # 自动加入
                try:
                    circle_service.join_circle(circle["circle_id"], agent_id)
                except ValueError:
                    return  # 不满足准入条件

            # 生成帖子内容
            side = latest.get("side", "LONG")
            size = latest.get("size_usdc", 0)
            pnl = latest.get("unrealized_pnl", 0)
            leverage = latest.get("leverage", 1)

            content = (
                f"Holding {side} {asset} | ${size:.0f} @ {leverage}x | "
                f"PnL: {'+'if pnl >= 0 else ''}{pnl:.2f} USDC"
            )

            position_id = latest.get("position_id", "")
            try:
                circle_service.create_post(
                    circle_id=circle["circle_id"],
                    author_id=agent_id,
                    content=content,
                    post_type="analysis",
                    linked_trade_id=position_id,
                )
                logger.info(f"[Social] {agent_id} posted to circle {circle['name']}")
            except ValueError as e:
                # 速率限制或其他验证失败 — 静默跳过
                logger.debug(f"[Social] {agent_id} post skipped: {e}")

            self._last_social_tick[agent_id] = datetime.now()

        except Exception as e:
            logger.warning(f"[Social] _social_tick error for {agent_id}: {e}")

    def get_status(self, agent_id: str = None) -> Dict[str, Any]:
        """获取 agent 状态"""
        if agent_id:
            if agent_id not in self.agents:
                return {"error": "Agent not found"}
            return {
                "agent_id": agent_id,
                "state": self.states.get(agent_id, AgentState.STOPPED).value,
                "config": {
                    "heartbeat_interval": self.agents[agent_id].heartbeat_interval,
                    "markets": self.agents[agent_id].markets,
                    "strategy": self.agents[agent_id].strategy,
                },
                "is_running": agent_id in self.tasks and not self.tasks[agent_id].done()
            }
        
        # 返回所有 agent 状态
        return {
            "total_agents": len(self.agents),
            "running_agents": sum(1 for t in self.tasks.values() if not t.done()),
            "agents": {
                aid: {
                    "state": self.states.get(aid, AgentState.STOPPED).value,
                    "is_running": aid in self.tasks and not self.tasks[aid].done()
                }
                for aid in self.agents
            }
        }


# 单例
agent_runtime = AgentRuntime()


# === 便捷函数 ===

def create_demo_agent(agent_id: str = "demo_agent") -> AgentConfig:
    """创建一个演示 agent"""
    config = AgentConfig(
        agent_id=agent_id,
        heartbeat_interval=30,  # 30秒心跳
        min_confidence=0.5,
        max_position_size=50,
        markets=["BTC-PERP", "ETH-PERP", "SOL-PERP"],
        strategy="momentum",
        auto_broadcast=True
    )
    agent_runtime.register_agent(config)
    return config
