"""
Trading Hub SDK - AI-Native Interface

设计原则：
1. 一行代码能交易
2. 异步优先
3. 自动重连
4. 内置决策辅助
"""

import asyncio
import aiohttp
import json
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class Direction(Enum):
    LONG = "long"
    SHORT = "short"

@dataclass
class Intent:
    intent_id: str
    agent_id: str
    direction: str
    asset: str
    size: float
    leverage: int
    status: str
    matched_with: Optional[str] = None

@dataclass  
class Match:
    match_id: str
    my_intent: str
    counterparty: str
    asset: str
    size: float
    price: float

class TradingHub:
    """
    AI-Native 交易接口
    
    用法:
        hub = TradingHub(wallet="0x...")
        await hub.connect()
        
        # 一行交易
        match = await hub.long("BTC", 100, leverage=10)
        
        # 或者更简单
        await hub.bet("BTC will pump", 100)
    """
    
    def __init__(
        self,
        wallet: str,
        api_url: str = "http://localhost:8082",
        ws_url: str = "ws://localhost:8082/ws",
        auto_register: bool = True,
    ):
        self.wallet = wallet
        self.api_url = api_url
        self.ws_url = ws_url
        self.auto_register = auto_register
        
        self.agent_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        
        # 回调
        self._on_match: Optional[Callable] = None
        self._on_intent: Optional[Callable] = None
        
        # 状态
        self.open_intents: Dict[str, Intent] = {}
        self.matches: List[Match] = []
        self.connected = False
    
    async def connect(self) -> "TradingHub":
        """连接并注册"""
        self.session = aiohttp.ClientSession()
        
        if self.auto_register:
            await self._register()
        
        # 启动 WebSocket
        asyncio.create_task(self._ws_loop())
        
        self.connected = True
        return self
    
    async def disconnect(self):
        """断开连接"""
        self.connected = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
    
    async def _register(self):
        """注册 Agent"""
        async with self.session.post(
            f"{self.api_url}/agents/register",
            json={"wallet_address": self.wallet}
        ) as resp:
            data = await resp.json()
            self.agent_id = data["agent"]["agent_id"]
    
    async def _ws_loop(self):
        """WebSocket 监听循环"""
        while self.connected:
            try:
                async with self.session.ws_connect(self.ws_url) as ws:
                    self.ws = ws
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_ws_message(json.loads(msg.data))
            except:
                await asyncio.sleep(3)  # 重连
    
    async def _handle_ws_message(self, message: dict):
        """处理 WebSocket 消息"""
        msg_type = message.get("type")
        data = message.get("data", {})
        
        if msg_type == "new_match":
            if data.get("agent_a_id") == self.agent_id or data.get("agent_b_id") == self.agent_id:
                match = Match(
                    match_id=data["match_id"],
                    my_intent=data["intent_a_id"] if data["agent_a_id"] == self.agent_id else data["intent_b_id"],
                    counterparty=data["agent_b_id"] if data["agent_a_id"] == self.agent_id else data["agent_a_id"],
                    asset=data["asset"],
                    size=data["size_usdc"],
                    price=data["price"],
                )
                self.matches.append(match)
                if self._on_match:
                    await self._on_match(match)
    
    # === 核心交易方法 ===
    
    async def long(
        self,
        asset: str = "BTC",
        size: float = 100,
        leverage: int = 1,
        wait_match: bool = True,
    ) -> Optional[Match]:
        """
        做多
        
        await hub.long("BTC", 100, leverage=10)
        """
        return await self._trade(Direction.LONG, asset, size, leverage, wait_match)
    
    async def short(
        self,
        asset: str = "BTC",
        size: float = 100,
        leverage: int = 1,
        wait_match: bool = True,
    ) -> Optional[Match]:
        """
        做空
        
        await hub.short("ETH", 200, leverage=5)
        """
        return await self._trade(Direction.SHORT, asset, size, leverage, wait_match)
    
    async def _trade(
        self,
        direction: Direction,
        asset: str,
        size: float,
        leverage: int,
        wait_match: bool,
    ) -> Optional[Match]:
        """内部交易方法"""
        
        # 标准化资产名
        if not asset.endswith("-PERP"):
            asset = f"{asset.upper()}-PERP"
        
        async with self.session.post(
            f"{self.api_url}/intents",
            json={
                "agent_id": self.agent_id,
                "intent_type": direction.value,
                "asset": asset,
                "size_usdc": size,
                "leverage": leverage,
            }
        ) as resp:
            data = await resp.json()
            
            if data.get("matched"):
                return Match(
                    match_id=data["match"]["match_id"],
                    my_intent=data["intent"]["intent_id"],
                    counterparty=data["match"]["agent_b_id"] if data["match"]["agent_a_id"] == self.agent_id else data["match"]["agent_a_id"],
                    asset=asset,
                    size=data["match"]["size_usdc"],
                    price=data["match"]["price"],
                )
            
            # 保存开放 Intent
            intent = Intent(
                intent_id=data["intent"]["intent_id"],
                agent_id=self.agent_id,
                direction=direction.value,
                asset=asset,
                size=size,
                leverage=leverage,
                status="open",
            )
            self.open_intents[intent.intent_id] = intent
            
            return None
    
    async def bet(self, prediction: str, amount: float = 100) -> Optional[Match]:
        """
        自然语言下注
        
        await hub.bet("BTC will pump", 100)
        await hub.bet("ETH 要跌", 50)
        """
        prediction_lower = prediction.lower()
        
        # 解析方向
        bullish_keywords = ["pump", "涨", "上", "moon", "bull", "up", "long", "买"]
        bearish_keywords = ["dump", "跌", "下", "crash", "bear", "down", "short", "卖"]
        
        is_bullish = any(kw in prediction_lower for kw in bullish_keywords)
        is_bearish = any(kw in prediction_lower for kw in bearish_keywords)
        
        if not is_bullish and not is_bearish:
            raise ValueError("Can't determine direction from prediction")
        
        direction = Direction.LONG if is_bullish else Direction.SHORT
        
        # 解析资产
        asset = "BTC"  # 默认
        for a in ["BTC", "ETH", "SOL"]:
            if a.lower() in prediction_lower:
                asset = a
                break
        
        return await self._trade(direction, asset, amount, leverage=1, wait_match=True)
    
    # === 市场数据 ===
    
    async def get_open_intents(self, asset: str = None) -> List[dict]:
        """获取所有开放 Intent"""
        url = f"{self.api_url}/intents"
        if asset:
            url += f"?asset={asset}"
        
        async with self.session.get(url) as resp:
            data = await resp.json()
            return data.get("intents", [])
    
    async def get_orderbook(self, asset: str = "BTC-PERP") -> dict:
        """获取订单簿视图"""
        intents = await self.get_open_intents(asset)
        
        longs = [i for i in intents if i["intent_type"] == "long"]
        shorts = [i for i in intents if i["intent_type"] == "short"]
        
        return {
            "asset": asset,
            "longs": sorted(longs, key=lambda x: x["size_usdc"], reverse=True),
            "shorts": sorted(shorts, key=lambda x: x["size_usdc"], reverse=True),
            "total_long_size": sum(i["size_usdc"] for i in longs),
            "total_short_size": sum(i["size_usdc"] for i in shorts),
            "sentiment": "bullish" if len(longs) > len(shorts) else "bearish",
        }
    
    async def get_leaderboard(self) -> List[dict]:
        """获取 Agent 排行榜"""
        async with self.session.get(f"{self.api_url}/leaderboard") as resp:
            data = await resp.json()
            return data.get("leaderboard", [])
    
    # === 回调注册 ===
    
    def on_match(self, callback: Callable):
        """注册匹配回调"""
        self._on_match = callback
        return callback
    
    def on_intent(self, callback: Callable):
        """注册新 Intent 回调"""
        self._on_intent = callback
        return callback
    
    # === 决策辅助 ===
    
    async def should_trade(self, asset: str = "BTC-PERP") -> dict:
        """
        AI 决策辅助：基于当前市场状态给出建议
        
        result = await hub.should_trade("BTC")
        if result["confidence"] > 0.7:
            await hub.long("BTC", 100)
        """
        orderbook = await self.get_orderbook(asset)
        
        long_size = orderbook["total_long_size"]
        short_size = orderbook["total_short_size"]
        total = long_size + short_size
        
        if total == 0:
            return {
                "recommendation": "wait",
                "confidence": 0.5,
                "reason": "No market activity",
            }
        
        long_ratio = long_size / total
        
        # 逆向思维：大家都看多时做空
        if long_ratio > 0.7:
            return {
                "recommendation": "short",
                "confidence": long_ratio,
                "reason": f"Market too bullish ({long_ratio:.0%} long). Contrarian short.",
            }
        elif long_ratio < 0.3:
            return {
                "recommendation": "long",
                "confidence": 1 - long_ratio,
                "reason": f"Market too bearish ({1-long_ratio:.0%} short). Contrarian long.",
            }
        else:
            return {
                "recommendation": "wait",
                "confidence": 0.5,
                "reason": "Market balanced. No clear signal.",
            }
    
    # === Context Manager ===
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.disconnect()


