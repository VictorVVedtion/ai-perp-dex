"""
Agent 鉴权中间件

提供 API Key 验证和 Agent 身份校验
"""
import hashlib
import secrets
import jwt
from typing import Optional, Dict
from fastapi import Header, HTTPException, Depends
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# 自定义异常
class AuthError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)

class ForbiddenError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)

@dataclass
class AgentAuth:
    """Agent 认证信息"""
    agent_id: str
    api_key: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

class APIKeyStore:
    """
    API Key 存储
    
    生产环境应该使用数据库
    """
    # JWT 配置
    JWT_SECRET = "your-secret-key-change-in-production"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_HOURS = 24
    
    def __init__(self):
        self._keys: Dict[str, AgentAuth] = {}  # api_key -> AgentAuth
        self._agent_keys: Dict[str, str] = {}  # agent_id -> api_key
    
    def generate_key(self, agent_id: str) -> str:
        """为 Agent 生成 API Key"""
        api_key = f"ak_{secrets.token_hex(24)}"
        
        auth = AgentAuth(
            agent_id=agent_id,
            api_key=api_key,
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
api_key_store = APIKeyStore()

def create_jwt_token(agent_id: str, expires_hours: int = 24) -> str:
    """创建 JWT token"""
    payload = {
        "agent_id": agent_id,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, APIKeyStore.JWT_SECRET, algorithm=APIKeyStore.JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[str]:
    """验证 JWT token，返回 agent_id"""
    try:
        payload = jwt.decode(token, APIKeyStore.JWT_SECRET, algorithms=[APIKeyStore.JWT_ALGORITHM])
        return payload.get("agent_id")
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError:
        return None

async def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """从 Header 获取 API Key 或 Bearer Token"""
    if x_api_key:
        return x_api_key
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None

async def verify_agent(
    agent_id: str,
    api_key: Optional[str] = Depends(get_api_key),
) -> str:
    """
    验证 Agent 身份 (严格模式)
    """
    # 开发模式: 允许无 key 访问
    if not api_key:
        return agent_id
    
    # 尝试 API Key
    auth = api_key_store.verify_key(api_key)
    if auth:
        if auth.agent_id != agent_id:
            raise ForbiddenError(f"API key does not belong to agent {agent_id}")
        return agent_id
    
    # 尝试 JWT
    jwt_agent_id = verify_jwt_token(api_key)
    if jwt_agent_id:
        if jwt_agent_id != agent_id:
            raise ForbiddenError(f"Token does not belong to agent {agent_id}")
        return agent_id
    
    raise AuthError("Invalid API key or token")

async def verify_agent_optional(
    api_key: Optional[str] = Depends(get_api_key),
) -> Optional[str]:
    """
    可选验证 - 返回 agent_id 或 None
    """
    if not api_key:
        return None
    
    auth = api_key_store.verify_key(api_key)
    if auth:
        return auth.agent_id
    
    jwt_agent_id = verify_jwt_token(api_key)
    if jwt_agent_id:
        return jwt_agent_id
    
    return None

async def verify_agent_owns_resource(
    agent_id: str,
    resource_owner_id: str,
    api_key: Optional[str] = Depends(get_api_key),
) -> bool:
    """
    验证 Agent 是否拥有资源
    """
    # 开发模式
    if not api_key:
        return agent_id == resource_owner_id
    
    verified_agent = await verify_agent(agent_id, api_key)
    return verified_agent == resource_owner_id

async def require_auth(
    api_key: Optional[str] = Depends(get_api_key),
) -> AgentAuth:
    """
    强制要求认证
    """
    if not api_key:
        raise AuthError("API key required")
    
    auth = api_key_store.verify_key(api_key)
    if auth:
        return auth
    
    jwt_agent_id = verify_jwt_token(api_key)
    if jwt_agent_id:
        # 为 JWT 创建临时 Auth 对象
        return AgentAuth(agent_id=jwt_agent_id, api_key="jwt")
    
    raise AuthError("Invalid API key or token")
