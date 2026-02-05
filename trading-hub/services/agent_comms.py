"""
Agent Communication Protocol - Agent 间通信协议

让 Agent 之间可以：
1. 发现彼此
2. 交换信号/策略
3. 协商交易
4. 组建联盟
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)


class MessageType(Enum):
    # 发现
    PING = "ping"
    PONG = "pong"
    ANNOUNCE = "announce"
    
    # 交易
    TRADE_REQUEST = "trade_request"  # 请求交易
    TRADE_ACCEPT = "trade_accept"
    TRADE_REJECT = "trade_reject"
    TRADE_COMPLETE = "trade_complete"
    
    # 信号
    SIGNAL_SHARE = "signal_share"  # 分享交易信号
    SIGNAL_ACK = "signal_ack"
    
    # 策略
    STRATEGY_OFFER = "strategy_offer"  # 出售策略
    STRATEGY_BUY = "strategy_buy"
    STRATEGY_DELIVER = "strategy_deliver"
    
    # 联盟
    ALLIANCE_INVITE = "alliance_invite"
    ALLIANCE_ACCEPT = "alliance_accept"
    ALLIANCE_LEAVE = "alliance_leave"
    
    # 通用
    CHAT = "chat"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Agent 间消息"""
    message_id: str
    msg_type: MessageType
    from_agent: str
    to_agent: str  # "*" = broadcast
    payload: dict
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "type": self.msg_type.value,
            "from": self.from_agent,
            "to": self.to_agent,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
        }


@dataclass
class AgentProfile:
    """Agent 公开信息"""
    agent_id: str
    name: str
    description: str = ""
    specialties: List[str] = field(default_factory=list)  # ["BTC", "meme coins", "arbitrage"]
    reputation: float = 0.0  # -1 to 1
    total_trades: int = 0
    win_rate: float = 0.0
    online: bool = True
    last_seen: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "specialties": self.specialties,
            "reputation": self.reputation,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "online": self.online,
        }


@dataclass
class Alliance:
    """Agent 联盟"""
    alliance_id: str
    name: str
    members: List[str]  # agent_ids
    leader_id: str
    created_at: datetime = field(default_factory=datetime.now)
    
    # 联盟设置
    profit_share: float = 0.1  # 利润分成 10%
    signal_sharing: bool = True  # 是否共享信号


