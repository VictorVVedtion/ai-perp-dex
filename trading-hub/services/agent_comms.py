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

    # === A2A 标准化协议 (v2) ===
    SIGNAL_PROPOSAL = "signal_proposal"          # 结构化信号提案
    TRADE_ACCEPTANCE = "trade_acceptance"         # 结构化交易接受
    STRATEGY_UPDATE = "strategy_update"           # 策略状态更新
    RISK_ALERT = "risk_alert"                     # 风险警报
    POSITION_UPDATE = "position_update"           # 持仓变动通知
    COORDINATION_REQUEST = "coordination_request" # 协调请求（联合建仓等）


# === A2A 标准化消息 Schema ===
# 为 Agent 间自动化通信定义严格的 JSON 结构

A2A_SCHEMAS = {
    "signal_proposal": {
        "required": ["asset", "direction", "confidence", "timeframe"],
        "optional": ["target_price", "stop_loss", "reasoning", "expires_in_seconds"],
        "example": {
            "asset": "BTC-PERP",
            "direction": "long",
            "confidence": 0.85,
            "timeframe": "4h",
            "target_price": 105000,
            "stop_loss": 98000,
            "reasoning": "Breakout above 102k resistance with volume confirmation",
            "expires_in_seconds": 3600,
        },
    },
    "trade_acceptance": {
        "required": ["proposal_message_id", "accepted", "size_usdc"],
        "optional": ["counter_price", "counter_size", "message"],
        "example": {
            "proposal_message_id": "msg_abc123",
            "accepted": True,
            "size_usdc": 500,
            "counter_price": None,
            "message": "Agreed, opening matching position",
        },
    },
    "strategy_update": {
        "required": ["strategy_name", "status"],
        "optional": ["markets", "performance", "params", "message"],
        "example": {
            "strategy_name": "momentum_v2",
            "status": "active",
            "markets": ["BTC-PERP", "ETH-PERP"],
            "performance": {"win_rate": 0.62, "sharpe": 1.4, "max_drawdown": -0.08},
            "params": {"lookback": 20, "threshold": 0.5},
        },
    },
    "risk_alert": {
        "required": ["alert_type", "severity", "asset"],
        "optional": ["details", "recommended_action", "expires_in_seconds"],
        "example": {
            "alert_type": "liquidation_warning",
            "severity": "high",
            "asset": "ETH-PERP",
            "details": "Position approaching liquidation price at 2x leverage",
            "recommended_action": "reduce_position",
        },
    },
    "position_update": {
        "required": ["asset", "action", "side"],
        "optional": ["size_usdc", "entry_price", "pnl", "leverage", "position_id"],
        "example": {
            "asset": "SOL-PERP",
            "action": "opened",
            "side": "long",
            "size_usdc": 200,
            "entry_price": 145.5,
            "leverage": 3,
            "position_id": "pos_abc123",
        },
    },
    "coordination_request": {
        "required": ["request_type", "asset", "proposed_side"],
        "optional": ["proposed_size", "proposed_leverage", "deadline_seconds", "message"],
        "example": {
            "request_type": "joint_position",
            "asset": "BTC-PERP",
            "proposed_side": "long",
            "proposed_size": 1000,
            "proposed_leverage": 2,
            "deadline_seconds": 300,
            "message": "Coordinated entry at support level",
        },
    },
}


