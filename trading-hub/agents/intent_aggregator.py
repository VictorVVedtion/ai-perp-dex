"""
Intent Aggregator
监控多个平台，聚合 Financial Intent 到 Trading Hub

支持的平台:
- Moltbook (Agent 社交网络)
- MoltX (Agent Twitter)
- 本地 Trading Hub
"""

import asyncio
import aiohttp
import re
from datetime import datetime
from typing import Optional, List, Dict, AsyncIterator
from dataclasses import dataclass

from sdk.tradinghub import TradingHub

@dataclass
class ExternalIntent:
    """外部平台的 Intent"""
    platform: str
    post_id: str
    author: str
    content: str
    intent_type: Optional[str] = None  # long/short/signal
    asset: Optional[str] = None
    size: Optional[float] = None
    confidence: float = 0.5
    timestamp: datetime = None
    url: Optional[str] = None

class IntentAggregator:
    """
    Intent 聚合器
    
    从多个平台收集 Financial Intent，转换为统一格式
    """
    
    def __init__(self, hub_url: str = "https://api.riverbit.ai"):
        self.hub_url = hub_url
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 平台配置
        self.platforms = {
            "moltbook": {
                "api": "https://moltbook.com/api/v1",
                "channels": ["crypto", "trading"],
            },
            "moltx": {
                "api": "https://moltx.io/v1",
                "channels": ["global"],
            },
        }
        
        # Intent 检测模式
        self.patterns = {
            "long": [
                r"(?i)\b(long|做多|买入|bullish|看多)\b.*?(btc|eth|sol)",
                r"(?i)(btc|eth|sol).*?\b(long|做多|买入|bullish|看多)\b",
                r"(?i)\b(going long|longing)\b",
            ],
            "short": [
                r"(?i)\b(short|做空|卖出|bearish|看空)\b.*?(btc|eth|sol)",
                r"(?i)(btc|eth|sol).*?\b(short|做空|卖出|bearish|看空)\b",
                r"(?i)\b(going short|shorting)\b",
            ],
            "signal": [
                r"(?i)(predict|预测|target|目标).*?(\d+)",
                r"(?i)(btc|eth|sol).*(pump|dump|涨|跌)",
            ],
        }
        
        # 资产映射
        self.asset_map = {
            "btc": "BTC-PERP",
            "bitcoin": "BTC-PERP",
            "eth": "ETH-PERP",
            "ethereum": "ETH-PERP",
            "sol": "SOL-PERP",
            "solana": "SOL-PERP",
        }
        
        # 已处理的帖子
        self.processed_posts: set = set()
        
        # 统计
        self.stats = {
            "total_scanned": 0,
            "intents_found": 0,
            "by_platform": {},
        }
    
    async def start(self):
        """启动聚合器"""
        self.session = aiohttp.ClientSession()
        print("🔍 Intent Aggregator started")
        print(f"   Monitoring: {list(self.platforms.keys())}")
    
    async def stop(self):
        """停止聚合器"""
        if self.session:
            await self.session.close()
        print(f"\n📊 Aggregator Stats:")
        print(f"   Total scanned: {self.stats['total_scanned']}")
        print(f"   Intents found: {self.stats['intents_found']}")
    
    async def scan_all(self) -> List[ExternalIntent]:
        """扫描所有平台"""
        all_intents = []
        
        for platform in self.platforms:
            intents = await self.scan_platform(platform)
            all_intents.extend(intents)
        
        return all_intents
    
    async def scan_platform(self, platform: str) -> List[ExternalIntent]:
        """扫描单个平台"""
        if platform == "moltbook":
            return await self._scan_moltbook()
        elif platform == "moltx":
            return await self._scan_moltx()
        return []
    
    async def _scan_moltbook(self) -> List[ExternalIntent]:
        """扫描 Moltbook"""
        intents = []
        config = self.platforms["moltbook"]
        
        for channel in config["channels"]:
            try:
                url = f"{config['api']}/posts?submolt={channel}&limit=20&sort=new"
                async with self.session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        continue
                    
                    data = await resp.json()
                    posts = data.get("posts", data.get("data", []))
                    
                    for post in posts:
                        self.stats["total_scanned"] += 1
                        
                        post_id = f"moltbook_{post.get('id', '')}"
                        if post_id in self.processed_posts:
                            continue
                        
                        self.processed_posts.add(post_id)
                        
                        content = post.get("content", "")
                        intent = self._parse_intent(content, "moltbook", post)
                        
                        if intent:
                            intents.append(intent)
                            self.stats["intents_found"] += 1
                            self.stats["by_platform"]["moltbook"] = \
                                self.stats["by_platform"].get("moltbook", 0) + 1
                            
            except Exception as e:
                print(f"⚠️ Moltbook scan error: {e}")
        
        return intents
    
    async def _scan_moltx(self) -> List[ExternalIntent]:
        """扫描 MoltX"""
        intents = []
        config = self.platforms["moltx"]
        
        try:
            url = f"{config['api']}/feed/global?limit=30"
            headers = {}
            
            # 如果有 API key
            # headers["Authorization"] = f"Bearer {api_key}"
            
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                posts = data.get("data", {}).get("posts", [])
                
                for post in posts:
                    self.stats["total_scanned"] += 1
                    
                    post_id = f"moltx_{post.get('id', '')}"
                    if post_id in self.processed_posts:
                        continue
                    
                    self.processed_posts.add(post_id)
                    
                    content = post.get("content", "")
                    intent = self._parse_intent(content, "moltx", post)
                    
                    if intent:
                        intents.append(intent)
                        self.stats["intents_found"] += 1
                        self.stats["by_platform"]["moltx"] = \
                            self.stats["by_platform"].get("moltx", 0) + 1
                        
        except Exception as e:
            print(f"⚠️ MoltX scan error: {e}")
        
        return intents
    
    def _parse_intent(self, content: str, platform: str, raw: dict) -> Optional[ExternalIntent]:
        """解析帖子内容，提取 Intent"""
        content_lower = content.lower()
        
        # 检测 Intent 类型
        intent_type = None
        confidence = 0.5
        
        for itype, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    intent_type = itype
                    confidence = 0.7
                    break
            if intent_type:
                break
        
        if not intent_type:
            return None
        
        # 提取资产
        asset = None
        for keyword, asset_name in self.asset_map.items():
            if keyword in content_lower:
                asset = asset_name
                break
        
        # 提取金额
        size = None
        size_match = re.search(r'(\d+)\s*(k|K|usdc|usd|\$)', content)
        if size_match:
            size = float(size_match.group(1))
            if size_match.group(2).lower() == 'k':
                size *= 1000
        
        return ExternalIntent(
            platform=platform,
            post_id=raw.get("id", ""),
            author=raw.get("author_name", raw.get("author", "unknown")),
            content=content[:200],
            intent_type=intent_type if intent_type != "signal" else "long",  # signal 转为 long
            asset=asset,
            size=size,
            confidence=confidence,
            timestamp=datetime.now(),
            url=f"https://{platform}.com/post/{raw.get('id', '')}",
        )
    
    async def forward_to_hub(self, intent: ExternalIntent, agent_id: str) -> dict:
        """将外部 Intent 转发到 Trading Hub"""
        if not intent.asset:
            intent.asset = "BTC-PERP"
        if not intent.size:
            intent.size = 100
        
        payload = {
            "agent_id": agent_id,
            "intent_type": intent.intent_type,
            "asset": intent.asset,
            "size_usdc": intent.size,
            "leverage": 1,
        }
        
        try:
            async with self.session.post(
                f"{self.hub_url}/intents",
                json=payload,
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}


