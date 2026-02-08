"""
AI Native SDK - 为 Agent 设计的交易接口

特点:
1. 自动 Agent 管理 (无需手动注册)
2. 自然语言交易 ("long ETH $100 5x")
3. Webhook 回调 (匹配通知)
4. 策略模板 (一键启用)
"""

import re
import json
import asyncio
import aiohttp
import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    success: bool
    intent_id: Optional[str] = None
    internal_rate: Optional[str] = None
    fee_saved: float = 0.0
    message: str = ""
    raw: dict = None


class AINativeSDK:
    """
    AI Agent 专用 SDK
    
    用法:
        sdk = AINativeSDK("https://api.riverbit.ai")
        
        # 自然语言交易
        result = await sdk.trade("long ETH $100 5x leverage")
        
        # 或者简洁调用
        result = await sdk.long("ETH", 100)
        
        # 设置回调
        sdk.on_match(lambda match: print(f"Matched! {match}"))
    """
    
    def __init__(self, base_url: str = "https://api.riverbit.ai", agent_name: str = None):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.agent_id: Optional[str] = None
        self.agent_name = agent_name or f"Agent_{datetime.now().strftime('%H%M%S')}"
        
        # 回调
        self._on_match_callbacks: List[Callable] = []
        self._on_signal_callbacks: List[Callable] = []
        
        # WebSocket
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ws_task: Optional[asyncio.Task] = None
    
    async def _ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def _ensure_agent(self):
        """自动创建/获取 Agent (无需手动注册)"""
        if self.agent_id:
            return
        
        await self._ensure_session()
        
        # 尝试用名字查找已有 agent
        async with self.session.get(f"{self.base_url}/agents") as resp:
            if resp.status == 200:
                data = await resp.json()
                for agent in data.get("agents", []):
                    if agent.get("display_name") == self.agent_name:
                        self.agent_id = agent["agent_id"]
                        return
        
        # 自动注册新 agent
        wallet = f"0x{hash(self.agent_name) & 0xFFFFFFFFFFFFFFFF:016x}"
        async with self.session.post(
            f"{self.base_url}/agents/register",
            json={"wallet_address": wallet, "display_name": self.agent_name}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.agent_id = data["agent"]["agent_id"]
    
    # ==========================================
    # 自然语言交易
    # ==========================================
    
    async def trade(self, instruction: str) -> TradeResult:
        """
        自然语言交易
        
        支持格式:
        - "long ETH $100"
        - "short BTC 50 USDC 10x leverage"
        - "做多 ETH 100刀 5倍"
        - "开空 BTC $200"
        """
        parsed = self._parse_instruction(instruction)
        if not parsed:
            return TradeResult(success=False, message=f"Cannot parse: {instruction}")
        
        if parsed["direction"] == "long":
            return await self.long(parsed["asset"], parsed["size"], parsed.get("leverage", 1))
        else:
            return await self.short(parsed["asset"], parsed["size"], parsed.get("leverage", 1))
    
    def _parse_instruction(self, text: str) -> Optional[dict]:
        """解析自然语言指令"""
        text = text.lower().strip()
        
        # 方向
        direction = None
        if any(w in text for w in ["long", "做多", "开多", "buy", "买"]):
            direction = "long"
        elif any(w in text for w in ["short", "做空", "开空", "sell", "卖"]):
            direction = "short"
        
        if not direction:
            return None
        
        # 资产
        asset = None
        for a in ["btc", "eth", "sol"]:
            if a in text:
                asset = a.upper()
                break
        
        if not asset:
            return None
        
        # 金额
        size = None
        # 匹配 $100, 100 USDC, 100刀, 100u
        patterns = [
            r'\$(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:usdc|usd|刀|u|美元)',
            r'(\d+(?:\.\d+)?)\s*(?=.*(?:leverage|倍|x))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                size = float(match.group(1))
                break
        
        # 如果还没找到，找独立的数字
        if not size:
            numbers = re.findall(r'(\d+(?:\.\d+)?)', text)
            if numbers:
                size = float(numbers[0])
        
        if not size:
            size = 100  # 默认
        
        # 杠杆
        leverage = 1
        lev_match = re.search(r'(\d+)\s*(?:x|倍|leverage)', text)
        if lev_match:
            leverage = int(lev_match.group(1))
        
        return {
            "direction": direction,
            "asset": asset,
            "size": size,
            "leverage": min(leverage, 100),  # 最大 100x
        }
    
    # ==========================================
    # 简洁 API
    # ==========================================
    
    async def long(self, asset: str, size: float, leverage: int = 1) -> TradeResult:
        """做多"""
        return await self._create_intent("long", asset, size, leverage)
    
    async def short(self, asset: str, size: float, leverage: int = 1) -> TradeResult:
        """做空"""
        return await self._create_intent("short", asset, size, leverage)
    
    async def _create_intent(self, direction: str, asset: str, size: float, leverage: int) -> TradeResult:
        """创建 Intent"""
        await self._ensure_agent()
        await self._ensure_session()
        
        # 标准化 asset
        if not asset.endswith("-PERP"):
            asset = f"{asset.upper()}-PERP"
        
        async with self.session.post(
            f"{self.base_url}/intents",
            json={
                "agent_id": self.agent_id,
                "intent_type": direction,
                "asset": asset,
                "size_usdc": size,
                "leverage": leverage,
            }
        ) as resp:
            data = await resp.json()
            
            if data.get("success"):
                routing = data.get("routing", {})
                return TradeResult(
                    success=True,
                    intent_id=data.get("intent", {}).get("intent_id"),
                    internal_rate=routing.get("internal_rate"),
                    fee_saved=routing.get("fee_saved", 0),
                    message=f"✅ {direction.upper()} {asset} ${size} @ {leverage}x",
                    raw=data,
                )
            else:
                return TradeResult(
                    success=False,
                    message=data.get("detail", "Failed"),
                    raw=data,
                )
    
    # ==========================================
    # Signal Betting
    # ==========================================
    
    async def predict(self, instruction: str) -> TradeResult:
        """
        自然语言预测
        
        - "ETH will be above $2200 in 24h, stake $50"
        - "BTC 24小时后低于 $70000, 押注 $100"
        """
        parsed = self._parse_prediction(instruction)
        if not parsed:
            return TradeResult(success=False, message=f"Cannot parse prediction: {instruction}")
        
        return await self.create_signal(
            parsed["asset"],
            parsed["signal_type"],
            parsed["target"],
            parsed.get("stake", 50),
            parsed.get("duration", 24),
        )
    
    def _parse_prediction(self, text: str) -> Optional[dict]:
        """解析预测指令"""
        text = text.lower()
        
        # 资产
        asset = None
        for a in ["btc", "eth", "sol"]:
            if a in text:
                asset = f"{a.upper()}-PERP"
                break
        if not asset:
            return None
        
        # 方向
        signal_type = "price_above"
        if any(w in text for w in ["below", "低于", "under", "less"]):
            signal_type = "price_below"
        
        # 目标价格
        target = None
        match = re.search(r'\$(\d+(?:,\d+)*(?:\.\d+)?)', text)
        if match:
            target = float(match.group(1).replace(",", ""))
        if not target:
            return None
        
        # 押注金额
        stake = 50
        stake_match = re.search(r'(?:stake|押注|bet)\s*\$?(\d+)', text)
        if stake_match:
            stake = float(stake_match.group(1))
        
        # 时长
        duration = 24
        dur_match = re.search(r'(\d+)\s*(?:h|小时|hour)', text)
        if dur_match:
            duration = int(dur_match.group(1))
        
        return {
            "asset": asset,
            "signal_type": signal_type,
            "target": target,
            "stake": stake,
            "duration": duration,
        }
    
    async def create_signal(
        self,
        asset: str,
        signal_type: str,
        target: float,
        stake: float = 50,
        duration_hours: int = 24,
    ) -> TradeResult:
        """创建预测信号"""
        await self._ensure_agent()
        await self._ensure_session()
        
        if not asset.endswith("-PERP"):
            asset = f"{asset.upper()}-PERP"
        
        async with self.session.post(
            f"{self.base_url}/signals",
            json={
                "agent_id": self.agent_id,
                "asset": asset,
                "signal_type": signal_type,
                "target_value": target,
                "stake_amount": stake,
                "duration_hours": duration_hours,
            }
        ) as resp:
            data = await resp.json()
            
            if data.get("success"):
                return TradeResult(
                    success=True,
                    intent_id=data.get("signal", {}).get("signal_id"),
                    message=f"✅ Signal: {asset} {signal_type} ${target}, stake ${stake}",
                    raw=data,
                )
            else:
                return TradeResult(success=False, message=data.get("detail", "Failed"), raw=data)
    
    async def fade(self, signal_id: str) -> TradeResult:
        """Fade 一个 Signal"""
        await self._ensure_agent()
        await self._ensure_session()
        
        async with self.session.post(
            f"{self.base_url}/signals/fade",
            json={"signal_id": signal_id, "fader_id": self.agent_id}
        ) as resp:
            data = await resp.json()
            
            if data.get("success"):
                return TradeResult(
                    success=True,
                    message=f"✅ Faded! Pot: ${data.get('bet', {}).get('total_pot', 0)}",
                    raw=data,
                )
            else:
                return TradeResult(success=False, message=data.get("detail", "Failed"), raw=data)
    
    # ==========================================
    # Webhook / 回调
    # ==========================================
    
    def on_match(self, callback: Callable):
        """注册匹配回调"""
        self._on_match_callbacks.append(callback)
        return self
    
    def on_signal(self, callback: Callable):
        """注册 Signal 回调"""
        self._on_signal_callbacks.append(callback)
        return self
    
    async def start_listening(self):
        """启动 WebSocket 监听"""
        await self._ensure_session()
        
        ws_url = self.base_url.replace("http", "ws") + "/ws"
        self._ws = await self.session.ws_connect(ws_url)
        
        async def listen():
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_ws_message(data)
        
        self._ws_task = asyncio.create_task(listen())
    
    async def _handle_ws_message(self, data: dict):
        """处理 WebSocket 消息"""
        msg_type = data.get("type")
        
        if msg_type == "intent_matched":
            for cb in self._on_match_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(data)
                    else:
                        cb(data)
                except Exception as e:
                    logger.error(f"Match callback error: {e}")
        
        elif msg_type in ["signal_created", "signal_faded", "bet_settled"]:
            for cb in self._on_signal_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(data)
                    else:
                        cb(data)
                except Exception as e:
                    logger.error(f"Signal callback error: {e}")
    
    async def stop_listening(self):
        """停止监听"""
        if self._ws_task:
            self._ws_task.cancel()
        if self._ws:
            await self._ws.close()
    
    # ==========================================
    # 策略模板
    # ==========================================
    
    async def run_strategy(self, name: str, params: dict = None) -> None:
        """
        运行策略模板
        
        可用策略:
        - "dca": 定投策略
        - "grid": 网格交易
        - "momentum": 动量策略
        """
        params = params or {}
        
        if name == "dca":
            await self._strategy_dca(params)
        elif name == "grid":
            await self._strategy_grid(params)
        elif name == "momentum":
            await self._strategy_momentum(params)
        else:
            raise ValueError(f"Unknown strategy: {name}")
    
    async def _strategy_dca(self, params: dict):
        """
        定投策略
        
        params:
        - asset: 资产
        - amount: 每次金额
        - interval_seconds: 间隔
        - times: 次数
        """
        asset = params.get("asset", "ETH")
        amount = params.get("amount", 10)
        interval = params.get("interval_seconds", 3600)
        times = params.get("times", 10)
        
        for i in range(times):
            result = await self.long(asset, amount)
            print(f"DCA #{i+1}: {result.message}")
            if i < times - 1:
                await asyncio.sleep(interval)
    
    async def _strategy_grid(self, params: dict):
        """
        网格交易策略
        
        params:
        - asset: 资产
        - lower: 下限价格
        - upper: 上限价格
        - grids: 网格数
        - amount_per_grid: 每格金额
        """
        asset = params.get("asset", "ETH")
        lower = params.get("lower", 2000)
        upper = params.get("upper", 2500)
        grids = params.get("grids", 5)
        amount = params.get("amount_per_grid", 20)
        
        step = (upper - lower) / grids
        
        for i in range(grids):
            price = lower + (i * step)
            # 创建预测：如果价格低于这个点，做多
            await self.create_signal(asset, "price_below", price, stake=amount)
            print(f"Grid #{i+1}: Buy signal at ${price:.0f}")
    
    async def _strategy_momentum(self, params: dict):
        """
        动量策略 (简化版)
        
        跟随市场方向
        """
        asset = params.get("asset", "ETH")
        amount = params.get("amount", 50)
        
        # 获取当前价格
        await self._ensure_session()
        async with self.session.get(f"{self.base_url}/prices/{asset}") as resp:
            data = await resp.json()
            price = data.get("price", 0)
            change = data.get("change_24h", 0)
        
        if change > 0:
            result = await self.long(asset, amount)
            print(f"Momentum: LONG (24h change: +{change:.1f}%) - {result.message}")
        else:
            result = await self.short(asset, amount)
            print(f"Momentum: SHORT (24h change: {change:.1f}%) - {result.message}")
    
    # ==========================================
    # 持仓管理 + 止盈止损
    # ==========================================
    
    async def get_positions(self) -> List[dict]:
        """获取我的持仓"""
        await self._ensure_agent()
        await self._ensure_session()
        
        async with self.session.get(f"{self.base_url}/positions/{self.agent_id}") as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("positions", [])
            return []
    
    async def get_portfolio(self) -> dict:
        """获取投资组合概览"""
        await self._ensure_agent()
        await self._ensure_session()
        
        async with self.session.get(f"{self.base_url}/portfolio/{self.agent_id}") as resp:
            if resp.status == 200:
                return await resp.json()
            return {}
    
    async def set_stop_loss(self, position_id: str, price: float) -> bool:
        """设置止损"""
        await self._ensure_session()
        async with self.session.post(
            f"{self.base_url}/positions/{position_id}/stop-loss",
            json={"price": price}
        ) as resp:
            return resp.status == 200
    
    async def set_take_profit(self, position_id: str, price: float) -> bool:
        """设置止盈"""
        await self._ensure_session()
        async with self.session.post(
            f"{self.base_url}/positions/{position_id}/take-profit",
            json={"price": price}
        ) as resp:
            return resp.status == 200
    
    async def close_position(self, position_id: str) -> TradeResult:
        """手动平仓"""
        await self._ensure_session()
        async with self.session.post(f"{self.base_url}/positions/{position_id}/close") as resp:
            data = await resp.json()
            if data.get("success"):
                return TradeResult(success=True, message=f"Position closed. PnL: ${data.get('pnl', 0):.2f}")
            return TradeResult(success=False, message=data.get("detail", "Failed"))
    
    # ==========================================
    # 风控告警
    # ==========================================
    
    async def get_alerts(self) -> List[dict]:
        """获取风控告警"""
        await self._ensure_agent()
        await self._ensure_session()
        
        async with self.session.get(f"{self.base_url}/alerts/{self.agent_id}") as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("alerts", [])
            return []
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        await self._ensure_session()
        async with self.session.post(f"{self.base_url}/alerts/{alert_id}/ack") as resp:
            return resp.status == 200
    
    def on_alert(self, callback: Callable):
        """注册告警回调 (WebSocket)"""
        async def wrapper(data):
            if data.get("type") == "risk_alert" and data.get("agent_id") == self.agent_id:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
        self._on_signal_callbacks.append(wrapper)
        return self
    
    # ==========================================
    # 策略回测
    # ==========================================
    
    async def backtest(
        self,
        strategy_name: str,
        asset: str = "ETH",
        days: int = 30,
        initial_capital: float = 1000,
    ) -> dict:
        """
        回测策略
        
        可用策略: momentum, grid, dca
        """
        await self._ensure_session()
        
        async with self.session.post(
            f"{self.base_url}/backtest",
            json={
                "strategy": strategy_name,
                "asset": asset,
                "days": days,
                "initial_capital": initial_capital,
            }
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return {"error": "Backtest failed"}
    
    # ==========================================
    # 工具方法
    # ==========================================
    
    async def get_prices(self) -> dict:
        """获取价格"""
        await self._ensure_session()
        async with self.session.get(f"{self.base_url}/prices") as resp:
            data = await resp.json()
            prices = data.get("prices", data)
            return {k: v.get("price", v) if isinstance(v, dict) else v for k, v in prices.items()}
    
    async def get_my_intents(self) -> list:
        """获取我的 Intent"""
        await self._ensure_agent()
        await self._ensure_session()
        async with self.session.get(f"{self.base_url}/intents") as resp:
            data = await resp.json()
            return [i for i in data.get("intents", []) if i.get("agent_id") == self.agent_id]
    
    async def close(self):
        """关闭连接"""
        await self.stop_listening()
        if self.session:
            await self.session.close()


# 便捷函数
async def quick_trade(instruction: str, base_url: str = "https://api.riverbit.ai") -> TradeResult:
    """
    一行交易
    
    用法:
        result = await quick_trade("long ETH $100 5x")
    """
    sdk = AINativeSDK(base_url)
    result = await sdk.trade(instruction)
    await sdk.close()
    return result


# 同步包装 (方便非 async 环境)
def trade_sync(instruction: str, base_url: str = "https://api.riverbit.ai") -> TradeResult:
    """同步版本的交易"""
    return asyncio.run(quick_trade(instruction, base_url))
