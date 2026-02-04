"""
Trading Hub - 内存数据库 (MVP)
生产环境换成 PostgreSQL/Redis
"""

from typing import Optional, List, Dict
from datetime import datetime, timedelta
import threading

import sys
sys.path.append('..')
from api.models import Agent, TradingIntent, Match, AgentStatus, IntentStatus, IntentType

class Store:
    """简单的内存存储"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.intents: Dict[str, TradingIntent] = {}
        self.matches: Dict[str, Match] = {}
        
        # 索引
        self.wallet_to_agent: Dict[str, str] = {}
        self.twitter_to_agent: Dict[str, str] = {}
        self.agent_intents: Dict[str, List[str]] = {}  # agent_id -> intent_ids
        
        self._lock = threading.Lock()
    
    # === Agent 操作 ===
    
    def create_agent(self, wallet_address: str, **kwargs) -> Agent:
        """创建 Agent"""
        with self._lock:
            # 检查钱包是否已注册
            if wallet_address in self.wallet_to_agent:
                existing_id = self.wallet_to_agent[wallet_address]
                return self.agents[existing_id]
            
            agent_id = f"agent_{len(self.agents) + 1:04d}"
            agent = Agent(
                agent_id=agent_id,
                wallet_address=wallet_address,
                status=AgentStatus.ACTIVE,  # 钱包注册直接激活
                **kwargs
            )
            
            self.agents[agent_id] = agent
            self.wallet_to_agent[wallet_address] = agent_id
            self.agent_intents[agent_id] = []
            
            return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)
    
    def get_agent_by_wallet(self, wallet: str) -> Optional[Agent]:
        agent_id = self.wallet_to_agent.get(wallet)
        return self.agents.get(agent_id) if agent_id else None
    
    def update_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return None
            
            for key, value in kwargs.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            
            return agent
    
    def list_agents(self, limit: int = 50, offset: int = 0) -> List[Agent]:
        agents = list(self.agents.values())
        return agents[offset:offset + limit]
    
    def get_leaderboard(self, limit: int = 20) -> List[Agent]:
        """获取声誉排行榜"""
        agents = list(self.agents.values())
        agents.sort(key=lambda a: a.reputation_score, reverse=True)
        return agents[:limit]
    
    # === Intent 操作 ===
    
    def create_intent(self, agent_id: str, **kwargs) -> Optional[TradingIntent]:
        """创建 Intent"""
        with self._lock:
            if agent_id not in self.agents:
                return None
            
            intent = TradingIntent(agent_id=agent_id, **kwargs)
            self.intents[intent.intent_id] = intent
            self.agent_intents[agent_id].append(intent.intent_id)
            
            return intent
    
    def get_intent(self, intent_id: str) -> Optional[TradingIntent]:
        return self.intents.get(intent_id)
    
    def update_intent(self, intent_id: str, **kwargs) -> Optional[TradingIntent]:
        with self._lock:
            intent = self.intents.get(intent_id)
            if not intent:
                return None
            
            for key, value in kwargs.items():
                if hasattr(intent, key):
                    setattr(intent, key, value)
            
            return intent
    
    def list_open_intents(self, asset: str = None, limit: int = 100) -> List[TradingIntent]:
        """获取所有开放的 Intent"""
        intents = [i for i in self.intents.values() if i.status == IntentStatus.OPEN]
        
        if asset:
            intents = [i for i in intents if i.asset == asset]
        
        # 按时间排序
        intents.sort(key=lambda i: i.created_at, reverse=True)
        return intents[:limit]
    
    def get_agent_intents(self, agent_id: str) -> List[TradingIntent]:
        """获取 Agent 的所有 Intent"""
        intent_ids = self.agent_intents.get(agent_id, [])
        return [self.intents[iid] for iid in intent_ids if iid in self.intents]
    
    def find_matching_intents(self, intent: TradingIntent) -> List[TradingIntent]:
        """找到可以匹配的 Intent"""
        matches = []
        for other in self.intents.values():
            if intent.is_compatible_with(other):
                matches.append(other)
        
        # 按声誉排序
        matches.sort(
            key=lambda i: self.agents.get(i.agent_id, Agent("", "")).reputation_score,
            reverse=True
        )
        return matches
    
    # === Match 操作 ===
    
    def create_match(self, intent_a: TradingIntent, intent_b: TradingIntent, price: float) -> Match:
        """创建匹配"""
        with self._lock:
            match = Match(
                intent_a_id=intent_a.intent_id,
                intent_b_id=intent_b.intent_id,
                agent_a_id=intent_a.agent_id,
                agent_b_id=intent_b.agent_id,
                asset=intent_a.asset,
                size_usdc=min(intent_a.size_usdc, intent_b.size_usdc),
                price=price,
            )
            
            self.matches[match.match_id] = match
            
            # 更新 Intent 状态
            intent_a.status = IntentStatus.MATCHED
            intent_a.matched_with = intent_b.intent_id
            intent_a.matched_at = datetime.now()
            
            intent_b.status = IntentStatus.MATCHED
            intent_b.matched_with = intent_a.intent_id
            intent_b.matched_at = datetime.now()
            
            return match
    
    def get_match(self, match_id: str) -> Optional[Match]:
        return self.matches.get(match_id)
    
    def list_recent_matches(self, limit: int = 50) -> List[Match]:
        matches = list(self.matches.values())
        matches.sort(key=lambda m: m.created_at, reverse=True)
        return matches[:limit]
    
    # === 统计 ===
    
    def get_stats(self) -> dict:
        return {
            "total_agents": len(self.agents),
            "active_agents": len([a for a in self.agents.values() if a.status == AgentStatus.ACTIVE]),
            "total_intents": len(self.intents),
            "open_intents": len([i for i in self.intents.values() if i.status == IntentStatus.OPEN]),
            "total_matches": len(self.matches),
            "total_volume": sum(m.size_usdc for m in self.matches.values()),
        }


# 全局存储实例
store = Store()
