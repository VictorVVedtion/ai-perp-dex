"""
Backtester - 策略回测

让 Agent 在执行策略前先测试历史表现
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional
import random

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """回测交易"""
    timestamp: datetime
    side: str  # "long" | "short"
    entry_price: float
    exit_price: float
    size_usdc: float
    leverage: int
    pnl: float
    pnl_pct: float
    holding_period: timedelta


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    asset: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # 绩效指标
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    
    # 交易统计
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_holding_period: str
    
    # 详细交易
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[tuple] = field(default_factory=list)  # [(timestamp, equity), ...]
    
    def summary(self) -> str:
        """生成摘要"""
        return f"""
📊 回测结果: {self.strategy_name}
{'=' * 50}
资产: {self.asset}
期间: {self.start_date.date()} → {self.end_date.date()}

💰 收益
  初始资金: ${self.initial_capital:,.2f}
  最终资金: ${self.final_capital:,.2f}
  总收益: ${self.total_return:,.2f} ({self.total_return_pct:+.1f}%)
  最大回撤: {self.max_drawdown_pct:.1f}%

📈 绩效
  夏普比率: {self.sharpe_ratio:.2f}
  胜率: {self.win_rate:.1f}%
  盈亏比: {self.profit_factor:.2f}

🔄 交易
  总交易数: {self.total_trades}
  盈利交易: {self.winning_trades}
  亏损交易: {self.losing_trades}
  平均持仓: {self.avg_holding_period}
"""


class Backtester:
    """
    策略回测器
    
    用法:
        bt = Backtester()
        result = await bt.run(
            strategy=my_strategy,
            asset="ETH",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=1000,
        )
        print(result.summary())
    """
    
    def __init__(self):
        self.price_data: Dict[str, List[tuple]] = {}  # asset -> [(timestamp, price), ...]
    
    async def load_price_data(self, asset: str, start: datetime, end: datetime) -> List[tuple]:
        """
        加载历史价格数据
        
        TODO: 接入真实数据源 (如 CoinGecko, Binance)
        现在用模拟数据
        """
        if asset in self.price_data:
            return self.price_data[asset]
        
        # 模拟数据生成
        data = []
        current_date = start
        
        # 起始价格
        base_prices = {"BTC": 40000, "ETH": 2000, "SOL": 80}
        price = base_prices.get(asset.replace("-PERP", ""), 100)
        
        while current_date <= end:
            # 随机波动 (-3% ~ +3%)
            change = random.uniform(-0.03, 0.03)
            price = price * (1 + change)
            data.append((current_date, price))
            current_date += timedelta(hours=1)
        
        self.price_data[asset] = data
        return data
    
    async def run(
        self,
        strategy: Callable,
        asset: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 1000,
        leverage: int = 1,
    ) -> BacktestResult:
        """
        运行回测
        
        strategy: async def strategy(price, position, capital) -> "long" | "short" | "close" | None
        """
        # 加载数据
        prices = await self.load_price_data(asset, start_date, end_date)
        
        # 状态
        capital = initial_capital
        position = None  # {"side": "long", "entry_price": xxx, "size": xxx, "entry_time": xxx}
        trades: List[BacktestTrade] = []
        equity_curve = []
        peak_equity = initial_capital
        max_drawdown = 0
        
        # 遍历每个时间点
        for timestamp, price in prices:
            # 计算当前权益
            if position:
                if position["side"] == "long":
                    pnl_pct = (price - position["entry_price"]) / position["entry_price"]
                else:
                    pnl_pct = (position["entry_price"] - price) / position["entry_price"]
                
                unrealized_pnl = position["size"] * pnl_pct * leverage
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            equity_curve.append((timestamp, current_equity))
            
            # 更新最大回撤
            if current_equity > peak_equity:
                peak_equity = current_equity
            drawdown = (peak_equity - current_equity) / peak_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            
            # 获取策略信号
            try:
                signal = await strategy(price, position, capital)
            except Exception as e:
                logger.warning(f"Strategy signal error: {e}")
                signal = None
            
            # 执行交易
            if signal == "close" and position:
                # 平仓
                if position["side"] == "long":
                    pnl_pct = (price - position["entry_price"]) / position["entry_price"]
                else:
                    pnl_pct = (position["entry_price"] - price) / position["entry_price"]
                
                pnl = position["size"] * pnl_pct * leverage
                capital += pnl
                
                trades.append(BacktestTrade(
                    timestamp=timestamp,
                    side=position["side"],
                    entry_price=position["entry_price"],
                    exit_price=price,
                    size_usdc=position["size"],
                    leverage=leverage,
                    pnl=pnl,
                    pnl_pct=pnl_pct * leverage * 100,
                    holding_period=timestamp - position["entry_time"],
                ))
                
                position = None
            
            elif signal in ["long", "short"] and not position:
                # 开仓 (用 50% 资金)
                size = capital * 0.5
                position = {
                    "side": signal,
                    "entry_price": price,
                    "size": size,
                    "entry_time": timestamp,
                }
        
        # 计算统计
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        total_return = capital - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        profit_factor = abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades)) if losing_trades and sum(t.pnl for t in losing_trades) != 0 else 0
        
        # 简化的夏普比率
        if trades:
            returns = [t.pnl_pct for t in trades]
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 平均持仓时间
        if trades:
            avg_holding = sum((t.holding_period.total_seconds() for t in trades)) / len(trades)
            avg_holding_str = f"{avg_holding/3600:.1f}h"
        else:
            avg_holding_str = "N/A"
        
        return BacktestResult(
            strategy_name=strategy.__name__ if hasattr(strategy, '__name__') else "Custom",
            asset=asset,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            max_drawdown=max_drawdown * initial_capital,
            max_drawdown_pct=max_drawdown * 100,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=max((t.pnl for t in trades), default=0),
            largest_loss=min((t.pnl for t in trades), default=0),
            avg_holding_period=avg_holding_str,
            trades=trades,
            equity_curve=equity_curve,
        )


# 内置策略
async def strategy_momentum(price: float, position: dict, capital: float) -> Optional[str]:
    """
    动量策略 (示例)
    
    简单的均值回归
    """
    # 这里应该用历史数据计算 MA，简化版用随机
    if not position:
        if random.random() > 0.6:
            return "long"
        elif random.random() < 0.4:
            return "short"
    else:
        # 持仓超过 24 小时或盈利/亏损超过 5% 平仓
        if random.random() > 0.8:
            return "close"
    return None


async def strategy_grid(price: float, position: dict, capital: float) -> Optional[str]:
    """网格策略 (示例)"""
    if not position:
        if random.random() > 0.5:
            return "long" if random.random() > 0.5 else "short"
    else:
        if random.random() > 0.7:
            return "close"
    return None


# 单例
backtester = Backtester()