def validate_a2a_payload(msg_type: str, payload: dict) -> tuple[bool, str]:
    """Validate A2A message payload against its schema.

    Returns (is_valid, error_message).
    """
    schema = A2A_SCHEMAS.get(msg_type)
    if not schema:
        return True, ""  # Non-schema messages pass through

    # Check required fields
    missing = [f for f in schema["required"] if f not in payload]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    # Check no unknown fields
    all_fields = set(schema["required"]) | set(schema.get("optional", []))
    unknown = [f for f in payload if f not in all_fields]
    if unknown:
        return False, f"Unknown fields: {', '.join(unknown)}"

    return True, ""


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

    def restore_from_store(self, agents_data: list) -> int:
        """从 Redis store 恢复 agent profiles（服务器重启后调用）

        Args:
            agents_data: store.list_agents() 返回的 Agent dataclass 列表

        Returns:
            恢复的 agent 数量
        """
        restored = 0
        for agent in agents_data:
            if agent.agent_id in self.agents:
                continue  # 已在内存中，跳过

            # 判断 online 状态: status == "active" 视为在线
            status_val = getattr(agent, 'status', None)
            online = False
            if status_val is not None:
                # AgentStatus enum 或 string
                s = status_val.value if hasattr(status_val, 'value') else str(status_val)
                online = s == "active"

            profile = AgentProfile(
                agent_id=agent.agent_id,
                name=getattr(agent, 'display_name', None) or agent.agent_id,
                description=getattr(agent, 'bio', '') or '',
                specialties=["trading"],
                reputation=getattr(agent, 'reputation_score', 0.5),
                total_trades=getattr(agent, 'total_trades', 0),
                win_rate=0.0,  # Redis 不存 win_rate，用默认值
                online=online,
            )
            self.agents[agent.agent_id] = profile
            self.inboxes[agent.agent_id] = []
            restored += 1
        return restored
    
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
        # --- 增强参数 ---
        min_win_rate: float = None,
        max_risk_score: float = None,
        asset: str = None,
        sort_by: str = "reputation",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 50,
    ) -> tuple:
        """发现 Agent（增强版：过滤 + 排序 + 分页）

        Returns:
            (agents_page, total_count) 分页后的结果 + 总数
        """
        results = []

        for agent in self.agents.values():
            if online_only and not agent.online:
                continue
            if specialty and specialty not in agent.specialties:
                continue
            if min_reputation is not None and agent.reputation < min_reputation:
                continue
            if min_trades is not None and agent.total_trades < min_trades:
                continue
            if min_win_rate is not None and agent.win_rate < min_win_rate:
                continue
            if asset and asset.upper().replace("-PERP", "") not in [
                s.upper().replace("-PERP", "") for s in agent.specialties
            ]:
                continue
            results.append(agent)

        # 排序
        sort_keys = {
            "reputation": lambda a: a.reputation,
            "win_rate": lambda a: a.win_rate,
            "total_pnl": lambda a: getattr(a, "total_pnl", 0),
            "risk_score": lambda a: getattr(a, "risk_score", 0),
            "total_trades": lambda a: a.total_trades,
            "created_at": lambda a: getattr(a, "last_seen", datetime.min),
        }
        key_fn = sort_keys.get(sort_by, sort_keys["reputation"])
        results.sort(key=key_fn, reverse=(sort_order == "desc"))

        total = len(results)
        return results[offset:offset + limit], total
    
    async def send(self, msg: AgentMessage) -> str:
        """发送消息"""
        self.messages[msg.message_id] = msg

        if msg.to_agent == "*":
            # 广播
            for agent_id in self.agents:
                if agent_id != msg.from_agent:
                    if agent_id not in self.inboxes:
                        self.inboxes[agent_id] = []
                    self.inboxes[agent_id].append(msg)
                    await self._deliver(agent_id, msg)
        else:
            # 点对点 — 兜底: 收件人不在内存中也创建 inbox，防止消息静默丢弃
            if msg.to_agent not in self.inboxes:
                self.inboxes[msg.to_agent] = []
            self.inboxes[msg.to_agent].append(msg)
            await self._deliver(msg.to_agent, msg)

        return msg.message_id
    
    async def _deliver(self, agent_id: str, msg: AgentMessage):
        """投递消息到 WebSocket"""
        if agent_id in self._connections:
            ws = self._connections[agent_id]
            try:
                await ws.send_json(msg.to_dict())
            except Exception as e:
                logger.warning(f"Failed to send message to agent {agent_id}: {e}")
        
        # 触发处理器
        if agent_id in self._handlers:
            handler = self._handlers[agent_id].get(msg.msg_type)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(msg)
                    else:
                        handler(msg)
                except Exception as e:
                    logger.error(f"Message handler error for {agent_id}: {e}")
    
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


# ==========================================
# Database-backed Chat for UI persistence
# ==========================================

from db.database import get_connection

class AgentChatDB:
    """
    Database-backed chat storage for UI.
    Complements the in-memory AgentCommunicator with persistence.
    """
    
    def __init__(self):
        self._ensure_table()
    
    def _ensure_table(self):
        """Ensure chat table exists"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_chat_messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                sender_name TEXT,
                channel TEXT DEFAULT 'public',
                message_type TEXT DEFAULT 'thought',
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def save_message(
        self,
        sender_id: str,
        content: str,
        message_type: str = "thought",
        channel: str = "public",
        metadata: dict = None,
    ) -> str:
        """Save a chat message to database"""
        import json
        msg_id = f"chat_{uuid.uuid4().hex[:12]}"
        
        # Get sender name from agents table
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM agents WHERE agent_id = ?", (sender_id,))
        row = cursor.fetchone()
        sender_name = row['display_name'] if row else sender_id
        
        cursor.execute("""
            INSERT INTO agent_chat_messages (id, sender_id, sender_name, channel, message_type, content, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, sender_id, sender_name, channel, message_type, content, json.dumps(metadata or {})))
        conn.commit()
        conn.close()
        
        return msg_id
    
    def get_messages(self, channel: str = "public", limit: int = 50) -> list:
        """Get recent messages from a channel"""
        import json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM agent_chat_messages
            WHERE channel = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (channel, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row['id'],
                'sender_id': row['sender_id'],
                'sender_name': row['sender_name'],
                'channel': row['channel'],
                'message_type': row['message_type'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'created_at': row['created_at'],
            })
        conn.close()
        
        return list(reversed(messages))  # Oldest first
    
    def get_thoughts_stream(self, limit: int = 20) -> list:
        """Get recent thoughts for the live feed"""
        import json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM agent_chat_messages
            WHERE message_type = 'thought' AND channel = 'public'
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        thoughts = []
        for row in cursor.fetchall():
            thoughts.append({
                'id': row['id'],
                'agent_id': row['sender_id'],
                'agent_name': row['sender_name'] or row['sender_id'],
                'thought': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'timestamp': row['created_at'],
            })
        conn.close()
        
        return list(reversed(thoughts))  # Oldest first


# Database chat singleton
chat_db = AgentChatDB()
