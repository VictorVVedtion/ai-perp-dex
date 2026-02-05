"""
Position Manager - 持仓管理 + 止盈止损 + 风控

为 AI Agent 提供完整的仓位管理功能
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Callable
from enum import Enum
import uuid


class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass
class Position:
    """持仓"""
    position_id: str
    agent_id: str
    asset: str
    side: PositionSide
    size_usdc: float
    entry_price: float
    leverage: int
    created_at: datetime = field(default_factory=datetime.now)
    
    # 止盈止损
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # 实时数据
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    liquidation_price: float = 0.0
    
    # 状态
    is_open: bool = True
    closed_at: Optional[datetime] = None
    close_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    close_reason: Optional[str] = None
    
    def update_pnl(self, current_price: float):
        """更新 PnL"""
        self.current_price = current_price
        
        if self.side == PositionSide.LONG:
            price_change_pct = (current_price - self.entry_price) / self.entry_price
        else:
            price_change_pct = (self.entry_price - current_price) / self.entry_price
        
        self.unrealized_pnl_pct = price_change_pct * self.leverage * 100
        self.unrealized_pnl = self.size_usdc * price_change_pct * self.leverage
        
        # 计算强平价格 (简化: 亏损 80% 保证金时强平)
        margin = self.size_usdc / self.leverage
        max_loss = margin * 0.8
        max_loss_pct = max_loss / self.size_usdc / self.leverage
        
        if self.side == PositionSide.LONG:
            self.liquidation_price = self.entry_price * (1 - max_loss_pct)
        else:
            self.liquidation_price = self.entry_price * (1 + max_loss_pct)
    
    def should_stop_loss(self) -> bool:
        """是否触发止损"""
        if not self.stop_loss or not self.current_price:
            return False
        
        if self.side == PositionSide.LONG:
            return self.current_price <= self.stop_loss
        else:
            return self.current_price >= self.stop_loss
    
    def should_take_profit(self) -> bool:
        """是否触发止盈"""
        if not self.take_profit or not self.current_price:
            return False
        
        if self.side == PositionSide.LONG:
            return self.current_price >= self.take_profit
        else:
            return self.current_price <= self.take_profit
    
    def to_dict(self) -> dict:
        return {
            "position_id": self.position_id,
            "agent_id": self.agent_id,
            "asset": self.asset,
            "side": self.side.value,
            "size_usdc": self.size_usdc,
            "entry_price": self.entry_price,
            "leverage": self.leverage,
            "current_price": self.current_price,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2),
            "liquidation_price": round(self.liquidation_price, 2),
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "is_open": self.is_open,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RiskAlert:
    """风控告警"""
    alert_id: str
    agent_id: str
    position_id: str
    alert_type: str  # "liquidation_warning", "stop_loss_triggered", "take_profit_triggered", "daily_loss_limit"
    message: str
    severity: str  # "info", "warning", "critical"
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


class PositionManager:
    """
    持仓管理器
    
    功能:
    1. 持仓追踪
    2. 实时 PnL 计算
    3. 止盈止损自动执行
    4. 风控告警
    """
    
    # 支持的资产白名单
    SUPPORTED_ASSETS = {"BTC-PERP", "ETH-PERP", "SOL-PERP"}
    
    # 风控参数
    LIQUIDATION_WARNING_THRESHOLD = 0.5  # 亏损 50% 保证金时警告
    DAILY_LOSS_LIMIT_PCT = 0.1  # 每日最大亏损 10%
    MAX_LEVERAGE = 100
    MAX_POSITION_SIZE = 10000  # 单笔最大 $10000
    
    def __init__(self, price_feed=None):
        self.positions: Dict[str, Position] = {}
        self.alerts: Dict[str, RiskAlert] = {}
        self.price_feed = price_feed
        
        # Agent 账户
        self.agent_balances: Dict[str, float] = {}  # agent_id -> balance
        self.agent_daily_pnl: Dict[str, float] = {}  # agent_id -> daily pnl
        
        # 回调
        self._on_alert_callbacks: List[Callable] = []
        self._on_close_callbacks: List[Callable] = []
        
        # 后台任务
        self._running = False
        self._monitor_task = None
    
    async def start(self):
        """启动持仓监控"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        print("📊 Position Manager started")
    
    async def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
    
    async def _monitor_loop(self):
        """持仓监控循环"""
        while self._running:
            await asyncio.sleep(5)  # 每 5 秒检查一次
            await self._check_all_positions()
    
    async def _check_all_positions(self):
        """检查所有持仓"""
        for pos in list(self.positions.values()):
            if not pos.is_open:
                continue
            
            # 更新价格
            if self.price_feed:
                asset = pos.asset.replace("-PERP", "")
                price = self.price_feed.get_price(asset)
                pos.update_pnl(price)
            
            # 检查止损
            if pos.should_stop_loss():
                await self._close_position(pos, "stop_loss")
                self._create_alert(
                    pos.agent_id, pos.position_id,
                    "stop_loss_triggered",
                    f"止损触发: {pos.asset} @ ${pos.current_price:.2f}",
                    "warning"
                )
            
            # 检查止盈
            elif pos.should_take_profit():
                await self._close_position(pos, "take_profit")
                self._create_alert(
                    pos.agent_id, pos.position_id,
                    "take_profit_triggered",
                    f"止盈触发: {pos.asset} @ ${pos.current_price:.2f}",
                    "info"
                )
            
            # 检查强平风险
            elif self._check_liquidation_risk(pos):
                self._create_alert(
                    pos.agent_id, pos.position_id,
                    "liquidation_warning",
                    f"⚠️ 强平预警: {pos.asset} 已亏损 {abs(pos.unrealized_pnl_pct):.1f}%",
                    "critical"
                )
    
    def _check_liquidation_risk(self, pos: Position) -> bool:
        """检查强平风险"""
        # 亏损超过阈值时警告
        if pos.unrealized_pnl_pct < -self.LIQUIDATION_WARNING_THRESHOLD * 100:
            # 避免重复告警
            for alert in self.alerts.values():
                if (alert.position_id == pos.position_id and 
                    alert.alert_type == "liquidation_warning" and
                    not alert.acknowledged):
                    return False
            return True
        return False
    
    def open_position(
        self,
        agent_id: str,
        asset: str,
        side: str,
        size_usdc: float,
        entry_price: float,
        leverage: int = 1,
        stop_loss: float = None,
        take_profit: float = None,
    ) -> Position:
        """
        开仓
        
        自动设置默认止损止盈
        """
        # 资产白名单验证
        if asset not in self.SUPPORTED_ASSETS:
            raise ValueError(f"Unsupported asset: {asset}. Supported: {self.SUPPORTED_ASSETS}")
        
        # 金额验证
        if size_usdc <= 0:
            raise ValueError(f"Position size must be positive, got {size_usdc}")
        
        # 风控检查
        if size_usdc > self.MAX_POSITION_SIZE:
            raise ValueError(f"Position size exceeds limit: ${self.MAX_POSITION_SIZE}")
        if leverage > self.MAX_LEVERAGE:
            raise ValueError(f"Leverage exceeds limit: {self.MAX_LEVERAGE}x")
        
        # 检查每日亏损限额
        daily_pnl = self.agent_daily_pnl.get(agent_id, 0)
        balance = self.agent_balances.get(agent_id, 1000)  # 默认 $1000
        if daily_pnl < -balance * self.DAILY_LOSS_LIMIT_PCT:
            raise ValueError(f"Daily loss limit reached: ${daily_pnl:.2f}")
        
        position_id = f"pos_{uuid.uuid4().hex[:12]}"
        position_side = PositionSide.LONG if side == "long" else PositionSide.SHORT
        
        # 自动设置止损止盈 (如果未指定)
        if stop_loss is None:
            # 默认止损: 亏损 10%
            if position_side == PositionSide.LONG:
                stop_loss = entry_price * 0.9
            else:
                stop_loss = entry_price * 1.1
        
        if take_profit is None:
            # 默认止盈: 盈利 20%
            if position_side == PositionSide.LONG:
                take_profit = entry_price * 1.2
            else:
                take_profit = entry_price * 0.8
        
        position = Position(
            position_id=position_id,
            agent_id=agent_id,
            asset=asset,
            side=position_side,
            size_usdc=size_usdc,
            entry_price=entry_price,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        
        position.update_pnl(entry_price)
        self.positions[position_id] = position
        
        return position
    
    async def _close_position(self, pos: Position, reason: str):
        """平仓"""
        pos.is_open = False
        pos.closed_at = datetime.now()
        pos.close_price = pos.current_price
        pos.realized_pnl = pos.unrealized_pnl
        pos.close_reason = reason
        
        # 更新每日 PnL
        agent_id = pos.agent_id
        self.agent_daily_pnl[agent_id] = self.agent_daily_pnl.get(agent_id, 0) + pos.realized_pnl
        
        # 触发回调
        for cb in self._on_close_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(pos)
                else:
                    cb(pos)
            except:
                pass
    
    def close_position_manual(self, position_id: str, close_price: float) -> Position:
        """手动平仓"""
        pos = self.positions.get(position_id)
        if not pos or not pos.is_open:
            raise ValueError("Position not found or already closed")
        
        pos.update_pnl(close_price)
        
        # 同步平仓 (不依赖事件循环)
        pos.is_open = False
        pos.closed_at = datetime.now()
        pos.close_price = close_price
        pos.realized_pnl = pos.unrealized_pnl
        pos.close_reason = "manual"
        
        # 更新每日 PnL
        agent_id = pos.agent_id
        self.agent_daily_pnl[agent_id] = self.agent_daily_pnl.get(agent_id, 0) + pos.realized_pnl
        
        return pos
    
    def set_stop_loss(self, position_id: str, price: float):
        """设置止损"""
        pos = self.positions.get(position_id)
        if not pos:
            raise ValueError("Position not found")
        pos.stop_loss = price
    
    def set_take_profit(self, position_id: str, price: float):
        """设置止盈"""
        pos = self.positions.get(position_id)
        if not pos:
            raise ValueError("Position not found")
        pos.take_profit = price
    
    def _create_alert(self, agent_id: str, position_id: str, alert_type: str, message: str, severity: str):
        """创建告警"""
        alert = RiskAlert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            position_id=position_id,
            alert_type=alert_type,
            message=message,
            severity=severity,
        )
        self.alerts[alert.alert_id] = alert
        
        # 触发回调
        for cb in self._on_alert_callbacks:
            try:
                cb(alert)
            except:
                pass
        
        return alert
    
    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self._on_alert_callbacks.append(callback)
    
    def on_close(self, callback: Callable):
        """注册平仓回调"""
        self._on_close_callbacks.append(callback)
    
    def get_positions(self, agent_id: str, only_open: bool = True) -> List[Position]:
        """获取 Agent 的持仓"""
        positions = [p for p in self.positions.values() if p.agent_id == agent_id]
        if only_open:
            positions = [p for p in positions if p.is_open]
        return positions
    
    def get_portfolio_value(self, agent_id: str) -> dict:
        """获取投资组合价值"""
        positions = self.get_positions(agent_id, only_open=True)
        
        total_size = sum(p.size_usdc for p in positions)
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        total_margin = sum(p.size_usdc / p.leverage for p in positions)
        
        return {
            "agent_id": agent_id,
            "open_positions": len(positions),
            "total_size": total_size,
            "total_margin": total_margin,
            "unrealized_pnl": round(total_unrealized_pnl, 2),
            "daily_pnl": round(self.agent_daily_pnl.get(agent_id, 0), 2),
            "positions": [p.to_dict() for p in positions],
        }
    
    def get_alerts(self, agent_id: str, unacknowledged_only: bool = True) -> List[RiskAlert]:
        """获取告警"""
        alerts = [a for a in self.alerts.values() if a.agent_id == agent_id]
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return alerts
    
    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.acknowledged = True


# 单例
position_manager = PositionManager()
