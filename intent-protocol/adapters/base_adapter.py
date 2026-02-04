"""
Base Intent Adapter
所有平台适配器的基类
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List
from dataclasses import dataclass
import asyncio

import sys
sys.path.append('..')
from core.standard import AgentIntent, AgentIdentity

@dataclass
class RawIntent:
    """平台原始意图数据"""
    platform: str
    post_id: str
    author_id: str
    author_handle: Optional[str]
    content: str
    timestamp: int
    metadata: dict = None

class IntentAdapter(ABC):
    """
    Intent 适配器基类
    每个平台需要实现这个接口
    """
    
    platform_name: str = "unknown"
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接到平台"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def listen(self, channels: List[str] = None) -> AsyncIterator[RawIntent]:
        """
        监听平台上的意图表达
        
        Args:
            channels: 监听的频道/社区列表 (平台特定)
        
        Yields:
            RawIntent: 原始意图数据
        """
        pass
    
    @abstractmethod
    async def parse(self, raw: RawIntent) -> Optional[AgentIntent]:
        """
        将原始数据解析为标准 Intent
        
        Args:
            raw: 平台原始数据
            
        Returns:
            AgentIntent 或 None (如果无法解析)
        """
        pass
    
    @abstractmethod
    async def broadcast(self, intent: AgentIntent) -> bool:
        """
        广播 Intent 到平台
        
        Args:
            intent: 标准 Intent
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def notify(self, agent_id: str, message: str) -> bool:
        """
        通知 Agent
        
        Args:
            agent_id: 平台内的 Agent ID
            message: 消息内容
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def get_agent_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """
        获取 Agent 身份信息
        
        Args:
            agent_id: 平台内的 Agent ID
            
        Returns:
            AgentIdentity 或 None
        """
        pass
    
    async def run(self, channels: List[str] = None, callback=None):
        """
        运行适配器，持续监听
        
        Args:
            channels: 监听的频道
            callback: 收到 Intent 时的回调函数
        """
        await self.connect()
        
        try:
            async for raw in self.listen(channels):
                intent = await self.parse(raw)
                if intent and callback:
                    await callback(intent)
        finally:
            await self.disconnect()


class MockAdapter(IntentAdapter):
    """
    Mock 适配器 (用于测试)
    """
    
    platform_name = "mock"
    
    def __init__(self):
        self.connected = False
        self.intents_queue = asyncio.Queue()
    
    async def connect(self) -> bool:
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        self.connected = False
    
    async def listen(self, channels: List[str] = None) -> AsyncIterator[RawIntent]:
        while self.connected:
            try:
                raw = await asyncio.wait_for(self.intents_queue.get(), timeout=1.0)
                yield raw
            except asyncio.TimeoutError:
                continue
    
    async def parse(self, raw: RawIntent) -> Optional[AgentIntent]:
        # Mock: 直接返回一个测试 Intent
        from core.standard import IntentType, SettlementType
        
        return AgentIntent(
            agent=AgentIdentity(
                platform="mock",
                platform_id=raw.author_id,
                platform_handle=raw.author_handle,
            ),
            type=IntentType.TRADE,
            description=raw.content,
            params={"raw": raw.content},
            source_platform="mock",
            source_post_id=raw.post_id,
        )
    
    async def broadcast(self, intent: AgentIntent) -> bool:
        print(f"[Mock] Broadcasting: {intent.description}")
        return True
    
    async def notify(self, agent_id: str, message: str) -> bool:
        print(f"[Mock] Notify {agent_id}: {message}")
        return True
    
    async def get_agent_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        return AgentIdentity(
            platform="mock",
            platform_id=agent_id,
            platform_handle=f"@{agent_id}",
        )
    
    # 测试用: 注入意图
    async def inject_intent(self, content: str, author: str = "test_agent"):
        await self.intents_queue.put(RawIntent(
            platform="mock",
            post_id=f"post_{id(content)}",
            author_id=author,
            author_handle=f"@{author}",
            content=content,
            timestamp=int(asyncio.get_event_loop().time()),
        ))
