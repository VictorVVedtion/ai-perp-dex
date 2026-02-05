"""
AI Perp DEX - 主客户端

AI-Native 交易接口，一行代码开始交易。
"""

import asyncio
import json
import logging
from typing import Optional, Callable, List, Dict, Any, Union
from datetime import datetime

import aiohttp

from .models import (
    Intent,
    Match,
    Position,
    Signal,
    Agent,
    Balance,
    OrderBook,
    Price,
    TradeAdvice,
    TradeResult,
    RoutingResult,
    Direction,
    IntentStatus,
    SignalType,
)
from .exceptions import (
    TradingHubError,
    AuthenticationError,
    RateLimitError,
    InsufficientBalanceError,
    InsufficientMarginError,
    NetworkError,
    InvalidParameterError,
    ServerError,
    WebSocketError,
)

logger = logging.getLogger(__name__)


class TradingHub:
    """
    AI-Native 永续合约交易客户端
    
    用法:
        # 方式1: Context Manager (推荐)
        async with TradingHub(api_key="th_xxx") as hub:
            await hub.long("BTC", 100, leverage=5)
        
        # 方式2: 手动管理
        hub = TradingHub(api_key="th_xxx")
        await hub.connect()
        await hub.long("BTC", 100)
        await hub.disconnect()
        
        # 方式3: 自然语言
        await hub.bet("BTC will pump", 100)
    """
    
    DEFAULT_API_URL = "http://localhost:8082"
    SUPPORTED_ASSETS = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
    
    def __init__(
        self,
        api_key: str = None,
        wallet: str = None,
        api_url: str = None,
        ws_url: str = None,
        auto_register: bool = True,
        timeout: int = 30,
    ):
        """
        初始化客户端
        
        Args:
            api_key: API Key (推荐方式)
            wallet: 钱包地址 (如果没有 api_key，会自动注册)
            api_url: API 地址
            ws_url: WebSocket 地址
            auto_register: 是否自动注册
            timeout: 请求超时秒数
        """
        self.api_key = api_key
        self.wallet = wallet or f"0x{id(self):040x}"
        self.api_url = (api_url or self.DEFAULT_API_URL).rstrip("/")
        self.ws_url = ws_url or self.api_url.replace("http", "ws") + "/ws"
        self.auto_register = auto_register
        self.timeout = timeout
        
        # 状态
        self.agent_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._connected = False
        
        # 缓存
        self._open_intents: Dict[str, Intent] = {}
        self._positions: Dict[str, Position] = {}
        self._matches: List[Match] = []
        
        # 回调
        self._on_match: Optional[Callable] = None
        self._on_intent: Optional[Callable] = None
        self._on_price: Optional[Callable] = None
        self._on_pnl: Optional[Callable] = None
        self._on_liquidation: Optional[Callable] = None
    
    # === Connection ===
    
    async def connect(self) -> "TradingHub":
        """连接到 Trading Hub"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # 如果有 API Key，验证并获取 agent_id
        if self.api_key:
            try:
                me = await self._request("GET", "/auth/me")
                self.agent_id = me["agent"]["agent_id"]
            except AuthenticationError:
                raise
        elif self.auto_register:
            # 自动注册
            await self._register()
        
        # 启动 WebSocket
        self._ws_task = asyncio.create_task(self._ws_loop())
        self._connected = True
        
        return self
    
    async def disconnect(self):
        """断开连接"""
        self._connected = False
        
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
        
        if self._session:
            await self._session.close()
    
    async def _register(self):
        """注册新 Agent"""
        result = await self._request(
            "POST",
            "/agents/register",
            json={"wallet_address": self.wallet},
            skip_auth=True,
        )
        self.agent_id = result["agent"]["agent_id"]
        self.api_key = result.get("api_key")
        return result
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    # === HTTP Client ===
    
    async def _request(
        self,
        method: str,
        path: str,
        json: dict = None,
        params: dict = None,
        skip_auth: bool = False,
    ) -> dict:
        """发送 HTTP 请求"""
        if not self._session:
            raise NetworkError("Not connected. Call connect() first.")
        
        url = f"{self.api_url}{path}"
        headers = {}
        
        if not skip_auth and self.api_key:
            headers["X-API-Key"] = self.api_key
        
        try:
            async with self._session.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
            ) as resp:
                data = await resp.json()
                
                if resp.status == 401:
                    raise AuthenticationError(data.get("detail", "Unauthorized"))
                elif resp.status == 429:
                    raise RateLimitError(
                        data.get("detail", "Rate limit exceeded"),
                        retry_after=int(resp.headers.get("Retry-After", 60)),
                    )
                elif resp.status >= 400:
                    error_msg = data.get("detail", data.get("error", str(data)))
                    
                    # 解析特定错误
                    if "insufficient" in error_msg.lower():
                        if "margin" in error_msg.lower():
                            raise InsufficientMarginError(0, 0, error_msg)
                        raise InsufficientBalanceError(0, 0, error_msg)
                    
                    raise TradingHubError(error_msg, status_code=resp.status)
                
                return data
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error: {e}", original=e)
    
    # === WebSocket ===
    
    async def _ws_loop(self):
        """WebSocket 监听循环 (自动重连)"""
        while self._connected:
            try:
                async with self._session.ws_connect(self.ws_url) as ws:
                    self._ws = ws
                    logger.info("WebSocket connected")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_ws_message(json.loads(msg.data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.warning(f"WebSocket error: {ws.exception()}")
                            break
                            
            except aiohttp.ClientError as e:
                if self._connected:
                    logger.warning(f"WebSocket disconnected, reconnecting in 3s: {e}")
                    await asyncio.sleep(3)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected WebSocket error: {e}")
                if self._connected:
                    await asyncio.sleep(3)
    
    async def _handle_ws_message(self, message: dict):
        """处理 WebSocket 消息"""
        msg_type = message.get("type")
        data = message.get("data", message)
        
        if msg_type == "new_match":
            # 检查是否是我的匹配
            if data.get("agent_a_id") == self.agent_id or data.get("agent_b_id") == self.agent_id:
                match = Match.from_dict(data, self.agent_id)
                self._matches.append(match)
                if self._on_match:
                    await self._on_match(match)
        
        elif msg_type == "new_intent":
            if self._on_intent:
                intent = Intent.from_dict(data)
                await self._on_intent(intent)
        
        elif msg_type == "pnl_update":
            if data.get("agent_id") == self.agent_id and self._on_pnl:
                await self._on_pnl(data)
        
        elif msg_type == "liquidation":
            if data.get("agent_id") == self.agent_id and self._on_liquidation:
                await self._on_liquidation(data)
    
    # === Core Trading ===
    
    async def long(
        self,
        asset: str = "BTC",
        size: float = 100,
        leverage: int = 1,
        reason: str = "",
        wait_match: bool = False,
    ) -> TradeResult:
        """
        开多仓
        
        Args:
            asset: 资产 (BTC, ETH, SOL)
            size: 仓位大小 (USDC)
            leverage: 杠杆倍数 (1-100)
            reason: 交易理由 (会显示在 Agent Thoughts)
            wait_match: 是否等待匹配
        
        Returns:
            TradeResult 包含 intent, routing, match, position
        
        Example:
            result = await hub.long("BTC", 100, leverage=5)
            if result.is_matched:
                print(f"Matched at ${result.match.price}")
        """
        return await self._trade(Direction.LONG, asset, size, leverage, reason, wait_match)
    
    async def short(
        self,
        asset: str = "BTC",
        size: float = 100,
        leverage: int = 1,
        reason: str = "",
        wait_match: bool = False,
    ) -> TradeResult:
        """
        开空仓
        
        Args:
            asset: 资产 (BTC, ETH, SOL)
            size: 仓位大小 (USDC)
            leverage: 杠杆倍数 (1-100)
            reason: 交易理由
            wait_match: 是否等待匹配
        
        Returns:
            TradeResult
        """
        return await self._trade(Direction.SHORT, asset, size, leverage, reason, wait_match)
    
    async def _trade(
        self,
        direction: Direction,
        asset: str,
        size: float,
        leverage: int,
        reason: str,
        wait_match: bool,
    ) -> TradeResult:
        """内部交易方法"""
        # 标准化资产名
        asset = self._normalize_asset(asset)
        
        # 验证参数
        if size <= 0:
            raise InvalidParameterError("size", size, "must be > 0")
        if leverage < 1 or leverage > 100:
            raise InvalidParameterError("leverage", leverage, "must be 1-100")
        
        result = await self._request(
            "POST",
            "/intents",
            json={
                "agent_id": self.agent_id,
                "intent_type": direction.value,
                "asset": asset,
                "size_usdc": size,
                "leverage": leverage,
                "reason": reason,
            }
        )
        
        intent = Intent.from_dict(result["intent"])
        routing = RoutingResult.from_dict(result["routing"])
        
        match = None
        if result.get("internal_match"):
            match = Match.from_dict(result["internal_match"], self.agent_id)
        
        position = None
        if result.get("position") and not result["position"].get("error"):
            position = Position.from_dict(result["position"])
        
        return TradeResult(
            intent=intent,
            routing=routing,
            match=match,
            position=position,
        )
    
    async def bet(
        self,
        prediction: str,
        amount: float = 100,
        leverage: int = 1,
    ) -> TradeResult:
        """
        自然语言下注
        
        Args:
            prediction: 预测描述 (如 "BTC will pump", "ETH 要跌")
            amount: 金额
            leverage: 杠杆
        
        Example:
            await hub.bet("BTC will pump", 100)
            await hub.bet("ETH 要跌", 50, leverage=3)
        """
        prediction_lower = prediction.lower()
        
        # 解析方向
        bullish = ["pump", "涨", "上", "moon", "bull", "up", "long", "买", "rise", "高"]
        bearish = ["dump", "跌", "下", "crash", "bear", "down", "short", "卖", "fall", "低"]
        
        is_bullish = any(kw in prediction_lower for kw in bullish)
        is_bearish = any(kw in prediction_lower for kw in bearish)
        
        if not is_bullish and not is_bearish:
            raise InvalidParameterError(
                "prediction", 
                prediction, 
                "Cannot determine direction. Include words like 'pump', 'dump', '涨', '跌'"
            )
        
        direction = Direction.LONG if is_bullish else Direction.SHORT
        
        # 解析资产
        asset = "BTC"  # 默认
        for a in ["SOL", "ETH", "BTC"]:  # 先匹配短的
            if a.lower() in prediction_lower:
                asset = a
                break
        
        return await self._trade(direction, asset, amount, leverage, reason=prediction, wait_match=False)
    
    # === Position Management ===
    
    async def get_positions(self) -> List[Position]:
        """获取所有持仓"""
        result = await self._request("GET", f"/positions/{self.agent_id}")
        return [Position.from_dict(p) for p in result.get("positions", [])]
    
    async def get_portfolio(self) -> dict:
        """获取投资组合概览"""
        return await self._request("GET", f"/portfolio/{self.agent_id}")
    
    async def close_position(self, position_id: str) -> dict:
        """平仓"""
        return await self._request("POST", f"/positions/{position_id}/close")
    
    async def set_stop_loss(self, position_id: str, price: float):
        """设置止损"""
        return await self._request(
            "POST",
            f"/positions/{position_id}/stop-loss",
            json={"price": price}
        )
    
    async def set_take_profit(self, position_id: str, price: float):
        """设置止盈"""
        return await self._request(
            "POST",
            f"/positions/{position_id}/take-profit",
            json={"price": price}
        )
    
    # === Balance ===
    
    async def get_balance(self) -> Balance:
        """获取余额"""
        result = await self._request("GET", f"/balance/{self.agent_id}")
        return Balance.from_dict(result)
    
    async def deposit(self, amount: float) -> Balance:
        """入金"""
        result = await self._request(
            "POST",
            "/deposit",
            json={"agent_id": self.agent_id, "amount": amount}
        )
        return Balance.from_dict(result["balance"])
    
    async def withdraw(self, amount: float) -> Balance:
        """出金"""
        result = await self._request(
            "POST",
            "/withdraw",
            json={"agent_id": self.agent_id, "amount": amount}
        )
        return Balance.from_dict(result["balance"])
    
    # === Market Data ===
    
    async def get_price(self, asset: str = "BTC") -> Price:
        """获取价格"""
        asset = asset.upper().replace("-PERP", "")
        result = await self._request("GET", f"/prices/{asset}")
        result["asset"] = asset
        return Price.from_dict(result)
    
    async def get_prices(self) -> Dict[str, Price]:
        """获取所有价格"""
        result = await self._request("GET", "/prices")
        return {k: Price.from_dict({**v, "asset": k}) for k, v in result.get("prices", {}).items()}
    
    async def get_orderbook(self, asset: str = "BTC-PERP") -> OrderBook:
        """获取订单簿"""
        asset = self._normalize_asset(asset)
        intents = await self._request("GET", "/intents", params={"asset": asset})
        
        all_intents = intents.get("intents", [])
        longs = [i for i in all_intents if i["intent_type"] == "long"]
        shorts = [i for i in all_intents if i["intent_type"] == "short"]
        
        return OrderBook(
            asset=asset,
            longs=sorted(longs, key=lambda x: x["size_usdc"], reverse=True),
            shorts=sorted(shorts, key=lambda x: x["size_usdc"], reverse=True),
            total_long_size=sum(i["size_usdc"] for i in longs),
            total_short_size=sum(i["size_usdc"] for i in shorts),
            sentiment="bullish" if len(longs) > len(shorts) else "bearish",
        )
    
    async def get_leaderboard(self, limit: int = 20) -> List[Agent]:
        """获取排行榜"""
        result = await self._request("GET", "/leaderboard", params={"limit": limit})
        return [Agent.from_dict(a) for a in result.get("leaderboard", [])]
    
    # === AI Decision Helpers ===
    
    async def should_trade(self, asset: str = "BTC-PERP") -> TradeAdvice:
        """
        AI 决策辅助：基于市场情绪给出建议
        
        Example:
            advice = await hub.should_trade("BTC")
            if advice.confidence > 0.7:
                if advice.recommendation == "long":
                    await hub.long("BTC", 100)
        """
        orderbook = await self.get_orderbook(asset)
        
        total = orderbook.total_long_size + orderbook.total_short_size
        if total == 0:
            return TradeAdvice(
                recommendation="wait",
                confidence=0.5,
                reason="No market activity",
            )
        
        long_ratio = orderbook.total_long_size / total
        
        # 逆向思维
        if long_ratio > 0.7:
            return TradeAdvice(
                recommendation="short",
                confidence=long_ratio,
                reason=f"Market too bullish ({long_ratio:.0%} long). Contrarian short.",
            )
        elif long_ratio < 0.3:
            return TradeAdvice(
                recommendation="long",
                confidence=1 - long_ratio,
                reason=f"Market too bearish ({1-long_ratio:.0%} short). Contrarian long.",
            )
        else:
            return TradeAdvice(
                recommendation="wait",
                confidence=0.5,
                reason="Market balanced. No clear signal.",
            )
    
    # === Signal Betting ===
    
    async def create_signal(
        self,
        asset: str,
        signal_type: Union[str, SignalType],
        target_value: float,
        stake: float,
        duration_hours: int = 24,
    ) -> Signal:
        """
        创建预测信号
        
        Args:
            asset: 资产
            signal_type: "price_above", "price_below", "price_change"
            target_value: 目标价格
            stake: 押注金额
            duration_hours: 持续小时数
        
        Example:
            # ETH 24h 后 > $2200
            signal = await hub.create_signal("ETH", "price_above", 2200, stake=50)
        """
        if isinstance(signal_type, SignalType):
            signal_type = signal_type.value
        
        result = await self._request(
            "POST",
            "/signals",
            json={
                "agent_id": self.agent_id,
                "asset": self._normalize_asset(asset),
                "signal_type": signal_type,
                "target_value": target_value,
                "stake_amount": stake,
                "duration_hours": duration_hours,
            }
        )
        return Signal.from_dict(result["signal"])
    
    async def fade_signal(self, signal_id: str) -> dict:
        """Fade 一个信号 (对赌)"""
        return await self._request(
            "POST",
            "/signals/fade",
            json={"signal_id": signal_id, "fader_id": self.agent_id}
        )
    
    async def get_open_signals(self, asset: str = None) -> List[Signal]:
        """获取开放信号"""
        params = {"status": "open"}
        if asset:
            params["asset"] = self._normalize_asset(asset)
        result = await self._request("GET", "/signals", params=params)
        return [Signal.from_dict(s) for s in result.get("signals", [])]
    
    # === Callbacks ===
    
    def on_match(self, callback: Callable):
        """注册匹配回调"""
        self._on_match = callback
        return callback
    
    def on_intent(self, callback: Callable):
        """注册新 Intent 回调"""
        self._on_intent = callback
        return callback
    
    def on_pnl(self, callback: Callable):
        """注册 PnL 更新回调"""
        self._on_pnl = callback
        return callback
    
    def on_liquidation(self, callback: Callable):
        """注册强平回调"""
        self._on_liquidation = callback
        return callback
    
    # === Utilities ===
    
    def _normalize_asset(self, asset: str) -> str:
        """标准化资产名"""
        asset = asset.upper()
        if not asset.endswith("-PERP"):
            asset = f"{asset}-PERP"
        return asset
    
    # === Context Manager ===
    
    async def __aenter__(self) -> "TradingHub":
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.disconnect()


# === Quick Functions ===

async def quick_long(
    asset: str,
    size: float,
    leverage: int = 1,
    api_key: str = None,
    api_url: str = None,
) -> TradeResult:
    """
    一行做多
    
    Example:
        from ai_perp_dex import quick_long
        result = await quick_long("BTC", 100, leverage=5)
    """
    async with TradingHub(api_key=api_key, api_url=api_url) as hub:
        return await hub.long(asset, size, leverage)


async def quick_short(
    asset: str,
    size: float,
    leverage: int = 1,
    api_key: str = None,
    api_url: str = None,
) -> TradeResult:
    """
    一行做空
    
    Example:
        from ai_perp_dex import quick_short
        result = await quick_short("ETH", 200, leverage=3)
    """
    async with TradingHub(api_key=api_key, api_url=api_url) as hub:
        return await hub.short(asset, size, leverage)
