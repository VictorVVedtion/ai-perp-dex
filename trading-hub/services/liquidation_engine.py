"""
Liquidation Engine - 清算引擎

功能:
1. 监控所有仓位健康度
2. 触发强平
3. 收取 0.5% 清算费
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Callable
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class LiquidationStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class LiquidationRecord:
    """清算记录"""
    liquidation_id: str
    position_id: str
    agent_id: str
    asset: str
    side: str
    
    # 仓位信息
    size_usdc: float
    entry_price: float
    liquidation_price: float
    mark_price: float  # 触发清算时的价格
    
    # 损益
    pnl: float  # 清算前的未实现盈亏
    margin_remaining: float  # 剩余保证金
    
    # 费用
    liquidation_fee: float  # 0.5%
    
    # 状态
    status: LiquidationStatus = LiquidationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "liquidation_id": self.liquidation_id,
            "position_id": self.position_id,
            "agent_id": self.agent_id,
            "asset": self.asset,
            "side": self.side,
            "size_usdc": self.size_usdc,
            "entry_price": self.entry_price,
            "liquidation_price": round(self.liquidation_price, 2),
            "mark_price": round(self.mark_price, 2),
            "pnl": round(self.pnl, 2),
            "margin_remaining": round(self.margin_remaining, 2),
            "liquidation_fee": round(self.liquidation_fee, 4),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


class LiquidationEngine:
    """清算引擎"""
    
    # 清算费率 0.5%
    LIQUIDATION_FEE_RATE = 0.005
    
    # 维持保证金率 (低于此触发清算)
    MAINTENANCE_MARGIN_RATE = 0.05  # 5%
    
    # 检查间隔
    CHECK_INTERVAL_SECONDS = 5
    
    def __init__(self):
        self.records: Dict[str, LiquidationRecord] = {}
        self.position_manager = None  # 稍后注入
        self.price_feed = None  # 稍后注入
        self.fee_service = None  # 稍后注入
        self.running = False
        self._task = None
        
        # 回调
        self._on_liquidation: Optional[Callable] = None
    
    def set_dependencies(self, position_manager, price_feed, fee_service):
        """注入依赖"""
        self.position_manager = position_manager
        self.price_feed = price_feed
        self.fee_service = fee_service
    
    def on_liquidation(self, callback: Callable):
        """注册清算回调"""
        self._on_liquidation = callback
        return callback
    
    async def start(self):
        """启动清算引擎"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Liquidation engine started")
    
    async def stop(self):
        """停止清算引擎"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Liquidation engine stopped")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                await self._check_all_positions()
            except Exception as e:
                logger.error(f"Liquidation check error: {e}")
            
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
    
    async def _check_all_positions(self):
        """检查所有仓位"""
        if not self.position_manager:
            return
        
        positions = self.position_manager.get_all_positions()
        
        for pos in positions:
            if pos.size_usdc <= 0:
                continue
            
            # 获取当前价格
            current_price = self._get_current_price(pos.asset)
            if not current_price:
                continue
            
            # 检查是否需要清算
            should_liquidate, health = self._check_health(pos, current_price)
            
            if should_liquidate:
                await self._execute_liquidation(pos, current_price, health)
    
    def _get_current_price(self, asset: str) -> Optional[float]:
        """获取当前价格"""
        if self.price_feed:
            return self.price_feed.get_cached_price(asset)
        return None
    
    def _check_health(self, position, current_price: float) -> tuple:
        """
        检查仓位健康度
        
        Returns:
            (should_liquidate: bool, health_ratio: float)
        """
        # 计算未实现盈亏
        if position.side == "long":
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - current_price) / position.entry_price
        
        pnl = position.size_usdc * pnl_pct * position.leverage
        
        # 初始保证金
        initial_margin = position.size_usdc / position.leverage
        
        # 当前权益
        equity = initial_margin + pnl
        
        # 健康度 = 当前权益 / 初始保证金
        health = equity / initial_margin if initial_margin > 0 else 0
        
        # 如果健康度低于维持保证金率，触发清算
        should_liquidate = health < self.MAINTENANCE_MARGIN_RATE
        
        return should_liquidate, health
    
    async def _execute_liquidation(self, position, mark_price: float, health: float):
        """执行清算"""
        logger.warning(
            f"Liquidating position: {position.position_id} "
            f"(agent={position.agent_id}, health={health:.2%})"
        )
        
        # 计算盈亏
        if position.side == "long":
            pnl_pct = (mark_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - mark_price) / position.entry_price
        
        pnl = position.size_usdc * pnl_pct * position.leverage
        
        # 初始保证金
        initial_margin = position.size_usdc / position.leverage
        
        # 剩余保证金
        margin_remaining = max(0, initial_margin + pnl)
        
        # 清算费 0.5%
        liquidation_fee = position.size_usdc * self.LIQUIDATION_FEE_RATE
        
        # 创建清算记录
        record = LiquidationRecord(
            liquidation_id=f"liq_{uuid.uuid4().hex[:12]}",
            position_id=position.position_id,
            agent_id=position.agent_id,
            asset=position.asset,
            side=position.side,
            size_usdc=position.size_usdc,
            entry_price=position.entry_price,
            liquidation_price=position.liquidation_price,
            mark_price=mark_price,
            pnl=pnl,
            margin_remaining=margin_remaining,
            liquidation_fee=liquidation_fee,
        )
        
        try:
            # 关闭仓位
            if self.position_manager:
                self.position_manager.close_position(
                    position.position_id,
                    exit_price=mark_price,
                    reason="liquidation"
                )
            
            # 收取清算费
            if self.fee_service:
                from services.fee_service import FeeType
                self.fee_service.collect_fee(
                    agent_id=position.agent_id,
                    size_usdc=position.size_usdc,
                    fee_type=FeeType.LIQUIDATION,
                    position_id=position.position_id,
                )
            
            record.status = LiquidationStatus.EXECUTED
            record.executed_at = datetime.now()
            
            logger.info(
                f"Liquidation executed: {record.liquidation_id} "
                f"(fee=${liquidation_fee:.2f}, margin_left=${margin_remaining:.2f})"
            )
            
            # 触发回调
            if self._on_liquidation:
                await self._on_liquidation(record)
                
        except Exception as e:
            record.status = LiquidationStatus.FAILED
            record.error = str(e)
            logger.error(f"Liquidation failed: {e}")
        
        self.records[record.liquidation_id] = record
        return record
    
    def check_position_health(self, position, current_price: float = None) -> dict:
        """
        检查单个仓位健康度 (API 用)
        """
        if current_price is None:
            current_price = self._get_current_price(position.asset)
        
        if not current_price:
            return {"error": "Price not available"}
        
        should_liquidate, health = self._check_health(position, current_price)
        
        # 计算距离清算的价格
        if position.side == "long":
            distance_pct = (current_price - position.liquidation_price) / current_price
        else:
            distance_pct = (position.liquidation_price - current_price) / current_price
        
        return {
            "position_id": position.position_id,
            "health_ratio": round(health, 4),
            "health_status": "danger" if health < 0.1 else "warning" if health < 0.3 else "safe",
            "current_price": current_price,
            "liquidation_price": round(position.liquidation_price, 2),
            "distance_to_liquidation": f"{distance_pct:.2%}",
            "will_liquidate": should_liquidate,
        }
    
    def get_stats(self) -> dict:
        """获取清算统计"""
        total = len(self.records)
        executed = sum(1 for r in self.records.values() if r.status == LiquidationStatus.EXECUTED)
        failed = sum(1 for r in self.records.values() if r.status == LiquidationStatus.FAILED)
        
        total_fees = sum(
            r.liquidation_fee for r in self.records.values() 
            if r.status == LiquidationStatus.EXECUTED
        )
        
        return {
            "total_liquidations": total,
            "executed": executed,
            "failed": failed,
            "total_fees_collected": round(total_fees, 4),
            "fee_rate": f"{self.LIQUIDATION_FEE_RATE * 100:.1f}%",
            "maintenance_margin": f"{self.MAINTENANCE_MARGIN_RATE * 100:.0f}%",
        }
    
    def get_recent(self, limit: int = 20) -> List[dict]:
        """获取最近的清算记录"""
        records = sorted(
            self.records.values(),
            key=lambda r: r.created_at,
            reverse=True
        )[:limit]
        return [r.to_dict() for r in records]


# 全局实例
liquidation_engine = LiquidationEngine()
