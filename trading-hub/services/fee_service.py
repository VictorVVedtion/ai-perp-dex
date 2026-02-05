"""
Fee Service - 手续费服务

根据 PRD 定义的费率：
- Taker Fee: 0.05% (0.0005)
- Maker Fee: 0.02% (0.0002)
- Funding Rate: ±0.01% / 8h
- Liquidation Fee: 0.5% (0.005)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeeType(Enum):
    TAKER = "taker"
    MAKER = "maker"
    FUNDING = "funding"
    LIQUIDATION = "liquidation"


@dataclass
class FeeConfig:
    """费率配置"""
    taker_rate: float = 0.0005      # 0.05%
    maker_rate: float = 0.0002      # 0.02%
    funding_rate: float = 0.0001    # 0.01% per 8h
    liquidation_rate: float = 0.005  # 0.5%
    
    # 收费地址 (协议收入)
    treasury_agent_id: str = "protocol_treasury"


@dataclass
class FeeRecord:
    """手续费记录"""
    fee_id: str
    fee_type: FeeType
    agent_id: str
    amount_usdc: float
    trade_size: float
    rate_applied: float
    match_id: Optional[str] = None
    position_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "fee_id": self.fee_id,
            "type": self.fee_type.value,
            "agent_id": self.agent_id,
            "amount_usdc": round(self.amount_usdc, 6),
            "trade_size": self.trade_size,
            "rate": self.rate_applied,
            "match_id": self.match_id,
            "created_at": self.created_at.isoformat(),
        }


class FeeService:
    """手续费服务"""
    
    def __init__(self, config: Optional[FeeConfig] = None):
        self.config = config or FeeConfig()
        self.fee_records: Dict[str, FeeRecord] = {}
        self.total_collected: float = 0.0
        self.treasury_balance: float = 0.0
    
    def calculate_fee(
        self, 
        size_usdc: float, 
        fee_type: FeeType,
    ) -> float:
        """计算手续费"""
        if fee_type == FeeType.TAKER:
            return size_usdc * self.config.taker_rate
        elif fee_type == FeeType.MAKER:
            return size_usdc * self.config.maker_rate
        elif fee_type == FeeType.LIQUIDATION:
            return size_usdc * self.config.liquidation_rate
        elif fee_type == FeeType.FUNDING:
            return size_usdc * self.config.funding_rate
        return 0.0
    
    def collect_fee(
        self,
        agent_id: str,
        size_usdc: float,
        fee_type: FeeType,
        match_id: Optional[str] = None,
        position_id: Optional[str] = None,
    ) -> FeeRecord:
        """
        收取手续费
        
        返回手续费记录，调用方负责从 Agent 余额扣除
        """
        import uuid
        
        if fee_type == FeeType.TAKER:
            rate = self.config.taker_rate
        elif fee_type == FeeType.MAKER:
            rate = self.config.maker_rate
        elif fee_type == FeeType.LIQUIDATION:
            rate = self.config.liquidation_rate
        else:
            rate = self.config.funding_rate
        
        fee_amount = size_usdc * rate
        
        record = FeeRecord(
            fee_id=f"fee_{uuid.uuid4().hex[:12]}",
            fee_type=fee_type,
            agent_id=agent_id,
            amount_usdc=fee_amount,
            trade_size=size_usdc,
            rate_applied=rate,
            match_id=match_id,
            position_id=position_id,
        )
        
        self.fee_records[record.fee_id] = record
        self.total_collected += fee_amount
        self.treasury_balance += fee_amount
        
        logger.info(
            f"Fee collected: {fee_type.value} ${fee_amount:.4f} from {agent_id} "
            f"(size=${size_usdc}, rate={rate*100:.3f}%)"
        )
        
        return record
    
    def get_stats(self) -> dict:
        """获取费用统计"""
        by_type = {}
        for record in self.fee_records.values():
            t = record.fee_type.value
            if t not in by_type:
                by_type[t] = {"count": 0, "total": 0.0}
            by_type[t]["count"] += 1
            by_type[t]["total"] += record.amount_usdc
        
        return {
            "total_collected": round(self.total_collected, 4),
            "treasury_balance": round(self.treasury_balance, 4),
            "by_type": by_type,
            "config": {
                "taker_rate": f"{self.config.taker_rate * 100:.3f}%",
                "maker_rate": f"{self.config.maker_rate * 100:.3f}%",
                "liquidation_rate": f"{self.config.liquidation_rate * 100:.2f}%",
            }
        }
    
    def get_agent_fees(self, agent_id: str) -> List[FeeRecord]:
        """获取 Agent 的费用记录"""
        return [
            r for r in self.fee_records.values() 
            if r.agent_id == agent_id
        ]


# 全局实例
fee_service = FeeService()
