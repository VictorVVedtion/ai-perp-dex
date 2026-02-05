"""
Risk Limits - 单 Agent 风险限额

防止单个 Agent:
1. 过度杠杆
2. 过大仓位
3. 过度亏损
4. 频繁交易
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentRiskLimits:
    """Agent 风险限额配置"""
    agent_id: str
    
    # 仓位限制
    max_position_size: float = 10000  # 单笔最大 $10000
    max_total_exposure: float = 50000  # 总敞口最大 $50000
    max_leverage: int = 20  # 最大杠杆 (与 PositionManager.MAX_LEVERAGE 保持一致)
    
    # 亏损限制
    max_daily_loss: float = 1000  # 每日最大亏损 $1000
    max_daily_loss_pct: float = 0.1  # 每日最大亏损 10%
    max_drawdown_pct: float = 0.3  # 最大回撤 30%
    
    # 交易限制
    max_trades_per_hour: int = 50  # 每小时最多 50 笔
    max_trades_per_day: int = 500  # 每天最多 500 笔
    min_trade_interval_seconds: int = 5  # 最小交易间隔 5 秒
    
    # 状态
    is_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "max_position_size": self.max_position_size,
            "max_total_exposure": self.max_total_exposure,
            "max_leverage": self.max_leverage,
            "max_daily_loss": self.max_daily_loss,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_trades_per_hour": self.max_trades_per_hour,
            "max_trades_per_day": self.max_trades_per_day,
            "is_enabled": self.is_enabled,
        }


@dataclass
class RiskViolation:
    """风险违规记录"""
    violation_id: str
    agent_id: str
    violation_type: str
    message: str
    severity: RiskLevel
    value: float
    limit: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "agent_id": self.agent_id,
            "type": self.violation_type,
            "message": self.message,
            "severity": self.severity.value,
            "value": self.value,
            "limit": self.limit,
            "timestamp": self.timestamp.isoformat(),
        }


class RiskManager:
    """
    风险管理器
    
    用法:
        rm = RiskManager()
        
        # 检查交易是否允许
        allowed, violations = rm.check_trade(
            agent_id="agent_001",
            size=1000,
            leverage=10,
        )
        
        if not allowed:
            for v in violations:
                print(f"Violation: {v.message}")
    """
    
    def __init__(self, position_manager=None, settlement_engine=None):
        self.position_manager = position_manager
        self.settlement_engine = settlement_engine
        
        # Agent 限额配置
        self.limits: Dict[str, AgentRiskLimits] = {}
        
        # 违规记录
        self.violations: List[RiskViolation] = []
        
        # 每日统计
        self.daily_stats: Dict[str, dict] = {}  # agent_id -> {trades, pnl, ...}
        
        # 交易记录 (用于频率检查)
        self.trade_times: Dict[str, List[datetime]] = {}
        
        print("🛡️ Risk Manager started")
    
    def get_limits(self, agent_id: str) -> AgentRiskLimits:
        """获取 Agent 限额 (如果没有则创建默认)"""
        if agent_id not in self.limits:
            self.limits[agent_id] = AgentRiskLimits(agent_id=agent_id)
        return self.limits[agent_id]
    
    def set_limits(self, agent_id: str, **kwargs) -> AgentRiskLimits:
        """设置 Agent 限额"""
        limits = self.get_limits(agent_id)
        for key, value in kwargs.items():
            if hasattr(limits, key):
                setattr(limits, key, value)
        return limits
    
    def check_trade(
        self,
        agent_id: str,
        size: float,
        leverage: int,
        side: str = "long",
    ) -> Tuple[bool, List[RiskViolation]]:
        """
        检查交易是否允许
        
        Returns:
            (allowed: bool, violations: List[RiskViolation])
        """
        limits = self.get_limits(agent_id)
        violations = []
        
        if not limits.is_enabled:
            return True, []
        
        # 0. 检查零/负金额
        if size <= 0:
            violations.append(self._create_violation(
                agent_id,
                "zero_size",
                f"Trade size must be positive, got {size}",
                RiskLevel.HIGH,
                size,
                0.01,  # 最小交易额
            ))
            return False, violations  # 立即返回，不检查其他
        
        # 1. 检查仓位大小
        if size > limits.max_position_size:
            violations.append(self._create_violation(
                agent_id,
                "position_size",
                f"Position size ${size} exceeds limit ${limits.max_position_size}",
                RiskLevel.HIGH,
                size,
                limits.max_position_size,
            ))
        
        # 2. 检查杠杆
        if leverage > limits.max_leverage:
            violations.append(self._create_violation(
                agent_id,
                "leverage",
                f"Leverage {leverage}x exceeds limit {limits.max_leverage}x",
                RiskLevel.HIGH,
                leverage,
                limits.max_leverage,
            ))
        
        # 3. 检查总敞口
        current_exposure = self._get_total_exposure(agent_id)
        new_exposure = current_exposure + size
        if new_exposure > limits.max_total_exposure:
            violations.append(self._create_violation(
                agent_id,
                "total_exposure",
                f"Total exposure ${new_exposure} exceeds limit ${limits.max_total_exposure}",
                RiskLevel.CRITICAL,
                new_exposure,
                limits.max_total_exposure,
            ))
        
        # 4. 检查每日亏损
        daily_pnl = self._get_daily_pnl(agent_id)
        if daily_pnl < -limits.max_daily_loss:
            violations.append(self._create_violation(
                agent_id,
                "daily_loss",
                f"Daily loss ${-daily_pnl} exceeds limit ${limits.max_daily_loss}",
                RiskLevel.CRITICAL,
                -daily_pnl,
                limits.max_daily_loss,
            ))
        
        # 5. 检查交易频率
        freq_violation = self._check_trade_frequency(agent_id, limits)
        if freq_violation:
            violations.append(freq_violation)
        
        # 6. 检查最大回撤
        drawdown = self._get_drawdown(agent_id)
        if drawdown > limits.max_drawdown_pct:
            violations.append(self._create_violation(
                agent_id,
                "drawdown",
                f"Drawdown {drawdown*100:.1f}% exceeds limit {limits.max_drawdown_pct*100:.1f}%",
                RiskLevel.CRITICAL,
                drawdown,
                limits.max_drawdown_pct,
            ))
        
        # 记录违规
        self.violations.extend(violations)
        
        allowed = len(violations) == 0
        return allowed, violations
    
    def _create_violation(
        self,
        agent_id: str,
        violation_type: str,
        message: str,
        severity: RiskLevel,
        value: float,
        limit: float,
    ) -> RiskViolation:
        """创建违规记录"""
        import uuid
        return RiskViolation(
            violation_id=f"viol_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            violation_type=violation_type,
            message=message,
            severity=severity,
            value=value,
            limit=limit,
        )
    
    def _get_total_exposure(self, agent_id: str) -> float:
        """获取总敞口"""
        if not self.position_manager:
            return 0
        positions = self.position_manager.get_positions(agent_id)
        return sum(p.size_usdc for p in positions)
    
    def _get_max_leverage(self, agent_id: str) -> float:
        """获取当前最大使用杠杆"""
        if not self.position_manager:
            return 0
        positions = self.position_manager.get_positions(agent_id)
        if not positions:
            return 0
        return max(p.leverage for p in positions)

    def _get_daily_pnl(self, agent_id: str) -> float:
        """获取每日 PnL"""
        stats = self.daily_stats.get(agent_id, {})
        return stats.get("realized_pnl", 0) + stats.get("unrealized_pnl", 0)
    
    def _get_drawdown(self, agent_id: str) -> float:
        """获取最大回撤"""
        stats = self.daily_stats.get(agent_id, {})
        peak = stats.get("peak_balance", 1000)
        current = stats.get("current_balance", 1000)
        if peak <= 0:
            return 0
        return max(0, (peak - current) / peak)
    
    def _check_trade_frequency(self, agent_id: str, limits: AgentRiskLimits) -> Optional[RiskViolation]:
        """检查交易频率"""
        now = datetime.now()
        
        if agent_id not in self.trade_times:
            self.trade_times[agent_id] = []
        
        times = self.trade_times[agent_id]
        
        # 清理过期记录
        one_day_ago = now - timedelta(days=1)
        times = [t for t in times if t > one_day_ago]
        self.trade_times[agent_id] = times
        
        # 检查最小间隔
        if times:
            last_trade = times[-1]
            interval = (now - last_trade).total_seconds()
            if interval < limits.min_trade_interval_seconds:
                return self._create_violation(
                    agent_id,
                    "trade_interval",
                    f"Trade interval {interval:.1f}s below minimum {limits.min_trade_interval_seconds}s",
                    RiskLevel.MEDIUM,
                    interval,
                    limits.min_trade_interval_seconds,
                )
        
        # 检查每小时限制
        one_hour_ago = now - timedelta(hours=1)
        trades_hour = sum(1 for t in times if t > one_hour_ago)
        if trades_hour >= limits.max_trades_per_hour:
            return self._create_violation(
                agent_id,
                "trades_per_hour",
                f"Trades per hour {trades_hour} exceeds limit {limits.max_trades_per_hour}",
                RiskLevel.HIGH,
                trades_hour,
                limits.max_trades_per_hour,
            )
        
        # 检查每日限制
        if len(times) >= limits.max_trades_per_day:
            return self._create_violation(
                agent_id,
                "trades_per_day",
                f"Trades per day {len(times)} exceeds limit {limits.max_trades_per_day}",
                RiskLevel.HIGH,
                len(times),
                limits.max_trades_per_day,
            )
        
        return None
    
    def record_trade(self, agent_id: str):
        """记录交易 (用于频率检查)"""
        if agent_id not in self.trade_times:
            self.trade_times[agent_id] = []
        self.trade_times[agent_id].append(datetime.now())
    
    def update_daily_stats(self, agent_id: str, realized_pnl: float = 0, unrealized_pnl: float = 0):
        """更新每日统计"""
        if agent_id not in self.daily_stats:
            self.daily_stats[agent_id] = {
                "date": datetime.now().date(),
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "peak_balance": 1000,
                "current_balance": 1000,
                "trades": 0,
            }
        
        stats = self.daily_stats[agent_id]
        
        # 检查是否需要重置 (新的一天)
        if stats["date"] != datetime.now().date():
            stats["date"] = datetime.now().date()
            stats["realized_pnl"] = 0
            stats["trades"] = 0
        
        stats["realized_pnl"] += realized_pnl
        stats["unrealized_pnl"] = unrealized_pnl
        stats["trades"] += 1
        
        # 更新余额
        if self.settlement_engine:
            balance = self.settlement_engine.get_balance(agent_id)
            current = balance.balance_usdc + unrealized_pnl
            stats["current_balance"] = current
            stats["peak_balance"] = max(stats["peak_balance"], current)
    
    def get_risk_score(self, agent_id: str) -> dict:
        """获取风险评分"""
        limits = self.get_limits(agent_id)

        # 各维度评分 (0-100, 越高越危险)
        exposure_score = min(100, self._get_total_exposure(agent_id) / limits.max_total_exposure * 100)
        loss_score = min(100, max(0, -self._get_daily_pnl(agent_id)) / limits.max_daily_loss * 100)
        drawdown_score = min(100, self._get_drawdown(agent_id) / limits.max_drawdown_pct * 100)
        leverage_score = min(100, self._get_max_leverage(agent_id) / limits.max_leverage * 100)

        # 综合评分 (杠杆权重较高，因为杠杆直接放大风险)
        overall = (exposure_score + loss_score + drawdown_score + leverage_score * 1.5) / 4.5

        if overall < 30:
            level = RiskLevel.LOW
        elif overall < 60:
            level = RiskLevel.MEDIUM
        elif overall < 80:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL

        return {
            "agent_id": agent_id,
            "overall_score": round(overall, 1),
            "level": level.value,
            "breakdown": {
                "exposure": round(exposure_score, 1),
                "daily_loss": round(loss_score, 1),
                "drawdown": round(drawdown_score, 1),
                "leverage": round(leverage_score, 1),
            },
        }
    
    def get_violations(self, agent_id: str = None, limit: int = 50) -> List[RiskViolation]:
        """获取违规记录"""
        violations = self.violations
        if agent_id:
            violations = [v for v in violations if v.agent_id == agent_id]
        return violations[-limit:]


# 单例
risk_manager = RiskManager()
