"""
Trading Hub - Redis 持久化存储

替换内存存储，数据持久化到 Redis
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict

import redis

from api.models import Agent, TradingIntent, Match, AgentStatus, IntentStatus, IntentType

logger = logging.getLogger(__name__)

# Redis 配置
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
KEY_PREFIX = "perpdex:"


def serialize_datetime(obj):
    """JSON 序列化 datetime"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def deserialize_datetime(d: dict) -> dict:
    """反序列化 datetime 字段"""
    datetime_fields = ['created_at', 'matched_at', 'expires_at', 'updated_at', 'settled_at']
    for field in datetime_fields:
        if field in d and d[field]:
            try:
                d[field] = datetime.fromisoformat(d[field])
            except (ValueError, TypeError):
                pass
    return d


class RedisStore:
    """Redis 持久化存储"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._connect()
        logger.info(f"RedisStore initialized: {self.redis_url}")
    
    def _connect(self):
        """连接 Redis"""
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._client.ping()
            logger.info("Redis connected successfully")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    @property
    def client(self) -> redis.Redis:
        if not self._client:
            self._connect()
        return self._client
    
    def _key(self, *parts) -> str:
        """生成 Redis key"""
        return KEY_PREFIX + ":".join(parts)
    
    # === Agent 操作 ===
    
    def create_agent(self, wallet_address: str, **kwargs) -> Agent:
        """创建 Agent"""
        # 检查钱包是否已注册
        existing_id = self.client.hget(self._key("wallet_to_agent"), wallet_address)
        if existing_id:
            return self.get_agent(existing_id)
        
        # 生成新 ID (原子操作)
        agent_num = self.client.incr(self._key("agent_counter"))
        agent_id = f"agent_{agent_num:04d}"
        
        agent = Agent(
            agent_id=agent_id,
            wallet_address=wallet_address,
            status=AgentStatus.ACTIVE,
            **kwargs
        )
        
        # 存储 Agent
        agent_data = self._agent_to_dict(agent)
        self.client.hset(self._key("agents"), agent_id, json.dumps(agent_data, default=serialize_datetime))
        
        # 索引
        self.client.hset(self._key("wallet_to_agent"), wallet_address, agent_id)
        
        logger.info(f"Agent created: {agent_id}")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取 Agent"""
        data = self.client.hget(self._key("agents"), agent_id)
        if not data:
            return None
        return self._dict_to_agent(json.loads(data))
    
    def get_agent_by_wallet(self, wallet: str) -> Optional[Agent]:
        """通过钱包获取 Agent"""
        agent_id = self.client.hget(self._key("wallet_to_agent"), wallet)
        return self.get_agent(agent_id) if agent_id else None
    
    def update_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """更新 Agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        # 保存更新
        agent_data = self._agent_to_dict(agent)
        self.client.hset(self._key("agents"), agent_id, json.dumps(agent_data, default=serialize_datetime))
        
        return agent
    
    def list_agents(self, limit: int = 50, offset: int = 0) -> List[Agent]:
        """列出所有 Agent"""
        all_data = self.client.hgetall(self._key("agents"))
        agents = [self._dict_to_agent(json.loads(v)) for v in all_data.values()]
        agents.sort(key=lambda a: a.created_at, reverse=True)
        return agents[offset:offset + limit]
    
    def get_leaderboard(self, limit: int = 20) -> List[Agent]:
        """获取声誉排行榜"""
        agents = self.list_agents(limit=1000)
        agents.sort(key=lambda a: a.reputation_score, reverse=True)
        return agents[:limit]
    
    def _agent_to_dict(self, agent: Agent) -> dict:
        """Agent 转字典"""
        return {
            "agent_id": agent.agent_id,
            "wallet_address": agent.wallet_address,
            "display_name": agent.display_name,
            "twitter_handle": agent.twitter_handle,
            "twitter_verified": agent.twitter_verified,
            "moltbook_handle": agent.moltbook_handle,
            "bio": agent.bio,
            "verified": agent.verified,
            "verification_nonce": agent.verification_nonce,
            "nonce_created_at": agent.nonce_created_at,
            "status": agent.status.value if isinstance(agent.status, AgentStatus) else agent.status,
            "reputation_score": agent.reputation_score,
            "total_trades": agent.total_trades,
            "total_volume": agent.total_volume,
            "pnl": agent.pnl,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        }
    
    def _dict_to_agent(self, d: dict) -> Agent:
        """字典转 Agent"""
        d = deserialize_datetime(d)
        if "status" in d and isinstance(d["status"], str):
            d["status"] = AgentStatus(d["status"])
        # 移除 Agent 不支持的字段
        valid_fields = {'agent_id', 'wallet_address', 'created_at', 'status',
                       'twitter_handle', 'twitter_verified', 'moltbook_handle',
                       'total_trades', 'total_volume', 'pnl', 'reputation_score',
                       'display_name', 'bio', 'verified', 'verification_nonce',
                       'nonce_created_at'}
        d = {k: v for k, v in d.items() if k in valid_fields}
        return Agent(**d)
    
    # === Intent 操作 ===
    
    def create_intent(self, agent_id: str, **kwargs) -> Optional[TradingIntent]:
        """创建 Intent"""
        if not self.get_agent(agent_id):
            return None
        
        intent = TradingIntent(agent_id=agent_id, **kwargs)
        
        # 存储
        intent_data = self._intent_to_dict(intent)
        self.client.hset(self._key("intents"), intent.intent_id, json.dumps(intent_data, default=serialize_datetime))
        
        # Agent 的 Intent 列表
        self.client.sadd(self._key("agent_intents", agent_id), intent.intent_id)
        
        # 开放 Intent 索引
        if intent.status == IntentStatus.OPEN:
            self.client.sadd(self._key("open_intents"), intent.intent_id)
            self.client.sadd(self._key("open_intents", intent.asset), intent.intent_id)
        
        logger.info(f"Intent created: {intent.intent_id}")
        return intent
    
    def get_intent(self, intent_id: str) -> Optional[TradingIntent]:
        """获取 Intent"""
        data = self.client.hget(self._key("intents"), intent_id)
        if not data:
            return None
        return self._dict_to_intent(json.loads(data))
    
    def update_intent(self, intent_id: str, **kwargs) -> Optional[TradingIntent]:
        """更新 Intent"""
        intent = self.get_intent(intent_id)
        if not intent:
            return None
        
        old_status = intent.status
        
        for key, value in kwargs.items():
            if hasattr(intent, key):
                setattr(intent, key, value)
        
        # 保存
        intent_data = self._intent_to_dict(intent)
        self.client.hset(self._key("intents"), intent_id, json.dumps(intent_data, default=serialize_datetime))
        
        # 更新索引
        if old_status == IntentStatus.OPEN and intent.status != IntentStatus.OPEN:
            self.client.srem(self._key("open_intents"), intent_id)
            self.client.srem(self._key("open_intents", intent.asset), intent_id)
        
        return intent
    
    def list_open_intents(self, asset: str = None, limit: int = 100) -> List[TradingIntent]:
        """获取开放的 Intent"""
        if asset:
            intent_ids = self.client.smembers(self._key("open_intents", asset))
        else:
            intent_ids = self.client.smembers(self._key("open_intents"))
        
        intents = []
        for iid in intent_ids:
            intent = self.get_intent(iid)
            if intent and intent.status == IntentStatus.OPEN:
                intents.append(intent)
        
        intents.sort(key=lambda i: i.created_at, reverse=True)
        return intents[:limit]
    
    def get_agent_intents(self, agent_id: str) -> List[TradingIntent]:
        """获取 Agent 的所有 Intent"""
        intent_ids = self.client.smembers(self._key("agent_intents", agent_id))
        intents = []
        for iid in intent_ids:
            intent = self.get_intent(iid)
            if intent:
                intents.append(intent)
        return intents
    
    def find_matching_intents(self, intent: TradingIntent) -> List[TradingIntent]:
        """找到可以匹配的 Intent"""
        open_intents = self.list_open_intents(asset=intent.asset)
        matches = [i for i in open_intents if intent.is_compatible_with(i)]
        
        # 按声誉排序
        def get_reputation(i):
            agent = self.get_agent(i.agent_id)
            return agent.reputation_score if agent else 0
        
        matches.sort(key=get_reputation, reverse=True)
        return matches
    
    def _intent_to_dict(self, intent: TradingIntent) -> dict:
        """Intent 转字典"""
        return {
            "intent_id": intent.intent_id,
            "agent_id": intent.agent_id,
            "intent_type": intent.intent_type.value if isinstance(intent.intent_type, IntentType) else intent.intent_type,
            "asset": intent.asset,
            "size_usdc": intent.size_usdc,
            "leverage": intent.leverage,
            "max_slippage": intent.max_slippage,
            "min_counterparty_reputation": getattr(intent, 'min_counterparty_reputation', 0.3),
            "status": intent.status.value if isinstance(intent.status, IntentStatus) else intent.status,
            "matched_with": intent.matched_with,
            "matched_at": intent.matched_at.isoformat() if intent.matched_at else None,
            "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
            "created_at": intent.created_at.isoformat() if intent.created_at else None,
            "execution_price": getattr(intent, 'execution_price', None),
        }
    
    def _dict_to_intent(self, d: dict) -> TradingIntent:
        """字典转 Intent"""
        d = deserialize_datetime(d)
        if "intent_type" in d and isinstance(d["intent_type"], str):
            d["intent_type"] = IntentType(d["intent_type"])
        if "status" in d and isinstance(d["status"], str):
            d["status"] = IntentStatus(d["status"])
        # 只保留 TradingIntent 支持的字段
        valid_fields = {'intent_id', 'agent_id', 'intent_type', 'asset', 'size_usdc', 
                       'leverage', 'max_slippage', 'min_counterparty_reputation', 'expires_at',
                       'status', 'created_at', 'matched_with', 'matched_at', 'execution_price'}
        d = {k: v for k, v in d.items() if k in valid_fields}
        return TradingIntent(**d)
    
    # === Match 操作 ===
    
    def create_match(self, intent_a: TradingIntent, intent_b: TradingIntent, price: float) -> Match:
        """创建匹配"""
        match = Match(
            intent_a_id=intent_a.intent_id,
            intent_b_id=intent_b.intent_id,
            agent_a_id=intent_a.agent_id,
            agent_b_id=intent_b.agent_id,
            asset=intent_a.asset,
            size_usdc=min(intent_a.size_usdc, intent_b.size_usdc),
            price=price,
        )
        
        # 存储
        match_data = self._match_to_dict(match)
        self.client.hset(self._key("matches"), match.match_id, json.dumps(match_data, default=serialize_datetime))
        
        # 最近 Match 列表 (ZSET，按时间排序)
        self.client.zadd(self._key("recent_matches"), {match.match_id: match.created_at.timestamp()})
        
        # 更新 Intent 状态
        self.update_intent(intent_a.intent_id, 
            status=IntentStatus.MATCHED,
            matched_with=intent_b.intent_id,
            matched_at=datetime.now()
        )
        self.update_intent(intent_b.intent_id,
            status=IntentStatus.MATCHED,
            matched_with=intent_a.intent_id,
            matched_at=datetime.now()
        )
        
        logger.info(f"Match created: {match.match_id}")
        return match
    
    def get_match(self, match_id: str) -> Optional[Match]:
        """获取 Match"""
        data = self.client.hget(self._key("matches"), match_id)
        if not data:
            return None
        return self._dict_to_match(json.loads(data))
    
    def list_recent_matches(self, limit: int = 50) -> List[Match]:
        """获取最近的 Match"""
        match_ids = self.client.zrevrange(self._key("recent_matches"), 0, limit - 1)
        matches = []
        for mid in match_ids:
            match = self.get_match(mid)
            if match:
                matches.append(match)
        return matches
    
    def _match_to_dict(self, match: Match) -> dict:
        """Match 转字典"""
        return {
            "match_id": match.match_id,
            "intent_a_id": match.intent_a_id,
            "intent_b_id": match.intent_b_id,
            "agent_a_id": match.agent_a_id,
            "agent_b_id": match.agent_b_id,
            "asset": match.asset,
            "size_usdc": match.size_usdc,
            "price": match.price,
            "created_at": match.created_at.isoformat() if match.created_at else None,
        }
    
    def _dict_to_match(self, d: dict) -> Match:
        """字典转 Match"""
        d = deserialize_datetime(d)
        return Match(**d)
    
    # === 统计 ===
    
    def get_stats(self) -> dict:
        """获取统计"""
        agents = self.list_agents(limit=10000)
        matches = self.list_recent_matches(limit=10000)
        open_count = self.client.scard(self._key("open_intents"))
        total_intents = self.client.hlen(self._key("intents"))
        
        return {
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if a.status == AgentStatus.ACTIVE]),
            "total_intents": total_intents,
            "open_intents": open_count,
            "total_matches": len(matches),
            "total_volume": sum(m.size_usdc for m in matches),
        }
    
    # === 额外数据存储 (balances, positions 等) ===
    
    def set_balance(self, agent_id: str, balance: float, locked: float = 0):
        """设置余额"""
        data = {"balance": balance, "locked": locked, "available": balance - locked}
        self.client.hset(self._key("balances"), agent_id, json.dumps(data))
    
    def get_balance(self, agent_id: str) -> dict:
        """获取余额"""
        data = self.client.hget(self._key("balances"), agent_id)
        if not data:
            return {"balance": 0, "locked": 0, "available": 0}
        return json.loads(data)
    
    def add_balance(self, agent_id: str, amount: float) -> dict:
        """增加余额"""
        bal = self.get_balance(agent_id)
        bal["balance"] += amount
        bal["available"] = bal["balance"] - bal["locked"]
        self.set_balance(agent_id, bal["balance"], bal["locked"])
        return bal
    
    def lock_balance(self, agent_id: str, amount: float) -> bool:
        """锁定余额"""
        bal = self.get_balance(agent_id)
        if bal["available"] < amount:
            return False
        bal["locked"] += amount
        bal["available"] = bal["balance"] - bal["locked"]
        self.set_balance(agent_id, bal["balance"], bal["locked"])
        return True
    
    def unlock_balance(self, agent_id: str, amount: float):
        """解锁余额"""
        bal = self.get_balance(agent_id)
        bal["locked"] = max(0, bal["locked"] - amount)
        bal["available"] = bal["balance"] - bal["locked"]
        self.set_balance(agent_id, bal["balance"], bal["locked"])
    
    def save_position(self, position_id: str, position_data: dict):
        """保存持仓"""
        self.client.hset(self._key("positions"), position_id, json.dumps(position_data, default=serialize_datetime))
        agent_id = position_data.get("agent_id")
        if agent_id:
            self.client.sadd(self._key("agent_positions", agent_id), position_id)
    
    def get_position(self, position_id: str) -> Optional[dict]:
        """获取持仓"""
        data = self.client.hget(self._key("positions"), position_id)
        return json.loads(data) if data else None
    
    def get_agent_positions(self, agent_id: str) -> List[dict]:
        """获取 Agent 的所有持仓"""
        position_ids = self.client.smembers(self._key("agent_positions", agent_id))
        positions = []
        for pid in position_ids:
            pos = self.get_position(pid)
            if pos:
                positions.append(pos)
        return positions
    
    def delete_position(self, position_id: str, agent_id: str = None):
        """删除持仓"""
        self.client.hdel(self._key("positions"), position_id)
        if agent_id:
            self.client.srem(self._key("agent_positions", agent_id), position_id)
    
    # === Signal Betting ===
    
    def save_signal(self, signal_id: str, signal_data: dict):
        """保存 Signal"""
        self.client.hset(self._key("signals"), signal_id, json.dumps(signal_data, default=serialize_datetime))
        if signal_data.get("status") == "ACTIVE":
            self.client.sadd(self._key("active_signals"), signal_id)
    
    def get_signal(self, signal_id: str) -> Optional[dict]:
        """获取 Signal"""
        data = self.client.hget(self._key("signals"), signal_id)
        return json.loads(data) if data else None
    
    def list_signals(self, status: str = None, limit: int = 100) -> List[dict]:
        """列出 Signals"""
        if status == "ACTIVE":
            signal_ids = self.client.smembers(self._key("active_signals"))
        else:
            signal_ids = self.client.hkeys(self._key("signals"))
        
        signals = []
        for sid in signal_ids:
            sig = self.get_signal(sid)
            if sig:
                if status is None or sig.get("status") == status:
                    signals.append(sig)
        return signals[:limit]
    
    def update_signal_status(self, signal_id: str, status: str):
        """更新 Signal 状态"""
        sig = self.get_signal(signal_id)
        if sig:
            sig["status"] = status
            self.save_signal(signal_id, sig)
            if status != "ACTIVE":
                self.client.srem(self._key("active_signals"), signal_id)
    
    # === API Keys ===
    
    def save_api_key(self, key_id: str, key_data: dict):
        """保存 API Key"""
        self.client.hset(self._key("api_keys"), key_id, json.dumps(key_data, default=serialize_datetime))
        if "hash" in key_data:
            self.client.hset(self._key("api_key_hashes"), key_data["hash"], key_id)
        if "agent_id" in key_data:
            self.client.sadd(self._key("agent_keys", key_data["agent_id"]), key_id)
    
    def get_api_key_by_hash(self, key_hash: str) -> Optional[dict]:
        """通过 hash 获取 API Key"""
        key_id = self.client.hget(self._key("api_key_hashes"), key_hash)
        if not key_id:
            return None
        data = self.client.hget(self._key("api_keys"), key_id)
        return json.loads(data) if data else None
    
    def get_agent_api_keys(self, agent_id: str) -> List[dict]:
        """获取 Agent 的所有 API Keys"""
        key_ids = self.client.smembers(self._key("agent_keys", agent_id))
        keys = []
        for kid in key_ids:
            data = self.client.hget(self._key("api_keys"), kid)
            if data:
                keys.append(json.loads(data))
        return keys


# 根据环境选择存储后端
def get_store():
    """获取存储实例"""
    use_redis = os.environ.get("USE_REDIS", "true").lower() == "true"
    
    if use_redis:
        try:
            return RedisStore()
        except Exception as e:
            logger.warning(f"Redis connection failed, falling back to memory store: {e}")
            from db.store import Store
            return Store()
    else:
        from db.store import Store
        return Store()


# 全局存储实例
store = get_store()
