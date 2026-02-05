"""
Agent 鉴权中间件

提供 API Key 验证和 Agent 身份校验
"""
import hashlib
import secrets
from typing import Optional, Dict
from fastapi import Header, HTTPException, Depends
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentAuth:
    """Agent 认证信息"""
    agent_id: str
    api_key: str
    created_at: datetime
    is_active: bool = True

class AuthManager:
    """
    认证管理器
    
    生产环境应该使用数据库存储
    """
    def __init__(self):
        self._keys: Dict[str, AgentAuth] = {}  # api_key -> AgentAuth
        self._agent_keys: Dict[str, str] = {}  # agent_id -> api_key
    
    def generate_key(self, agent_id: str) -> str:
        """为 Agent 生成 API Key"""
        # 生成安全的随机 key
        api_key = f"ak_{secrets.token_hex(24)}"
        
        # 存储
        auth = AgentAuth(
            agent_id=agent_id,
            api_key=api_key,
            created_at=datetime.now(),
        )
        self._keys[api_key] = auth
        self._agent_keys[agent_id] = api_key
        
        return api_key
    
    def verify_key(self, api_key: str) -> Optional[AgentAuth]:
        """验证 API Key"""
        auth = self._keys.get(api_key)
        if auth and auth.is_active:
            return auth
        return None
    
    def get_agent_key(self, agent_id: str) -> Optional[str]:
        """获取 Agent 的 API Key"""
        return self._agent_keys.get(agent_id)
    
    def revoke_key(self, agent_id: str) -> bool:
        """撤销 Agent 的 Key"""
        api_key = self._agent_keys.get(agent_id)
        if api_key and api_key in self._keys:
            self._keys[api_key].is_active = False
            return True
        return False

# 全局实例
auth_manager = AuthManager()

async def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[str]:
    """从 Header 获取 API Key"""
    return x_api_key

async def verify_agent(
    agent_id: str,
    api_key: Optional[str] = Depends(get_api_key),
) -> str:
    """
    验证 Agent 身份
    
    用法:
        @app.post("/some-endpoint")
        async def endpoint(agent_id: str = Depends(verify_agent)):
            # agent_id 已验证
            ...
    """
    # 开发模式: 如果没有 API key，允许通过 (方便测试)
    # 生产环境应该移除这个
    if not api_key:
        return agent_id
    
    auth = auth_manager.verify_key(api_key)
    if not auth:
        raise HTTPException(401, "Invalid API key")
    
    if auth.agent_id != agent_id:
        raise HTTPException(403, f"API key does not belong to agent {agent_id}")
    
    return agent_id

async def require_auth(
    api_key: Optional[str] = Depends(get_api_key),
) -> AgentAuth:
    """
    要求认证 (不指定 agent_id)
    
    用法:
        @app.get("/my-profile")
        async def get_profile(auth: AgentAuth = Depends(require_auth)):
            return {"agent_id": auth.agent_id}
    """
    if not api_key:
        raise HTTPException(401, "API key required")
    
    auth = auth_manager.verify_key(api_key)
    if not auth:
        raise HTTPException(401, "Invalid API key")
    
    return auth
