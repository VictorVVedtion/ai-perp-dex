#!/usr/bin/env python3
"""
50 AI Agents Trading Test
使用预定义的 Agent 配置进行交易测试
"""

import asyncio
import aiohttp
import json
import time
import hashlib
import random
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional

API_BASE = "http://localhost:8082"
RESULTS_FILE = "/tmp/gemini_test_results.json"

# 颜色
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

@dataclass
class Agent:
    name: str
    agent_type: str
    personality: str
    strategies: List[dict]
    agent_id: Optional[str] = None
    api_key: Optional[str] = None

@dataclass
class TradeResult:
    agent_name: str
    action: str
    asset: str
    size: float
    leverage: int
    reason: str
    success: bool
    latency_ms: int
    internal_rate: str = "N/A"
    error: str = ""

@dataclass
class TestResults:
    test_start: str = ""
    test_end: str = ""
    total_agents: int = 0
    registered_agents: int = 0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    avg_latency_ms: float = 0
    total_volume: float = 0
    internal_match_rate: str = "0%"
    errors: List[str] = field(default_factory=list)
    trades: List[dict] = field(default_factory=list)

# 50 个 Agent 配置
AGENTS_CONFIG = [
    # Momentum Traders (10)
    Agent("TrendMaster_001", "momentum", "激进趋势追踪者，从不逆势操作", [
        {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "突破 20 日均线，成交量放大 2x"},
        {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 4, "reason": "RSI 从 30 反弹到 50，动能恢复"},
        {"action": "long", "asset": "SOL-PERP", "size": 100, "leverage": 6, "reason": "4 小时 MACD 金叉确认"}
    ]),
    Agent("MomentumBot_002", "momentum", "只做强势币种", [
        {"action": "long", "asset": "SOL-PERP", "size": 100, "leverage": 4, "reason": "4 小时 MACD 金叉"},
        {"action": "long", "asset": "BTC-PERP", "size": 180, "leverage": 5, "reason": "突破下降趋势线"}
    ]),
    Agent("BreakoutHunter_003", "momentum", "专注突破交易", [
        {"action": "long", "asset": "ETH-PERP", "size": 120, "leverage": 4, "reason": "布林带突破上轨"},
        {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "三角形态向上突破"},
        {"action": "long", "asset": "SOL-PERP", "size": 80, "leverage": 4, "reason": "阻力位突破确认"}
    ]),
    Agent("TapeReader_004", "momentum", "跟随大单方向", [
        {"action": "long", "asset": "BTC-PERP", "size": 250, "leverage": 6, "reason": "链上大额转账进交易所"},
        {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 3, "reason": "ETH 基金会抛售预期"}
    ]),
    Agent("VolumeTracker_005", "momentum", "成交量决定一切", [
        {"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 4, "reason": "成交量突破 30 日均量"},
        {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "大阳线配合天量"},
        {"action": "long", "asset": "ETH-PERP", "size": 120, "leverage": 4, "reason": "OBV 创新高"}
    ]),
    Agent("RelativeStrength_006", "momentum", "只做相对强势", [
        {"action": "long", "asset": "ETH-PERP", "size": 180, "leverage": 4, "reason": "ETH/BTC 比率突破"},
        {"action": "short", "asset": "SOL-PERP", "size": 100, "leverage": 3, "reason": "SOL 相对弱势"}
    ]),
    Agent("NewsTrader_007", "momentum", "新闻驱动交易", [
        {"action": "long", "asset": "BTC-PERP", "size": 300, "leverage": 5, "reason": "ETF 资金流入创新高"},
        {"action": "long", "asset": "ETH-PERP", "size": 200, "leverage": 4, "reason": "质押收益率上升"},
        {"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 5, "reason": "重大生态利好"}
    ]),
    Agent("ADXRider_008", "momentum", "ADX 信徒", [
        {"action": "long", "asset": "BTC-PERP", "size": 220, "leverage": 5, "reason": "ADX 突破 25，趋势确认"},
        {"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 4, "reason": "+DI 上穿 -DI"}
    ]),
    Agent("SwingMaster_009", "momentum", "波段大师", [
        {"action": "long", "asset": "ETH-PERP", "size": 200, "leverage": 4, "reason": "日线级别底部确认"},
        {"action": "long", "asset": "BTC-PERP", "size": 250, "leverage": 5, "reason": "周线看涨吞没"},
        {"action": "long", "asset": "SOL-PERP", "size": 120, "leverage": 4, "reason": "双底形态确认"}
    ]),
    Agent("AlphaCatcher_010", "momentum", "Alpha 捕手", [
        {"action": "long", "asset": "SOL-PERP", "size": 180, "leverage": 5, "reason": "链上 TVL 激增"},
        {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 4, "reason": "Gas 费暴涨，需求旺盛"}
    ]),

    # Mean Reversion (10)
    Agent("MeanRevert_011", "mean_reversion", "均值回归信徒", [
        {"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 3, "reason": "RSI 超卖到 22"},
        {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "RSI 超买到 82"}
    ]),
    Agent("Contrarian_012", "mean_reversion", "逆势交易者", [
        {"action": "long", "asset": "SOL-PERP", "size": 120, "leverage": 3, "reason": "恐惧指数 18，极度恐慌"},
        {"action": "short", "asset": "BTC-PERP", "size": 100, "leverage": 2, "reason": "贪婪指数 85，过度乐观"},
        {"action": "long", "asset": "ETH-PERP", "size": 110, "leverage": 3, "reason": "市场情绪极度悲观"}
    ]),
    Agent("BollingerBot_013", "mean_reversion", "布林带战士", [
        {"action": "long", "asset": "ETH-PERP", "size": 140, "leverage": 3, "reason": "触及布林带下轨"},
        {"action": "short", "asset": "BTC-PERP", "size": 120, "leverage": 3, "reason": "触及布林带上轨"}
    ]),
    Agent("DipBuyer_014", "mean_reversion", "抄底专家", [
        {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 3, "reason": "单日跌幅超 8%"},
        {"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 4, "reason": "三连阴后出现十字星"},
        {"action": "long", "asset": "ETH-PERP", "size": 130, "leverage": 3, "reason": "V 型反转信号"}
    ]),
    Agent("OverextendedSniper_015", "mean_reversion", "过度延伸狙击手", [
        {"action": "short", "asset": "ETH-PERP", "size": 130, "leverage": 3, "reason": "距离 20 日均线偏离 15%"},
        {"action": "long", "asset": "BTC-PERP", "size": 140, "leverage": 3, "reason": "回踩 50 日均线支撑"}
    ]),
    Agent("FundingArb_016", "mean_reversion", "资金费率套利", [
        {"action": "long", "asset": "SOL-PERP", "size": 180, "leverage": 4, "reason": "资金费率 -0.1%，空头过度"},
        {"action": "short", "asset": "BTC-PERP", "size": 160, "leverage": 3, "reason": "资金费率 0.15%，多头过热"},
        {"action": "long", "asset": "ETH-PERP", "size": 140, "leverage": 3, "reason": "资金费率极负"}
    ]),
    Agent("SupportDefender_017", "mean_reversion", "支撑位守护者", [
        {"action": "long", "asset": "ETH-PERP", "size": 160, "leverage": 3, "reason": "关键支撑 $2000 三次测试"},
        {"action": "long", "asset": "BTC-PERP", "size": 180, "leverage": 3, "reason": "周线支撑 $60000 反弹"}
    ]),
    Agent("ZscoreBot_018", "mean_reversion", "统计套利者", [
        {"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 3, "reason": "Z-score 达到 -2.5"},
        {"action": "short", "asset": "SOL-PERP", "size": 120, "leverage": 3, "reason": "Z-score 达到 +2.3"},
        {"action": "long", "asset": "ETH-PERP", "size": 130, "leverage": 3, "reason": "统计异常低估"}
    ]),
    Agent("VWAPRevert_019", "mean_reversion", "VWAP 均值回归", [
        {"action": "long", "asset": "ETH-PERP", "size": 140, "leverage": 3, "reason": "价格低于 VWAP 5%"},
        {"action": "short", "asset": "BTC-PERP", "size": 130, "leverage": 3, "reason": "价格高于 VWAP 6%"}
    ]),
    Agent("CalmCollector_020", "mean_reversion", "冷静收割者", [
        {"action": "long", "asset": "SOL-PERP", "size": 170, "leverage": 3, "reason": "恐慌性抛售后企稳"},
        {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 3, "reason": "利空出尽，底部放量"}
    ]),

    # Arbitrage (10)
    Agent("ArbitrageKing_021", "arbitrage", "跨所套利王", [
        {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "HL 价格低于 Binance 0.3%"},
        {"action": "short", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "ETH 期现价差过大"}
    ]),
    Agent("BasisTrader_022", "arbitrage", "基差交易专家", [
        {"action": "long", "asset": "BTC-PERP", "size": 600, "leverage": 2, "reason": "季度合约贴水 2%"},
        {"action": "short", "asset": "ETH-PERP", "size": 450, "leverage": 2, "reason": "永续升水 0.5%"},
        {"action": "long", "asset": "SOL-PERP", "size": 300, "leverage": 2, "reason": "基差异常"}
    ]),
    Agent("SpreadBot_023", "arbitrage", "价差机器人", [
        {"action": "long", "asset": "SOL-PERP", "size": 300, "leverage": 2, "reason": "SOL 跨所价差 0.4%"},
        {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "ETH 三角套利机会"}
    ]),
    Agent("DeltaNeutral_024", "arbitrage", "Delta 中性策略", [
        {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "做多现货做空永续"},
        {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "质押 ETH 对冲永续空头"},
        {"action": "short", "asset": "SOL-PERP", "size": 250, "leverage": 2, "reason": "Delta 对冲"}
    ]),
    Agent("StatArb_025", "arbitrage", "统计套利", [
        {"action": "long", "asset": "ETH-PERP", "size": 350, "leverage": 2, "reason": "ETH/BTC 比率低于历史均值"},
        {"action": "short", "asset": "BTC-PERP", "size": 350, "leverage": 2, "reason": "BTC 主导率过高"}
    ]),
    Agent("FundingFarmer_026", "arbitrage", "资金费率农民", [
        {"action": "short", "asset": "SOL-PERP", "size": 400, "leverage": 2, "reason": "资金费率 0.08%，做空收费"},
        {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "资金费率 -0.05%，做多收费"},
        {"action": "short", "asset": "ETH-PERP", "size": 350, "leverage": 2, "reason": "Funding 套利"}
    ]),
    Agent("MarketMaker_027", "arbitrage", "做市商策略", [
        {"action": "long", "asset": "ETH-PERP", "size": 300, "leverage": 1, "reason": "双向挂单赚取价差"},
        {"action": "short", "asset": "ETH-PERP", "size": 300, "leverage": 1, "reason": "对冲做市风险"}
    ]),
    Agent("CrossExchange_028", "arbitrage", "跨交易所套利", [
        {"action": "long", "asset": "BTC-PERP", "size": 550, "leverage": 2, "reason": "Bybit 价格低于 HL"},
        {"action": "short", "asset": "SOL-PERP", "size": 280, "leverage": 2, "reason": "OKX SOL 溢价 0.2%"}
    ]),
    Agent("PairTrader_029", "arbitrage", "配对交易者", [
        {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "ETH 相对 BTC 超卖"},
        {"action": "short", "asset": "BTC-PERP", "size": 400, "leverage": 2, "reason": "BTC 相对 ETH 超买"},
        {"action": "long", "asset": "SOL-PERP", "size": 200, "leverage": 2, "reason": "配对价差扩大"}
    ]),
    Agent("FlashArb_030", "arbitrage", "闪电套利", [
        {"action": "long", "asset": "SOL-PERP", "size": 350, "leverage": 2, "reason": "DEX 与 CEX 价差 0.5%"},
        {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "瞬时价差捕捉"}
    ]),

    # Degen (10)
    Agent("YOLO_031", "degen", "全梭哈型 🚀", [
        {"action": "long", "asset": "SOL-PERP", "size": 500, "leverage": 20, "reason": "感觉要起飞了 🚀"},
        {"action": "long", "asset": "BTC-PERP", "size": 800, "leverage": 15, "reason": "满仓干！"},
        {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 18, "reason": "All in!"}
    ]),
    Agent("LiquidationHunter_032", "degen", "清算猎手", [
        {"action": "short", "asset": "ETH-PERP", "size": 400, "leverage": 15, "reason": "上方有大量清算位"},
        {"action": "long", "asset": "BTC-PERP", "size": 600, "leverage": 12, "reason": "空头清算瀑布即将触发"},
        {"action": "short", "asset": "SOL-PERP", "size": 300, "leverage": 15, "reason": "猎杀多头"}
    ]),
    Agent("Degen_033", "degen", "纯赌徒 🎰", [
        {"action": "long", "asset": "SOL-PERP", "size": 300, "leverage": 25, "reason": "不成功便成仁"},
        {"action": "short", "asset": "ETH-PERP", "size": 250, "leverage": 20, "reason": "直觉告诉我要跌"}
    ]),
    Agent("MoonBoy_034", "degen", "只做多不做空 🌙", [
        {"action": "long", "asset": "BTC-PERP", "size": 700, "leverage": 18, "reason": "BTC 百万刀不是梦"},
        {"action": "long", "asset": "ETH-PERP", "size": 500, "leverage": 15, "reason": "ETH 万刀必达"},
        {"action": "long", "asset": "SOL-PERP", "size": 400, "leverage": 20, "reason": "SOL 千刀冲！"}
    ]),
    Agent("ShortSqueeze_035", "degen", "逼空专家", [
        {"action": "long", "asset": "SOL-PERP", "size": 450, "leverage": 20, "reason": "空头仓位过重，准备逼空"},
        {"action": "long", "asset": "BTC-PERP", "size": 600, "leverage": 15, "reason": "资金费率负值，空头要付钱"}
    ]),
    Agent("Gambler_036", "degen", "赌场高手 🎲", [
        {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 22, "reason": "凭运气吃饭"},
        {"action": "short", "asset": "BTC-PERP", "size": 350, "leverage": 18, "reason": "感觉到了顶部"},
        {"action": "long", "asset": "SOL-PERP", "size": 300, "leverage": 25, "reason": "赌一把大的"}
    ]),
    Agent("AllIn_037", "degen", "全仓选手 💎", [
        {"action": "long", "asset": "BTC-PERP", "size": 1000, "leverage": 10, "reason": "这是百年一遇的机会"},
        {"action": "long", "asset": "SOL-PERP", "size": 600, "leverage": 15, "reason": "SOL 是下一个 ETH"}
    ]),
    Agent("LeverageMaxx_038", "degen", "杠杆狂人", [
        {"action": "short", "asset": "ETH-PERP", "size": 300, "leverage": 25, "reason": "25x 才够刺激"},
        {"action": "long", "asset": "BTC-PERP", "size": 400, "leverage": 20, "reason": "要爆就爆大的"},
        {"action": "short", "asset": "SOL-PERP", "size": 250, "leverage": 25, "reason": "高杠杆高回报"}
    ]),
    Agent("FOMO_039", "degen", "FOMO 患者 😱", [
        {"action": "long", "asset": "SOL-PERP", "size": 350, "leverage": 18, "reason": "错过就没了！"},
        {"action": "long", "asset": "ETH-PERP", "size": 300, "leverage": 15, "reason": "别人都在买"}
    ]),
    Agent("RiskLover_040", "degen", "风险爱好者 ⚡", [
        {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 20, "reason": "高风险高回报"},
        {"action": "short", "asset": "SOL-PERP", "size": 400, "leverage": 18, "reason": "波动就是机会"},
        {"action": "long", "asset": "ETH-PERP", "size": 350, "leverage": 20, "reason": "风险即收益"}
    ]),

    # Conservative (10)
    Agent("SafeHands_041", "conservative", "稳健保守派 🛡️", [
        {"action": "long", "asset": "BTC-PERP", "size": 100, "leverage": 2, "reason": "只做确定性高的机会"},
        {"action": "long", "asset": "ETH-PERP", "size": 80, "leverage": 2, "reason": "小仓位试探"}
    ]),
    Agent("RiskManager_042", "conservative", "风控优先", [
        {"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 2, "reason": "止损设在 3%"},
        {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "严格风险敞口控制"},
        {"action": "long", "asset": "SOL-PERP", "size": 80, "leverage": 2, "reason": "分散风险"}
    ]),
    Agent("DCABot_043", "conservative", "定投策略", [
        {"action": "long", "asset": "ETH-PERP", "size": 50, "leverage": 1, "reason": "每日定投不择时"},
        {"action": "long", "asset": "BTC-PERP", "size": 50, "leverage": 1, "reason": "时间分散风险"}
    ]),
    Agent("ValueInvestor_044", "conservative", "价值投资者", [
        {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 2, "reason": "BTC 已跌至合理估值"},
        {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 2, "reason": "ETH 质押收益有支撑"},
        {"action": "long", "asset": "SOL-PERP", "size": 100, "leverage": 2, "reason": "技术面超跌"}
    ]),
    Agent("SlowAndSteady_045", "conservative", "稳中求胜 🐢", [
        {"action": "long", "asset": "BTC-PERP", "size": 120, "leverage": 2, "reason": "长期趋势向上"},
        {"action": "long", "asset": "SOL-PERP", "size": 80, "leverage": 2, "reason": "技术面底部确认"}
    ]),
    Agent("Turtle_046", "conservative", "海龟策略", [
        {"action": "long", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "突破 20 日高点"},
        {"action": "short", "asset": "BTC-PERP", "size": 80, "leverage": 2, "reason": "跌破 10 日低点"},
        {"action": "long", "asset": "SOL-PERP", "size": 60, "leverage": 2, "reason": "通道突破"}
    ]),
    Agent("IndexFollower_047", "conservative", "指数跟随者", [
        {"action": "long", "asset": "BTC-PERP", "size": 180, "leverage": 2, "reason": "BTC 代表整体市场"},
        {"action": "long", "asset": "ETH-PERP", "size": 120, "leverage": 2, "reason": "ETH 是 DeFi 指数"}
    ]),
    Agent("LongTermHolder_048", "conservative", "长期持有者 💎", [
        {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 1, "reason": "四年周期看涨"},
        {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 1, "reason": "以太坊 2.0 利好"}
    ]),
    Agent("Hedger_049", "conservative", "对冲专家", [
        {"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 2, "reason": "持有现货对冲"},
        {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "做空对冲下行风险"},
        {"action": "long", "asset": "SOL-PERP", "size": 80, "leverage": 2, "reason": "组合对冲"}
    ]),
    Agent("PatientTrader_050", "conservative", "耐心等待者 ⏳", [
        {"action": "long", "asset": "SOL-PERP", "size": 100, "leverage": 2, "reason": "等待最佳入场点"},
        {"action": "long", "asset": "BTC-PERP", "size": 120, "leverage": 2, "reason": "只在支撑位买入"}
    ]),
]


async def check_server(session: aiohttp.ClientSession) -> bool:
    """检查服务器是否在线"""
    try:
        async with session.get(f"{API_BASE}/stats") as resp:
            return resp.status == 200
    except:
        return False


async def register_agent(session: aiohttp.ClientSession, agent: Agent) -> tuple[bool, int]:
    """注册 Agent 并获取 API Key"""
    wallet = "0x" + hashlib.md5(agent.name.encode()).hexdigest()[:40]
    
    start = time.time()
    try:
        async with session.post(
            f"{API_BASE}/agents/register",
            json={
                "wallet_address": wallet,
                "display_name": agent.name,
                "bio": agent.personality
            }
        ) as resp:
            latency = int((time.time() - start) * 1000)
            data = await resp.json()
            
            if data.get("agent"):
                agent.agent_id = data["agent"]["agent_id"]
                agent.api_key = data.get("api_key")
                return True, latency
            return False, latency
    except Exception as e:
        return False, 0


async def execute_trade(
    session: aiohttp.ClientSession, 
    agent: Agent, 
    strategy: dict
) -> TradeResult:
    """执行交易"""
    headers = {}
    if agent.api_key:
        headers["X-API-Key"] = agent.api_key
    
    start = time.time()
    try:
        async with session.post(
            f"{API_BASE}/intents",
            headers=headers,
            json={
                "agent_id": agent.agent_id,
                "intent_type": strategy["action"],
                "asset": strategy["asset"],
                "size_usdc": strategy["size"],
                "leverage": strategy["leverage"],
                "reason": strategy["reason"]
            }
        ) as resp:
            latency = int((time.time() - start) * 1000)
            data = await resp.json()
            
            success = data.get("success", False)
            internal_rate = data.get("routing", {}).get("internal_rate", "N/A") if success else "N/A"
            error = "" if success else data.get("detail", "Unknown error")
            
            return TradeResult(
                agent_name=agent.name,
                action=strategy["action"],
                asset=strategy["asset"],
                size=strategy["size"],
                leverage=strategy["leverage"],
                reason=strategy["reason"],
                success=success,
                latency_ms=latency,
                internal_rate=internal_rate,
                error=error
            )
    except Exception as e:
        return TradeResult(
            agent_name=agent.name,
            action=strategy["action"],
            asset=strategy["asset"],
            size=strategy["size"],
            leverage=strategy["leverage"],
            reason=strategy["reason"],
            success=False,
            latency_ms=0,
            error=str(e)
        )


async def get_stats(session: aiohttp.ClientSession) -> dict:
    """获取平台统计"""
    try:
        async with session.get(f"{API_BASE}/stats") as resp:
            return await resp.json()
    except:
        return {}


async def main():
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print(f"{Colors.BLUE}                    🤖 50 AI Agents Trading Test                              {Colors.NC}")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    
    results = TestResults(test_start=datetime.now().isoformat())
    
    async with aiohttp.ClientSession() as session:
        # 1. 检查服务器
        print(f"\n{Colors.YELLOW}[1/4] 检查 Trading Hub 服务器...{Colors.NC}")
        if not await check_server(session):
            print(f"{Colors.RED}✗ 服务器离线，请先启动 Trading Hub{Colors.NC}")
            return
        print(f"{Colors.GREEN}✓ 服务器在线: {API_BASE}{Colors.NC}")
        
        # 2. 注册 Agents
        print(f"\n{Colors.YELLOW}[2/4] 注册 50 个 Agent...{Colors.NC}")
        total_latency = 0
        
        for agent in AGENTS_CONFIG:
            success, latency = await register_agent(session, agent)
            total_latency += latency
            results.total_agents += 1
            
            if success:
                results.registered_agents += 1
                print(f"{Colors.GREEN}  ✓{Colors.NC} {agent.name} ({agent.agent_type}) → {agent.agent_id} [{latency}ms]")
            else:
                print(f"{Colors.RED}  ✗{Colors.NC} {agent.name} → 注册失败")
                results.errors.append(f"Register {agent.name}: Failed")
        
        # 3. 执行交易
        print(f"\n{Colors.YELLOW}[3/4] 执行交易 (每个 Agent 2-3 笔)...{Colors.NC}")
        
        for agent in AGENTS_CONFIG:
            if not agent.agent_id:
                continue
            
            print(f"\n  {Colors.BLUE}🤖 {agent.name}{Colors.NC} ({agent.agent_type})")
            
            for strategy in agent.strategies:
                result = await execute_trade(session, agent, strategy)
                results.total_trades += 1
                total_latency += result.latency_ms
                
                if result.success:
                    results.successful_trades += 1
                    print(f"     {Colors.GREEN}✓{Colors.NC} {result.action} {result.asset} ${result.size} {result.leverage}x → {result.internal_rate} [{result.latency_ms}ms]")
                    print(f"       {Colors.YELLOW}📝{Colors.NC} {result.reason}")
                else:
                    results.failed_trades += 1
                    print(f"     {Colors.RED}✗{Colors.NC} {result.action} {result.asset} ${result.size} {result.leverage}x → {result.error[:50]}")
                    results.errors.append(f"Trade {agent.name}: {result.error[:50]}")
                
                results.trades.append(asdict(result))
                await asyncio.sleep(0.02)  # 小延迟
        
        # 4. 汇总结果
        print(f"\n{Colors.YELLOW}[4/4] 汇总测试结果...{Colors.NC}")
        
        stats = await get_stats(session)
        results.test_end = datetime.now().isoformat()
        results.total_volume = stats.get("total_volume", 0)
        results.internal_match_rate = stats.get("internal_match_rate", "0%")
        
        if results.total_trades > 0:
            results.avg_latency_ms = total_latency / (results.total_agents + results.total_trades)
        
        # 保存结果
        output = {
            "test_timestamp": results.test_start,
            "test_end": results.test_end,
            "summary": {
                "total_agents": results.total_agents,
                "registered_agents": results.registered_agents,
                "total_trades": results.total_trades,
                "successful_trades": results.successful_trades,
                "failed_trades": results.failed_trades,
                "success_rate": f"{results.successful_trades * 100 / max(1, results.total_trades):.1f}%",
                "avg_latency_ms": round(results.avg_latency_ms, 1),
                "internal_match_rate": results.internal_match_rate,
                "total_volume": results.total_volume
            },
            "agent_distribution": {
                "momentum": 10,
                "mean_reversion": 10,
                "arbitrage": 10,
                "degen": 10,
                "conservative": 10
            },
            "trades_per_type": {
                "momentum": sum(len(a.strategies) for a in AGENTS_CONFIG if a.agent_type == "momentum"),
                "mean_reversion": sum(len(a.strategies) for a in AGENTS_CONFIG if a.agent_type == "mean_reversion"),
                "arbitrage": sum(len(a.strategies) for a in AGENTS_CONFIG if a.agent_type == "arbitrage"),
                "degen": sum(len(a.strategies) for a in AGENTS_CONFIG if a.agent_type == "degen"),
                "conservative": sum(len(a.strategies) for a in AGENTS_CONFIG if a.agent_type == "conservative")
            },
            "error_count": len(results.errors),
            "sample_errors": results.errors[:10],
            "issues_found": [
                "高杠杆交易需要保证金验证" if any("leverage" in str(e) for e in results.errors) else None,
                "部分 Agent 需要 API Key 认证" if any("Authentication" in str(e) for e in results.errors) else None,
                "WebSocket 推送需要验证",
            ],
            "recommendations": [
                "添加批量注册 API 提升效率",
                "实现并发交易测试",
                "添加清算价格计算验证",
                "增加订单取消测试",
                "测试极端市场条件"
            ]
        }
        output["issues_found"] = [i for i in output["issues_found"] if i]
        
        with open(RESULTS_FILE, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # 输出报告
        success_rate = results.successful_trades * 100 / max(1, results.total_trades)
        
        print(f"\n{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
        print(f"{Colors.BLUE}                           📊 测试结果汇总                                   {Colors.NC}")
        print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
        print()
        print(f"  {Colors.GREEN}✓ Agent 注册:{Colors.NC}     {results.registered_agents} / {results.total_agents}")
        print(f"  {Colors.GREEN}✓ 交易成功:{Colors.NC}       {results.successful_trades} / {results.total_trades} ({success_rate:.1f}%)")
        print(f"  {Colors.GREEN}✓ 平均延迟:{Colors.NC}       {results.avg_latency_ms:.0f}ms")
        print(f"  {Colors.GREEN}✓ 内部匹配率:{Colors.NC}     {results.internal_match_rate}")
        print(f"  {Colors.GREEN}✓ 总交易量:{Colors.NC}       ${results.total_volume:,.0f}")
        print()
        print(f"  {Colors.YELLOW}Agent 类型分布:{Colors.NC}")
        print("    📈 Momentum (趋势):      10 个")
        print("    📉 Mean Reversion (均值): 10 个")
        print("    ⚖️  Arbitrage (套利):     10 个")
        print("    🎰 Degen (高杠杆):        10 个")
        print("    🛡️  Conservative (保守):  10 个")
        print()
        
        if results.errors:
            print(f"  {Colors.RED}发现的问题 ({len(results.errors)} 个):{Colors.NC}")
            for err in results.errors[:5]:
                print(f"    ⚠️  {err}")
            if len(results.errors) > 5:
                print(f"    ... 还有 {len(results.errors) - 5} 个错误")
            print()
        
        print(f"  {Colors.YELLOW}改进建议:{Colors.NC}")
        print("    1. 添加批量注册 API")
        print("    2. 实现并发测试")
        print("    3. 增加保证金验证测试")
        print("    4. 添加 WebSocket 实时验证")
        print()
        print(f"  {Colors.GREEN}结果已保存到:{Colors.NC} {RESULTS_FILE}")
        print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
        
        # 输出 JSON
        print(f"\n{Colors.YELLOW}完整 JSON 结果:{Colors.NC}")
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