# === 便捷函数 ===

async def quick_long(asset: str, size: float, wallet: str = "0xquick") -> Optional[Match]:
    """一行做多"""
    async with TradingHub(wallet) as hub:
        return await hub.long(asset, size)

async def quick_short(asset: str, size: float, wallet: str = "0xquick") -> Optional[Match]:
    """一行做空"""
    async with TradingHub(wallet) as hub:
        return await hub.short(asset, size)


# === 测试 ===

async def demo():
    print("🤖 AI Trading Agent Demo")
    print("=" * 50)
    
    # 创建两个 Agent
    async with TradingHub("0xAgent_A") as agent_a:
        async with TradingHub("0xAgent_B") as agent_b:
            
            print(f"\nAgent A: {agent_a.agent_id}")
            print(f"Agent B: {agent_b.agent_id}")
            
            # Agent A 想做多
            print("\n📈 Agent A: long BTC 100 USDC 10x")
            result_a = await agent_a.long("BTC", 100, leverage=10)
            print(f"   Matched: {result_a is not None}")
            
            # Agent B 想做空 → 自动匹配！
            print("\n📉 Agent B: short BTC 100 USDC 10x")
            result_b = await agent_b.short("BTC", 100, leverage=10)
            print(f"   Matched: {result_b is not None}")
            if result_b:
                print(f"   Match ID: {result_b.match_id}")
                print(f"   Price: ${result_b.price:,}")
                print(f"   Counterparty: {result_b.counterparty}")
            
            # 自然语言下注
            print("\n🎲 Agent A: bet('ETH will pump', 50)")
            await agent_a.bet("ETH will pump", 50)
            
            # 决策辅助
            print("\n🤔 Agent B: should_trade('ETH')?")
            advice = await agent_b.should_trade("ETH-PERP")
            print(f"   Recommendation: {advice['recommendation']}")
            print(f"   Confidence: {advice['confidence']:.0%}")
            print(f"   Reason: {advice['reason']}")

if __name__ == "__main__":
    asyncio.run(demo())
