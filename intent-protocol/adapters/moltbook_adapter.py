"""
Moltbook Intent Adapter
接入 Moltbook Agent 社交平台
"""

import asyncio
import aiohttp
import re
from typing import AsyncIterator, Optional, List
from dataclasses import dataclass

import sys
sys.path.append('..')
from core.standard import (
    AgentIntent, AgentIdentity, IntentType, SettlementType,
    Wallet, Constraints, Collateral
)
from adapters.base_adapter import IntentAdapter, RawIntent

# Moltbook API 配置
MOLTBOOK_API = "https://moltbook.com/api/v1"
MOLTBOOK_WS = "wss://moltbook.com/ws"

class MoltbookAdapter(IntentAdapter):
    """
    Moltbook 平台适配器
    """
    
    platform_name = "moltbook"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.connected = False
        
        # Intent 检测关键词
        self.intent_keywords = {
            IntentType.TRADE: [
                "long", "short", "买", "卖", "做多", "做空",
                "trade", "position", "leverage", "杠杆"
            ],
            IntentType.SERVICE: [
                "帮你", "help you", "offer", "service", "报价",
                "design", "设计", "consulting", "咨询", "收费"
            ],
            IntentType.SIGNAL: [
                "predict", "预测", "信号", "signal", "涨", "跌",
                "看多", "看空", "target", "目标"
            ],
            IntentType.COLLAB: [
                "合作", "collab", "partner", "分成", "split",
                "一起", "together", "revenue share"
            ],
            IntentType.SWAP: [
                "swap", "exchange", "兑换", "换", "trade for"
            ],
        }
    
    async def connect(self) -> bool:
        """连接到 Moltbook"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.session = aiohttp.ClientSession(headers=headers)
        
        # 测试连接
        try:
            async with self.session.get(f"{MOLTBOOK_API}/health") as resp:
                if resp.status == 200:
                    self.connected = True
                    print(f"[Moltbook] Connected to API")
                    return True
        except Exception as e:
            print(f"[Moltbook] Connection failed: {e}")
            # 继续，可能只是 health 端点不存在
            self.connected = True
            return True
        
        return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        self.connected = False
    
    async def listen(self, channels: List[str] = None) -> AsyncIterator[RawIntent]:
        """
        监听 Moltbook 帖子
        
        Args:
            channels: 监听的 submolt 列表，如 ["crypto", "trading"]
        """
        if not channels:
            channels = ["crypto", "trading", "agentcommerce"]
        
        print(f"[Moltbook] Listening to: {channels}")
        
        # 轮询模式 (Moltbook 可能没有 WebSocket)
        seen_posts = set()
        
        while self.connected:
            for channel in channels:
                try:
                    posts = await self._fetch_posts(channel)
                    for post in posts:
                        if post["id"] not in seen_posts:
                            seen_posts.add(post["id"])
                            
                            # 检查是否包含 Financial Intent
                            if self._has_intent_keywords(post.get("content", "")):
                                yield RawIntent(
                                    platform="moltbook",
                                    post_id=post["id"],
                                    author_id=post.get("author_id", ""),
                                    author_handle=post.get("author_name", ""),
                                    content=post.get("content", ""),
                                    timestamp=post.get("created_at", 0),
                                    metadata={
                                        "submolt": channel,
                                        "title": post.get("title", ""),
                                        "likes": post.get("like_count", 0),
                                    }
                                )
                except Exception as e:
                    print(f"[Moltbook] Error fetching {channel}: {e}")
            
            await asyncio.sleep(30)  # 30秒轮询一次
    
    async def _fetch_posts(self, submolt: str, limit: int = 20) -> List[dict]:
        """获取 submolt 的帖子"""
        try:
            url = f"{MOLTBOOK_API}/posts?submolt={submolt}&limit={limit}&sort=new"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("posts", data.get("data", []))
        except:
            pass
        return []
    
    def _has_intent_keywords(self, content: str) -> bool:
        """检查内容是否包含 Intent 关键词"""
        content_lower = content.lower()
        for keywords in self.intent_keywords.values():
            if any(kw in content_lower for kw in keywords):
                return True
        return False
    
    def _detect_intent_type(self, content: str) -> IntentType:
        """检测 Intent 类型"""
        content_lower = content.lower()
        
        # 按优先级检测
        for intent_type, keywords in self.intent_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return intent_type
        
        return IntentType.TRADE  # 默认
    
    async def parse(self, raw: RawIntent) -> Optional[AgentIntent]:
        """解析 Moltbook 帖子为标准 Intent"""
        
        content = raw.content
        intent_type = self._detect_intent_type(content)
        
        # 获取 Agent 身份
        agent = await self.get_agent_identity(raw.author_id)
        if not agent:
            agent = AgentIdentity(
                platform="moltbook",
                platform_id=raw.author_id,
                platform_handle=raw.author_handle,
            )
        
        # 解析参数
        params = self._extract_params(content, intent_type)
        
        # 确定可接受的结算方式
        settlements = self._determine_settlements(intent_type)
        
        return AgentIntent(
            agent=agent,
            type=intent_type,
            description=content[:200],  # 截断
            params=params,
            acceptable_settlements=settlements,
            source_platform="moltbook",
            source_post_id=raw.post_id,
        )
    
    def _extract_params(self, content: str, intent_type: IntentType) -> dict:
        """从内容中提取参数"""
        
        params = {"raw_content": content}
        content_lower = content.lower()
        
        if intent_type == IntentType.TRADE:
            # 检测方向
            if any(kw in content_lower for kw in ["long", "做多", "买"]):
                params["action"] = "long"
            elif any(kw in content_lower for kw in ["short", "做空", "卖"]):
                params["action"] = "short"
            
            # 检测资产
            for asset in ["btc", "eth", "sol"]:
                if asset in content_lower:
                    params["asset"] = f"{asset.upper()}-PERP"
                    break
            
            # 检测杠杆
            leverage_match = re.search(r'(\d+)x|杠杆(\d+)', content_lower)
            if leverage_match:
                params["leverage"] = int(leverage_match.group(1) or leverage_match.group(2))
            
            # 检测金额
            amount_match = re.search(r'(\d+)\s*(usdc|usd|u|\$)', content_lower)
            if amount_match:
                params["size"] = f"{amount_match.group(1)} USDC"
        
        elif intent_type == IntentType.SERVICE:
            # 检测价格
            price_match = re.search(r'(\d+)\s*(molt|usdc|usd)', content_lower)
            if price_match:
                params["price"] = f"{price_match.group(1)} {price_match.group(2).upper()}"
        
        elif intent_type == IntentType.SIGNAL:
            # 检测置信度
            conf_match = re.search(r'(\d+)%|confidence[:\s]*(\d+)', content_lower)
            if conf_match:
                params["confidence"] = int(conf_match.group(1) or conf_match.group(2)) / 100
        
        return params
    
    def _determine_settlements(self, intent_type: IntentType) -> List[SettlementType]:
        """确定可接受的结算方式"""
        mapping = {
            IntentType.TRADE: [SettlementType.PERP_DEX, SettlementType.EXTERNAL_DEX],
            IntentType.SERVICE: [SettlementType.ESCROW],
            IntentType.SIGNAL: [SettlementType.ORACLE_SETTLE],
            IntentType.COLLAB: [SettlementType.REVENUE_SHARE],
            IntentType.SWAP: [SettlementType.ATOMIC_SWAP],
        }
        return mapping.get(intent_type, [SettlementType.ESCROW])
    
    async def broadcast(self, intent: AgentIntent) -> bool:
        """广播 Intent 到 Moltbook (发帖)"""
        
        if not self.api_key:
            print("[Moltbook] No API key, cannot broadcast")
            return False
        
        # 格式化 Intent 为帖子
        content = self._format_intent_post(intent)
        
        try:
            async with self.session.post(
                f"{MOLTBOOK_API}/posts",
                json={
                    "submolt": "crypto",
                    "title": f"[Intent] {intent.type.value.upper()}",
                    "content": content,
                }
            ) as resp:
                if resp.status in [200, 201]:
                    print(f"[Moltbook] Broadcasted intent: {intent.intent_id}")
                    return True
                else:
                    print(f"[Moltbook] Broadcast failed: {resp.status}")
        except Exception as e:
            print(f"[Moltbook] Broadcast error: {e}")
        
        return False
    
    def _format_intent_post(self, intent: AgentIntent) -> str:
        """格式化 Intent 为 Moltbook 帖子"""
        return f"""
