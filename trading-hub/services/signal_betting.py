"""
Signal Betting Service - Agent 之间的预测对赌

核心概念:
- Agent A 发布 Signal: "ETH 24h 后 > $2200" + stake $50
- Agent B fade: "我不同意" + stake $50  
- Oracle 结算: 赢家拿走 $100 (扣少量协议费)

100% 内部匹配，零外部费用！
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List
import uuid
import time


class SignalType(Enum):
    PRICE_ABOVE = "price_above"      # 价格高于 X
    PRICE_BELOW = "price_below"      # 价格低于 X
    PRICE_CHANGE = "price_change"    # 涨跌幅


class SignalStatus(Enum):
    OPEN = "open"           # 等待对手
    MATCHED = "matched"     # 已匹配，等待结算
    SETTLED = "settled"     # 已结算
    EXPIRED = "expired"     # 过期未匹配
    CANCELLED = "cancelled" # 取消


@dataclass
class Signal:
    """预测信号"""
    signal_id: str
    creator_id: str
    asset: str
    signal_type: SignalType
    target_value: float         # 目标价格或涨跌幅
    stake_amount: float         # 押注金额 (USDC)
    expires_at: datetime        # 预测到期时间
    created_at: datetime = field(default_factory=datetime.now)
    created_price: float = 0.0  # 创建时的价格 (用于计算涨跌幅)
    status: SignalStatus = SignalStatus.OPEN
    
    # 匹配信息
    fader_id: Optional[str] = None
    matched_at: Optional[datetime] = None
    
    # 结算信息
    settled_at: Optional[datetime] = None
    settlement_price: Optional[float] = None
    winner_id: Optional[str] = None
    payout: Optional[float] = None


@dataclass  
class Bet:
    """对赌记录"""
    bet_id: str
    signal_id: str
    creator_id: str
    fader_id: str
    asset: str
    signal_type: SignalType
    target_value: float
    stake_per_side: float
    total_pot: float
    expires_at: datetime
    created_at: datetime
    status: str = "pending"
    
    # 结算
    settlement_price: Optional[float] = None
    winner_id: Optional[str] = None
    settled_at: Optional[datetime] = None


class SignalBettingService:
    """
    Signal 对赌服务
    
    流程:
    1. Agent 创建 Signal (预测 + 押注)
    2. 另一个 Agent fade (对赌)
    3. 到期后 Oracle 结算
    4. 赢家获得全部押注 (扣协议费)
    """
    
    PROTOCOL_FEE_RATE = 0.01  # 1% 协议费
    MIN_STAKE = 1.0           # 最小押注 $1
    MAX_STAKE = 1000.0        # 最大押注 $1000
    
    def __init__(self, price_feed=None):
        self.signals: Dict[str, Signal] = {}
        self.bets: Dict[str, Bet] = {}
        self.price_feed = price_feed
        
        # 统计
        self.stats = {
            "total_signals": 0,
            "total_bets": 0,
            "total_volume": 0.0,
            "protocol_fees": 0.0,
        }
    
    def create_signal(
        self,
        creator_id: str,
        asset: str,
        signal_type: SignalType,
        target_value: float,
        stake_amount: float,
        duration_hours: int = 24,
        current_price: float = 0.0,  # 当前价格 (用于 PRICE_CHANGE 类型)
    ) -> Signal:
        """
        创建预测信号
        
        示例:
        - "ETH 24h 后 > $2200" (PRICE_ABOVE)
        - "BTC 24h 后 < $70000" (PRICE_BELOW)
        - "SOL 24h 涨幅 > 5%" (PRICE_CHANGE, 需要传入 current_price)
        """
        if stake_amount < self.MIN_STAKE:
            raise ValueError(f"Minimum stake is ${self.MIN_STAKE}")
        if stake_amount > self.MAX_STAKE:
            raise ValueError(f"Maximum stake is ${self.MAX_STAKE}")
        
        signal_id = f"sig_{uuid.uuid4().hex[:12]}"
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        signal = Signal(
            signal_id=signal_id,
            creator_id=creator_id,
            asset=asset,
            signal_type=signal_type,
            target_value=target_value,
            stake_amount=stake_amount,
            expires_at=expires_at,
            created_price=current_price,  # 记录创建时价格
        )
        
        self.signals[signal_id] = signal
        self.stats["total_signals"] += 1
        
        return signal
    
    def fade_signal(self, signal_id: str, fader_id: str) -> Bet:
        """
        Fade 一个 Signal (对赌)
        
        Fader 押注相同金额，认为 Signal 预测错误
        """
        signal = self.signals.get(signal_id)
        if not signal:
            raise ValueError(f"Signal {signal_id} not found")
        
        if signal.status != SignalStatus.OPEN:
            raise ValueError(f"Signal is {signal.status.value}, cannot fade")
        
        if signal.creator_id == fader_id:
            raise ValueError("Cannot fade your own signal")
        
        if datetime.now() > signal.expires_at:
            signal.status = SignalStatus.EXPIRED
            raise ValueError("Signal has expired")
        
        # 创建 Bet
        bet_id = f"bet_{uuid.uuid4().hex[:12]}"
        total_pot = signal.stake_amount * 2
        
        bet = Bet(
            bet_id=bet_id,
            signal_id=signal_id,
            creator_id=signal.creator_id,
            fader_id=fader_id,
            asset=signal.asset,
            signal_type=signal.signal_type,
            target_value=signal.target_value,
            stake_per_side=signal.stake_amount,
            total_pot=total_pot,
            expires_at=signal.expires_at,
            created_at=datetime.now(),
        )
        
        # 更新 Signal 状态
        signal.status = SignalStatus.MATCHED
        signal.fader_id = fader_id
        signal.matched_at = datetime.now()
        
        self.bets[bet_id] = bet
        self.stats["total_bets"] += 1
        self.stats["total_volume"] += total_pot
        
        return bet
    
    async def settle_bet(self, bet_id: str, settlement_price: float = None) -> Bet:
        """
        结算对赌
        
        需要 Oracle 价格
        """
        bet = self.bets.get(bet_id)
        if not bet:
            raise ValueError(f"Bet {bet_id} not found")
        
        if bet.status == "settled":
            raise ValueError("Bet already settled")
        
        # 获取结算价格
        if settlement_price is None:
            if self.price_feed:
                settlement_price = self.price_feed.get_price(bet.asset.replace("-PERP", ""))
            else:
                raise ValueError("No settlement price provided")
        
        # 判断赢家
        signal = self.signals.get(bet.signal_id)
        creator_wins = self._check_signal_outcome(signal, settlement_price)
        
        winner_id = bet.creator_id if creator_wins else bet.fader_id
        
        # 计算 payout (扣协议费)
        protocol_fee = bet.total_pot * self.PROTOCOL_FEE_RATE
        payout = bet.total_pot - protocol_fee
        
        # 更新
        bet.settlement_price = settlement_price
        bet.winner_id = winner_id
        bet.settled_at = datetime.now()
        bet.status = "settled"
        
        signal.status = SignalStatus.SETTLED
        signal.settlement_price = settlement_price
        signal.winner_id = winner_id
        signal.payout = payout
        signal.settled_at = datetime.now()
        
        self.stats["protocol_fees"] += protocol_fee
        
        return bet
    
    def _check_signal_outcome(self, signal: Signal, price: float) -> bool:
        """检查 Signal 预测是否正确"""
        if signal.signal_type == SignalType.PRICE_ABOVE:
            return price > signal.target_value
        elif signal.signal_type == SignalType.PRICE_BELOW:
            return price < signal.target_value
        elif signal.signal_type == SignalType.PRICE_CHANGE:
            # 计算涨跌幅
            if signal.created_price <= 0:
                return False
            change_pct = (price - signal.created_price) / signal.created_price * 100
            # target_value 是预测的涨跌幅百分比 (正数=涨，负数=跌)
            if signal.target_value > 0:
                return change_pct >= signal.target_value  # 预测涨，实际涨幅 >= 目标
            else:
                return change_pct <= signal.target_value  # 预测跌，实际跌幅 >= 目标
        return False
    
    def get_open_signals(self, asset: str = None) -> List[Signal]:
        """获取开放的 Signals"""
        signals = [s for s in self.signals.values() if s.status == SignalStatus.OPEN]
        if asset:
            signals = [s for s in signals if s.asset == asset]
        return signals
    
    def get_pending_bets(self) -> List[Bet]:
        """获取待结算的 Bets"""
        return [b for b in self.bets.values() if b.status == "pending"]
    
    def get_agent_stats(self, agent_id: str) -> dict:
        """获取 Agent 的对赌统计"""
        wins = 0
        losses = 0
        total_wagered = 0.0
        total_won = 0.0
        
        for bet in self.bets.values():
            if bet.status != "settled":
                continue
            
            if bet.creator_id == agent_id or bet.fader_id == agent_id:
                total_wagered += bet.stake_per_side
                
                if bet.winner_id == agent_id:
                    wins += 1
                    total_won += bet.total_pot * (1 - self.PROTOCOL_FEE_RATE)
                else:
                    losses += 1
        
        return {
            "wins": wins,
            "losses": losses,
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
            "total_wagered": total_wagered,
            "total_won": total_won,
            "net_pnl": total_won - total_wagered,
        }
    
    def get_stats(self) -> dict:
        """获取服务统计"""
        return {
            **self.stats,
            "open_signals": len([s for s in self.signals.values() if s.status == SignalStatus.OPEN]),
            "pending_bets": len([b for b in self.bets.values() if b.status == "pending"]),
            "internal_match_rate": "100%",  # Signal betting 永远是 100% 内部
        }


    async def auto_settle_expired(self) -> List[Bet]:
        """
        自动结算所有到期的 Bets
        
        应该由后台任务定期调用
        """
        now = datetime.now()
        settled = []
        
        for bet in list(self.bets.values()):
            if bet.status != "pending":
                continue
            
            if now >= bet.expires_at:
                try:
                    # 尝试获取价格并结算
                    settled_bet = await self.settle_bet(bet.bet_id)
                    settled.append(settled_bet)
                    print(f"✅ Auto-settled bet {bet.bet_id}: winner={settled_bet.winner_id}")
                except Exception as e:
                    print(f"⚠️ Failed to settle bet {bet.bet_id}: {e}")
        
        return settled
    
    async def _settlement_loop(self):
        """后台结算循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                settled = await self.auto_settle_expired()
                if settled:
                    print(f"🎯 Auto-settled {len(settled)} bets")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Settlement loop error: {e}")
    
    async def start_auto_settlement(self):
        """启动自动结算"""
        self._settlement_task = asyncio.create_task(self._settlement_loop())
        print("🎯 Signal Betting auto-settlement started")
    
    async def stop_auto_settlement(self):
        """停止自动结算"""
        if hasattr(self, '_settlement_task'):
            self._settlement_task.cancel()
            try:
                await self._settlement_task
            except asyncio.CancelledError:
                pass


# 单例
signal_betting = SignalBettingService()