async def demo():
    """演示 Intent 聚合"""
    print("=" * 60)
    print("🔍 INTENT AGGREGATOR DEMO")
    print("=" * 60)
    
    aggregator = IntentAggregator()
    await aggregator.start()
    
    # 模拟一些帖子
    test_posts = [
        {"content": "Going long BTC here, 10x leverage 1000 USDC", "author": "trader1"},
        {"content": "Shorting ETH, looks bearish", "author": "trader2"},
        {"content": "Just bought some SOL", "author": "trader3"},
        {"content": "I predict BTC will pump to 80k", "author": "signal_guy"},
        {"content": "Nice weather today", "author": "random"},  # 不是 Intent
    ]
    
    print("\n📝 Parsing test posts:")
    for i, post in enumerate(test_posts):
        post["id"] = f"test_{i}"
        intent = aggregator._parse_intent(post["content"], "test", post)
        
        if intent:
            print(f"\n✅ Found Intent:")
            print(f"   Author: {intent.author}")
            print(f"   Type: {intent.intent_type}")
            print(f"   Asset: {intent.asset}")
            print(f"   Content: {intent.content[:50]}...")
        else:
            print(f"\n⏭️  Skipped: {post['content'][:30]}...")
    
    # 尝试扫描真实平台
    print("\n\n🌐 Scanning real platforms...")
    
    try:
        intents = await aggregator.scan_all()
        print(f"\nFound {len(intents)} intents from real platforms:")
        for intent in intents[:5]:  # 只显示前 5 个
            print(f"\n  Platform: {intent.platform}")
            print(f"  Author: {intent.author}")
            print(f"  Type: {intent.intent_type}")
            print(f"  Asset: {intent.asset}")
            print(f"  Content: {intent.content[:50]}...")
    except Exception as e:
        print(f"  (Scan failed: {e})")
    
    await aggregator.stop()

if __name__ == "__main__":
    asyncio.run(demo())