**Financial Intent**

Type: {intent.type.value}
Description: {intent.description}

Params:
```json
{intent.params}
```

Acceptable Settlements: {[s.value for s in intent.acceptable_settlements]}

---
*This intent was generated by Agent Intent Protocol*
Intent ID: {intent.intent_id}
        """.strip()
    
    async def notify(self, agent_id: str, message: str) -> bool:
        """通知 Agent (评论或私信)"""
        # Moltbook 可能不支持私信，先返回 True
        print(f"[Moltbook] Would notify {agent_id}: {message}")
        return True
    
    async def get_agent_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """获取 Agent 身份信息"""
        try:
            async with self.session.get(f"{MOLTBOOK_API}/users/{agent_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return AgentIdentity(
                        platform="moltbook",
                        platform_id=agent_id,
                        platform_handle=data.get("username", data.get("name")),
                        onchain_id=data.get("onchain_id"),
                        wallets=[
                            Wallet(w["chain"], w["address"])
                            for w in data.get("wallets", [])
                        ],
                    )
        except:
            pass
        
        return None


# 测试
async def test_moltbook_adapter():
    print("🧪 Testing Moltbook Adapter")
    print("=" * 50)
    
    adapter = MoltbookAdapter()
    await adapter.connect()
    
    # 模拟解析
    test_posts = [
        "Looking to long BTC 10x with 1000 USDC",
        "I'll help you design tokenomics for 100 MOLT",
        "预测 ETH 24h 涨 10%，信心 80%",
        "想找人合作，你出 Alpha 我出执行，分成 60/40",
    ]
    
    for content in test_posts:
        raw = RawIntent(
            platform="moltbook",
            post_id="test_123",
            author_id="user_456",
            author_handle="@TestAgent",
            content=content,
            timestamp=0,
        )
        
        intent = await adapter.parse(raw)
        if intent:
            print(f"\nContent: {content}")
            print(f"Type: {intent.type.value}")
            print(f"Params: {intent.params}")
            print(f"Settlements: {[s.value for s in intent.acceptable_settlements]}")
    
    await adapter.disconnect()

if __name__ == "__main__":
    asyncio.run(test_moltbook_adapter())
