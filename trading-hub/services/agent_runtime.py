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
from typing import Optional, Dict, List, Callable, Any
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
            current_price = price_feed.get_cached_price(market)
            if current_price == 0:
                latest = await price_feed.get_price(market)
                current_price = latest.price if latest else 0
            
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
            if analysis.confidence >= self.config.min_confidence:
                if best_signal is None or analysis.confidence > best_signal.confidence:
                    best_signal = analysis
        
        if best_signal is None:
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

    def _safe_save_message(
        self,
        sender_id: str,
        content: str,
        message_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Best-effort chat persistence. Runtime should not fail if chat DB is unavailable."""
        try:
            chat_db.save_message(
                sender_id=sender_id,
                content=content,
                message_type=message_type,
                metadata=metadata,
            )
        except Exception as e:
            logger.debug(f"Skip runtime chat persistence for {sender_id}: {e}")
    
    def register_agent(self, config: AgentConfig) -> bool:
        """注册一个 agent 到运行时"""
        if config.agent_id in self.agents:
            # 允许幂等更新配置（用于重复 deploy / runtime start）
            self.agents[config.agent_id] = config
            self.brains[config.agent_id] = AgentBrain(config)
            if config.agent_id not in self.states:
                self.states[config.agent_id] = AgentState.DORMANT
            logger.info(f"Agent {config.agent_id} config updated")
            return True
        
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
            # 幂等语义：已在运行视为成功
            logger.info(f"Agent {agent_id} already running")
            return True
        
        self.states[agent_id] = AgentState.ACTIVE
        self.tasks[agent_id] = asyncio.create_task(self._heartbeat_loop(agent_id))
        
        # 广播启动消息
        config = self.agents[agent_id]
        if config.auto_broadcast:
            self._safe_save_message(
                sender_id=agent_id,
                content=f"Agent activated. Strategy: {config.strategy}. Monitoring: {', '.join(config.markets)}",
                message_type="system"
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
            self._safe_save_message(
                sender_id=agent_id,
                content="Agent deactivated. Going offline.",
                message_type="system"
            )
        
        logger.info(f"Agent {agent_id} stopped")
        return True
    
    async def _heartbeat_loop(self, agent_id: str):
        """Agent 心跳循环"""
        logger.info(f"Starting heartbeat loop for {agent_id}")
        
        while self.states[agent_id] == AgentState.ACTIVE:
            try:
                config = self.agents.get(agent_id)
                if config is None:
                    logger.warning(f"Agent {agent_id} config missing, stopping heartbeat")
                    break
                brain = self.brains.get(agent_id)
                if brain is None:
                    logger.warning(f"Agent {agent_id} brain missing, stopping heartbeat")
                    break

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
                    self._safe_save_message(
                        sender_id=agent_id,
                        content=thought,
                        message_type="thought",
                        metadata={
                            "markets": [a.market for a in analyses],
                            "decision": decision.action,
                            "confidence": decision.confidence
                        }
                    )
                
                # 如果有交易决策，执行它
                if decision and decision.action.startswith("open_"):
                    self.states[agent_id] = AgentState.EXECUTING
                    await self._execute_trade(agent_id, decision)
                
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
        side = "long" if "long" in decision.action else "short"
        size_usdc = max(1.0, round(float(decision.size), 2))
        leverage = max(1, min(10, int(2 + decision.confidence * 8)))

        # 价格优先走缓存，不命中时异步拉取
        entry_price = price_feed.get_cached_price(decision.market)
        if entry_price <= 0:
            latest = await price_feed.get_price(decision.market)
            entry_price = latest.price if latest else 0
        if entry_price <= 0:
            logger.warning(f"Runtime trade skipped for {agent_id}: no price for {decision.market}")
            return

        from services.position_manager import position_manager
        from db.redis_store import store

        try:
            position = position_manager.open_position(
                agent_id=agent_id,
                asset=decision.market,
                side=side,
                size_usdc=size_usdc,
                entry_price=entry_price,
                leverage=leverage,
            )

            # 同步交易统计
            agent = store.get_agent(agent_id)
            if agent:
                store.update_agent(
                    agent_id,
                    total_trades=agent.total_trades + 1,
                    total_volume=agent.total_volume + size_usdc,
                )

            logger.info(
                f"Runtime trade executed: {agent_id} {side.upper()} {decision.market} "
                f"size=${size_usdc:.2f} lev={leverage}x pos={position.position_id}"
            )

            config = self.agents[agent_id]
            if config.auto_broadcast:
                self._safe_save_message(
                    sender_id=agent_id,
                    content=(
                        f"Opened {side.upper()} {decision.market} | Size: ${size_usdc:.0f} "
                        f"| Lev: {leverage}x | Confidence: {decision.confidence:.0%}"
                    ),
                    message_type="signal",
                    metadata={
                        "asset": decision.market,
                        "direction": side,
                        "confidence": decision.confidence,
                        "size": size_usdc,
                        "leverage": leverage,
                        "position_id": position.position_id,
                    },
                )
        except Exception as e:
            logger.warning(f"Runtime trade rejected for {agent_id}: {e}")
            config = self.agents.get(agent_id)
            if config and config.auto_broadcast:
                self._safe_save_message(
                    sender_id=agent_id,
                    content=f"Trade rejected: {side.upper()} {decision.market} (${size_usdc:.0f}) | Reason: {e}",
                    message_type="system",
                    metadata={
                        "asset": decision.market,
                        "direction": side,
                        "size": size_usdc,
                        "error": str(e),
                    },
                )
    
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