class AgentCommunicator:
    """
    Agent 通信中心
    
    用法:
        comm = AgentCommunicator()
        
        # 注册
        comm.register("agent_001", "TradingBot", ["BTC", "ETH"])
        
        # 发现其他 Agent
        agents = comm.discover(specialty="BTC")
        
        # 发送交易请求
        await comm.send_trade_request("agent_001", "agent_002", {
            "asset": "ETH-PERP",
            "side": "long",
            "size": 100,
        })
        
        # 分享信号
        await comm.share_signal("agent_001", {
            "asset": "BTC-PERP",
            "direction": "long",
            "confidence": 0.8,
            "reason": "Breakout above resistance",
        })
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self.messages: Dict[str, AgentMessage] = {}
        self.alliances: Dict[str, Alliance] = {}
        
        # 消息队列 (每个 agent 一个)
        self.inboxes: Dict[str, List[AgentMessage]] = {}
        
        # 回调
        self._handlers: Dict[str, Dict[MessageType, Callable]] = {}
        
        # WebSocket 连接
        self._connections: Dict[str, Any] = {}  # agent_id -> websocket
    
    def register(
        self,
        agent_id: str,
        name: str,
        specialties: List[str] = None,
        description: str = "",
    ) -> AgentProfile:
        """注册 Agent"""
        profile = AgentProfile(
            agent_id=agent_id,
            name=name,
            description=description,
            specialties=specialties or [],
        )
        self.agents[agent_id] = profile
        self.inboxes[agent_id] = []
        return profile
    
    def update_stats(self, agent_id: str, trades: int = 0, wins: int = 0):
        """更新 Agent 统计"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.total_trades += trades
            if agent.total_trades > 0:
                agent.win_rate = (agent.win_rate * (agent.total_trades - trades) + wins) / agent.total_trades
    
    def discover(
        self,
        specialty: str = None,
        min_reputation: float = None,
        min_trades: int = None,
        online_only: bool = True,
    ) -> List[AgentProfile]:
        """发现 Agent"""
        results = []
        
        for agent in self.agents.values():
            if online_only and not agent.online:
                continue
            if specialty and specialty not in agent.specialties:
                continue
            if min_reputation and agent.reputation < min_reputation:
                continue
            if min_trades and agent.total_trades < min_trades:
                continue
            results.append(agent)
        
        return sorted(results, key=lambda a: a.reputation, reverse=True)
    
    async def send(self, msg: AgentMessage) -> str:
        """发送消息"""
        self.messages[msg.message_id] = msg
        
        if msg.to_agent == "*":
            # 广播
            for agent_id in self.agents:
                if agent_id != msg.from_agent:
                    self.inboxes[agent_id].append(msg)
                    await self._deliver(agent_id, msg)
        else:
            # 点对点
            if msg.to_agent in self.inboxes:
                self.inboxes[msg.to_agent].append(msg)
                await self._deliver(msg.to_agent, msg)
        
        return msg.message_id
    
    async def _deliver(self, agent_id: str, msg: AgentMessage):
        """投递消息到 WebSocket"""
        if agent_id in self._connections:
            ws = self._connections[agent_id]
            try:
                await ws.send_json(msg.to_dict())
            except:
                pass
        
        # 触发处理器
        if agent_id in self._handlers:
            handler = self._handlers[agent_id].get(msg.msg_type)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(msg)
                    else:
                        handler(msg)
                except:
                    pass
    
    def get_inbox(self, agent_id: str, limit: int = 50, unread_only: bool = False) -> List[AgentMessage]:
        """获取收件箱"""
        messages = self.inboxes.get(agent_id, [])
        return messages[-limit:]
    
    def on_message(self, agent_id: str, msg_type: MessageType, handler: Callable):
        """注册消息处理器"""
        if agent_id not in self._handlers:
            self._handlers[agent_id] = {}
        self._handlers[agent_id][msg_type] = handler
    
    # ==========================================
    # 便捷方法
    # ==========================================
    
    async def ping(self, from_agent: str, to_agent: str) -> str:
        """Ping 另一个 Agent"""
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.PING,
            from_agent=from_agent,
            to_agent=to_agent,
            payload={},
        )
        return await self.send(msg)
    
    async def announce(self, agent_id: str, content: str):
        """广播公告"""
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.ANNOUNCE,
            from_agent=agent_id,
            to_agent="*",
            payload={"content": content},
        )
        return await self.send(msg)
    
    async def send_trade_request(
        self,
        from_agent: str,
        to_agent: str,
        trade: dict,  # {asset, side, size, price?}
    ) -> str:
        """发送交易请求"""
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.TRADE_REQUEST,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=trade,
        )
        return await self.send(msg)
    
    async def accept_trade(self, from_agent: str, request_id: str) -> str:
        """接受交易"""
        original = self.messages.get(request_id)
        if not original:
            raise ValueError("Trade request not found")
        
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.TRADE_ACCEPT,
            from_agent=from_agent,
            to_agent=original.from_agent,
            payload={"request_id": request_id},
            reply_to=request_id,
        )
        return await self.send(msg)
    
    async def share_signal(
        self,
        from_agent: str,
        signal: dict,  # {asset, direction, confidence, reason, target_price?}
        to_agent: str = "*",  # 默认广播
    ) -> str:
        """分享交易信号"""
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.SIGNAL_SHARE,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=signal,
        )
        return await self.send(msg)
    
    async def offer_strategy(
        self,
        from_agent: str,
        strategy: dict,  # {name, description, backtest_results, price_usdc}
    ) -> str:
        """出售策略"""
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.STRATEGY_OFFER,
            from_agent=from_agent,
            to_agent="*",
            payload=strategy,
        )
        return await self.send(msg)
    
    # ==========================================
    # 联盟
    # ==========================================
    
    def create_alliance(self, leader_id: str, name: str) -> Alliance:
        """创建联盟"""
        alliance = Alliance(
            alliance_id=f"ally_{uuid.uuid4().hex[:8]}",
            name=name,
            members=[leader_id],
            leader_id=leader_id,
        )
        self.alliances[alliance.alliance_id] = alliance
        return alliance
    
    async def invite_to_alliance(self, alliance_id: str, inviter_id: str, invitee_id: str) -> str:
        """邀请加入联盟"""
        alliance = self.alliances.get(alliance_id)
        if not alliance:
            raise ValueError("Alliance not found")
        if inviter_id not in alliance.members:
            raise ValueError("Inviter not in alliance")
        
        msg = AgentMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=MessageType.ALLIANCE_INVITE,
            from_agent=inviter_id,
            to_agent=invitee_id,
            payload={
                "alliance_id": alliance_id,
                "alliance_name": alliance.name,
                "profit_share": alliance.profit_share,
            },
        )
        return await self.send(msg)
    
    def join_alliance(self, alliance_id: str, agent_id: str):
        """加入联盟"""
        alliance = self.alliances.get(alliance_id)
        if alliance and agent_id not in alliance.members:
            alliance.members.append(agent_id)
    
    def get_alliance_members(self, alliance_id: str) -> List[AgentProfile]:
        """获取联盟成员"""
        alliance = self.alliances.get(alliance_id)
        if not alliance:
            return []
        return [self.agents[m] for m in alliance.members if m in self.agents]


# 单例
agent_comm = AgentCommunicator()
