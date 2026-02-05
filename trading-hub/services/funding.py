"""
Funding Rate Settlement - 资金费率结算

永续合约的核心机制:
- 多头持仓 → 空头持仓 (当 funding rate > 0)
- 空头持仓 → 多头持仓 (当 funding rate < 0)
- 每 8 小时结算一次
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


@dataclass
class FundingRate:
    """资金费率"""
    asset: str
    rate: float  # 正数 = 多付空，负数 = 空付多
    timestamp: datetime
    next_settlement: datetime
    
    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "rate": self.rate,
            "rate_pct": f"{self.rate * 100:.4f}%",
            "timestamp": self.timestamp.isoformat(),
            "next_settlement": self.next_settlement.isoformat(),
        }


@dataclass
class FundingPayment:
    """资金费支付记录"""
    payment_id: str
    agent_id: str
    asset: str
    position_side: str  # "long" | "short"
    position_size: float
    funding_rate: float
    payment_amount: float  # 正 = 收到，负 = 支付
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "agent_id": self.agent_id,
            "asset": self.asset,
            "side": self.position_side,
            "size": self.position_size,
            "rate": f"{self.funding_rate * 100:.4f}%",
            "amount": round(self.payment_amount, 4),
            "timestamp": self.timestamp.isoformat(),
        }


class FundingSettlement:
    """
    资金费率结算服务
    
    核心逻辑:
    1. 计算资金费率 (基于 mark-index 价差)
    2. 每 8 小时结算
    3. 多头支付空头 (正费率) 或反之
    """
    
    # 配置
    SETTLEMENT_INTERVAL_HOURS = 8
    MAX_FUNDING_RATE = 0.01  # 最大 1%
    MIN_FUNDING_RATE = -0.01  # 最小 -1%
    
    def __init__(self, position_manager=None, settlement_engine=None):
        self.position_manager = position_manager
        self.settlement_engine = settlement_engine
        
        # 当前费率
        self.current_rates: Dict[str, FundingRate] = {}
        
        # 历史费率
        self.rate_history: Dict[str, List[FundingRate]] = {}
        
        # 支付记录
        self.payments: List[FundingPayment] = []
        
        # 后台任务
        self._running = False
        self._task = None
        
        # 下次结算时间
        self._next_settlement = self._calculate_next_settlement()
    
    def _calculate_next_settlement(self) -> datetime:
        """计算下次结算时间 (0:00, 8:00, 16:00 UTC)"""
        now = datetime.utcnow()
        hour = now.hour
        
        if hour < 8:
            next_hour = 8
        elif hour < 16:
            next_hour = 16
        else:
            next_hour = 24  # 下一天 0:00
        
        if next_hour == 24:
            return datetime(now.year, now.month, now.day) + timedelta(days=1)
        else:
            return datetime(now.year, now.month, now.day, next_hour)
    
    async def start(self):
        """启动结算服务"""
        self._running = True
        self._task = asyncio.create_task(self._settlement_loop())
        print(f"💸 Funding Settlement started (next: {self._next_settlement})")
    
    async def stop(self):
        """停止服务"""
        self._running = False
        if self._task:
            self._task.cancel()
    
    async def _settlement_loop(self):
        """结算循环"""
        while self._running:
            now = datetime.utcnow()
            
            if now >= self._next_settlement:
                await self._settle_all()
                self._next_settlement = self._calculate_next_settlement()
            
            # 每分钟检查一次
            await asyncio.sleep(60)
    
    def calculate_funding_rate(
        self,
        asset: str,
        mark_price: float,
        index_price: float,
        interest_rate: float = 0.0003,  # 0.03% 日利率
    ) -> float:
        """
        计算资金费率
        
        公式: Funding Rate = Premium Index + clamp(Interest Rate - Premium Index, -0.05%, 0.05%)
        简化版: Funding Rate = (Mark - Index) / Index
        """
        if index_price == 0:
            return 0
        
        premium = (mark_price - index_price) / index_price
        
        # 加上利率差
        rate = premium + interest_rate
        
        # 限制范围
        rate = max(self.MIN_FUNDING_RATE, min(self.MAX_FUNDING_RATE, rate))
        
        return rate
    
    def update_rate(self, asset: str, mark_price: float, index_price: float):
        """更新资金费率"""
        rate = self.calculate_funding_rate(asset, mark_price, index_price)
        
        funding_rate = FundingRate(
            asset=asset,
            rate=rate,
            timestamp=datetime.utcnow(),
            next_settlement=self._next_settlement,
        )
        
        self.current_rates[asset] = funding_rate
        
        # 保存历史
        if asset not in self.rate_history:
            self.rate_history[asset] = []
        self.rate_history[asset].append(funding_rate)
        
        # 只保留最近 100 条
        if len(self.rate_history[asset]) > 100:
            self.rate_history[asset] = self.rate_history[asset][-100:]
        
        return funding_rate
    
    async def _settle_all(self):
        """结算所有资产"""
        if not self.position_manager:
            return
        
        timestamp = datetime.utcnow()
        
        for asset, funding_rate in self.current_rates.items():
            await self._settle_asset(asset, funding_rate, timestamp)
    
    async def _settle_asset(self, asset: str, funding_rate: FundingRate, timestamp: datetime):
        """结算单个资产"""
        if not self.position_manager:
            return
        
        rate = funding_rate.rate
        if rate == 0:
            return
        
        # 获取所有该资产的持仓
        all_positions = list(self.position_manager.positions.values())
        asset_positions = [p for p in all_positions if p.asset == asset and p.is_open]
        
        # 分离多空
        longs = [p for p in asset_positions if p.side.value == "long"]
        shorts = [p for p in asset_positions if p.side.value == "short"]
        
        total_long_size = sum(p.size_usdc for p in longs)
        total_short_size = sum(p.size_usdc for p in shorts)
        
        if total_long_size == 0 or total_short_size == 0:
            return
        
        # 计算支付
        # 正费率: 多付空
        # 负费率: 空付多
        
        for pos in longs:
            payment = -pos.size_usdc * rate  # 负 = 支付
            if rate < 0:
                payment = -payment  # 负费率时多头收钱
            
            self._record_payment(pos, rate, payment, timestamp)
        
        for pos in shorts:
            payment = pos.size_usdc * rate  # 正 = 收到
            if rate < 0:
                payment = -payment  # 负费率时空头付钱
            
            self._record_payment(pos, rate, payment, timestamp)
    
    def _record_payment(self, position, rate: float, amount: float, timestamp: datetime):
        """记录支付"""
        import uuid
        
        payment = FundingPayment(
            payment_id=f"fund_{uuid.uuid4().hex[:12]}",
            agent_id=position.agent_id,
            asset=position.asset,
            position_side=position.side.value,
            position_size=position.size_usdc,
            funding_rate=rate,
            payment_amount=amount,
            timestamp=timestamp,
        )
        
        self.payments.append(payment)
        
        # 实际转账
        if self.settlement_engine and amount != 0:
            if amount > 0:
                # 收到资金 - 从协议账户转入
                self.settlement_engine.deposit(position.agent_id, amount)
            else:
                # 支付资金 - 扣除余额
                self.settlement_engine.withdraw(position.agent_id, -amount)
    
    def get_current_rate(self, asset: str) -> Optional[FundingRate]:
        """获取当前费率"""
        return self.current_rates.get(asset)
    
    def get_rate_history(self, asset: str, limit: int = 24) -> List[FundingRate]:
        """获取历史费率"""
        history = self.rate_history.get(asset, [])
        return history[-limit:]
    
    def get_payments(self, agent_id: str = None, limit: int = 50) -> List[FundingPayment]:
        """获取支付记录"""
        payments = self.payments
        if agent_id:
            payments = [p for p in payments if p.agent_id == agent_id]
        return payments[-limit:]
    
    def get_predicted_payment(self, agent_id: str) -> dict:
        """预测下次结算的支付"""
        if not self.position_manager:
            return {"total": 0, "positions": []}
        
        positions = self.position_manager.get_positions(agent_id)
        
        predictions = []
        total = 0
        
        for pos in positions:
            rate = self.current_rates.get(pos.asset)
            if not rate:
                continue
            
            if pos.side.value == "long":
                payment = -pos.size_usdc * rate.rate
            else:
                payment = pos.size_usdc * rate.rate
            
            if rate.rate < 0:
                payment = -payment
            
            predictions.append({
                "asset": pos.asset,
                "side": pos.side.value,
                "size": pos.size_usdc,
                "rate": rate.rate,
                "predicted_payment": round(payment, 4),
            })
            total += payment
        
        return {
            "agent_id": agent_id,
            "next_settlement": self._next_settlement.isoformat(),
            "total_predicted": round(total, 4),
            "positions": predictions,
        }


# 单例
funding_settlement = FundingSettlement()
