"""
Trading Hub - Agent 鉴权中间件

支持两种认证方式:
1. API Key (X-API-Key header) - 简单快速
2. JWT Bearer Token - 更安全，适合生产环境

使用方式:
    from middleware.auth import verify_agent, verify_agent_owns_resource
    
    @app.post("/intents")
    async def create_intent(
        request: IntentRequest,
        auth: AgentAuth = Depends(verify_agent)
    ):
        # auth.agent_id 已验证
        ...
"""

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import secrets
import hmac
import json
import base64


class AuthError(HTTPException):
    """认证错误"""
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(HTTPException):
    """权限错误"""
    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=403, detail=detail)


@dataclass
class AgentAuth:
    """认证结果"""
    agent_id: str
    api_key_id: Optional[str] = None
    scopes: List[str] = field(default_factory=lambda: ["read", "write"])
    authenticated_at: datetime = field(default_factory=datetime.now)


@dataclass  
class APIKey:
    """API Key 记录"""
    key_id: str
    agent_id: str
    key_hash: str  # 只存 hash，不存明文
    name: str = "default"
    scopes: List[str] = field(default_factory=lambda: ["read", "write"])
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "scopes": self.scopes,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
        }


class APIKeyStore:
    """API Key 存储 (内存版)"""
    
    def __init__(self):
        self.keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._agent_keys: Dict[str, List[str]] = {}  # agent_id -> [key_ids]
        self._hash_to_key: Dict[str, str] = {}  # key_hash -> key_id
        
    def _hash_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def create_key(
        self, 
        agent_id: str, 
        name: str = "default",
        scopes: List[str] = None,
        expires_in_days: int = None
    ) -> tuple:
        """创建新 API Key"""
        agent_prefix = agent_id.replace("agent_", "")[:4]
        random_part = secrets.token_urlsafe(24)
        raw_key = f"th_{agent_prefix}_{random_part}"
        
        key_id = f"key_{secrets.token_hex(8)}"
        key_hash = self._hash_key(raw_key)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            key_id=key_id,
            agent_id=agent_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes or ["read", "write"],
            expires_at=expires_at,
        )
        
        self.keys[key_id] = api_key
        self._hash_to_key[key_hash] = key_id
        
        if agent_id not in self._agent_keys:
            self._agent_keys[agent_id] = []
        self._agent_keys[agent_id].append(key_id)
        
        return raw_key, api_key
    
    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """验证 API key"""
        key_hash = self._hash_key(raw_key)
        key_id = self._hash_to_key.get(key_hash)
        if not key_id:
            return None
        
        api_key = self.keys.get(key_id)
        if not api_key:
            return None
            
        if api_key.expires_at and datetime.now() > api_key.expires_at:
            return None
        if not api_key.is_active:
            return None
        
        api_key.last_used = datetime.now()
        return api_key
    
    def get_agent_keys(self, agent_id: str) -> List[APIKey]:
        """获取 Agent 的所有 API keys"""
        key_ids = self._agent_keys.get(agent_id, [])
        return [self.keys[kid] for kid in key_ids if kid in self.keys]
    
    def revoke_key(self, key_id: str, agent_id: str) -> bool:
        """撤销 API key"""
        api_key = self.keys.get(key_id)
        if not api_key or api_key.agent_id != agent_id:
            return False
        api_key.is_active = False
        return True
    
    def delete_key(self, key_id: str, agent_id: str) -> bool:
        """删除 API key"""
        api_key = self.keys.get(key_id)
        if not api_key or api_key.agent_id != agent_id:
            return False
        del self.keys[key_id]
        if api_key.key_hash in self._hash_to_key:
            del self._hash_to_key[api_key.key_hash]
        if agent_id in self._agent_keys:
            self._agent_keys[agent_id].remove(key_id)
        return True


class RedisAPIKeyStore(APIKeyStore):
    """Redis 持久化版 API Key 存储"""
    
    KEY_PREFIX = "perpdex:api_keys:"
    
    def __init__(self, redis_client=None):
        super().__init__()
        self._redis = redis_client
        
    @property
    def redis(self):
        if self._redis is None:
            import redis
            import os
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis.from_url(redis_url, decode_responses=True)
        return self._redis
    
    def _key(self, *parts) -> str:
        return self.KEY_PREFIX + ":".join(parts)
    
    def create_key(self, agent_id: str, name: str = "default", 
                   scopes: List[str] = None, expires_in_days: int = None) -> tuple:
        """创建新 API Key (持久化到 Redis)"""
        raw_key, api_key = super().create_key(agent_id, name, scopes, expires_in_days)
        
        # 持久化到 Redis
        key_data = {
            "key_id": api_key.key_id,
            "agent_id": api_key.agent_id,
            "key_hash": api_key.key_hash,
            "name": api_key.name,
            "scopes": ",".join(api_key.scopes),
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else "",
            "is_active": "1" if api_key.is_active else "0",
        }
        self.redis.hset(self._key("keys"), api_key.key_id, json.dumps(key_data))
        self.redis.hset(self._key("hashes"), api_key.key_hash, api_key.key_id)
        self.redis.sadd(self._key("agent", agent_id), api_key.key_id)
        
        return raw_key, api_key
    
    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """验证 API key (从 Redis 查询)"""
        key_hash = self._hash_key(raw_key)
        
        # 先查内存缓存
        if key_hash in self._hash_to_key:
            return super().validate_key(raw_key)
        
        # 从 Redis 查询
        key_id = self.redis.hget(self._key("hashes"), key_hash)
        if not key_id:
            return None
        
        key_data = self.redis.hget(self._key("keys"), key_id)
        if not key_data:
            return None
        
        data = json.loads(key_data)
        
        # 检查过期
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now() > expires_at:
                return None
        
        # 检查激活
        if data.get("is_active") == "0":
            return None
        
        # 构建 APIKey 对象并缓存
        api_key = APIKey(
            key_id=data["key_id"],
            agent_id=data["agent_id"],
            key_hash=data["key_hash"],
            name=data["name"],
            scopes=data["scopes"].split(",") if data["scopes"] else ["read", "write"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            is_active=data.get("is_active") != "0",
        )
        
        # 缓存到内存
        self.keys[key_id] = api_key
        self._hash_to_key[key_hash] = key_id
        
        api_key.last_used = datetime.now()
        return api_key
    
    def get_agent_keys(self, agent_id: str) -> List[APIKey]:
        """获取 Agent 的所有 API keys"""
        key_ids = self.redis.smembers(self._key("agent", agent_id))
        keys = []
        for key_id in key_ids:
            key_data = self.redis.hget(self._key("keys"), key_id)
            if key_data:
                data = json.loads(key_data)
                keys.append(APIKey(
                    key_id=data["key_id"],
                    agent_id=data["agent_id"],
                    key_hash=data["key_hash"],
                    name=data["name"],
                    scopes=data["scopes"].split(",") if data["scopes"] else ["read", "write"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
                    is_active=data.get("is_active") != "0",
                ))
        return keys
    
    def revoke_key(self, key_id: str, agent_id: str) -> bool:
        """撤销 API key"""
        key_data = self.redis.hget(self._key("keys"), key_id)
        if not key_data:
            return False
        
        data = json.loads(key_data)
        if data["agent_id"] != agent_id:
            return False
        
        data["is_active"] = "0"
        self.redis.hset(self._key("keys"), key_id, json.dumps(data))
        
        # 清除内存缓存
        if key_id in self.keys:
            del self.keys[key_id]
        if data["key_hash"] in self._hash_to_key:
            del self._hash_to_key[data["key_hash"]]
        
        return True


# 根据环境选择 API Key 存储
import os
_use_redis = os.environ.get("USE_REDIS", "true").lower() == "true"

if _use_redis:
    try:
        api_key_store = RedisAPIKeyStore()
        # 测试连接
        api_key_store.redis.ping()
    except Exception as e:
        print(f"⚠️ Redis API key store failed, using memory: {e}")
        api_key_store = APIKeyStore()
else:
    api_key_store = APIKeyStore()


# JWT 相关配置 (自包含实现，无需外部库)
JWT_SECRET = secrets.token_hex(32)  # 生产环境从环境变量读取
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def create_jwt_token(agent_id: str, scopes: List[str] = None) -> str:
    """创建 JWT token (自包含实现)"""
    now = datetime.utcnow()
    payload = {
        "sub": agent_id,
        "scopes": scopes or ["read", "write"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()),
    }
    
    # 简单 JWT 实现
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": JWT_ALGORITHM, "typ": "JWT"}).encode()
    ).rstrip(b'=').decode()
    
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b'=').decode()
    
    message = f"{header}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode(), 
        message.encode(), 
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
    
    return f"{message}.{signature_b64}"


def verify_jwt_token(token: str) -> Optional[dict]:
    """验证 JWT token"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, signature_b64 = parts
        
        # 验证签名
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b'=').decode()
        
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
        
        # 解码 payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        # 检查过期
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        
        return payload
        
    except Exception:
        return None


# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_agent(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AgentAuth:
    """
    验证 Agent 身份
    
    支持两种方式:
    1. Header: X-API-Key: th_xxxx_xxxxxxxxx
    2. Header: Authorization: Bearer <jwt_token>
    
    Usage:
        @app.post("/intents")
        async def create_intent(auth: AgentAuth = Depends(verify_agent)):
            agent_id = auth.agent_id
    """
    
    # 方式 1: API Key
    if x_api_key:
        api_key = api_key_store.validate_key(x_api_key)
        if api_key:
            return AgentAuth(
                agent_id=api_key.agent_id,
                api_key_id=api_key.key_id,
                scopes=api_key.scopes,
            )
        raise AuthError("Invalid API key")
    
    # 方式 2: JWT Bearer Token
    if authorization and authorization.credentials:
        payload = verify_jwt_token(authorization.credentials)
        if payload:
            return AgentAuth(
                agent_id=payload["sub"],
                scopes=payload.get("scopes", []),
            )
        raise AuthError("Invalid or expired token")
    
    # 没有提供任何认证信息
    raise AuthError("Authentication required. Provide X-API-Key header or Bearer token.")


async def verify_agent_optional(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[AgentAuth]:
    """
    可选的 Agent 验证
    
    如果提供了认证信息则验证，否则返回 None
    适用于可选认证的端点
    """
    if not x_api_key and not (authorization and authorization.credentials):
        return None
    
    return await verify_agent(request, x_api_key, authorization)


def verify_agent_owns_resource(
    auth: AgentAuth,
    resource_agent_id: str,
    resource_name: str = "resource"
) -> None:
    """
    验证 Agent 是否拥有资源
    
    Usage:
        @app.delete("/intents/{intent_id}")
        async def cancel_intent(
            intent_id: str,
            auth: AgentAuth = Depends(verify_agent)
        ):
            intent = store.get_intent(intent_id)
            verify_agent_owns_resource(auth, intent.agent_id, "intent")
    """
    if auth.agent_id != resource_agent_id:
        raise ForbiddenError(f"You don't own this {resource_name}")


def require_scope(required_scope: str):
    """
    装饰器: 要求特定权限
    
    Usage:
        @app.post("/admin/action")
        @require_scope("admin")
        async def admin_action(auth: AgentAuth = Depends(verify_agent)):
            ...
    """
    def decorator(func):
        async def wrapper(*args, auth: AgentAuth = None, **kwargs):
            if auth and required_scope not in auth.scopes:
                raise ForbiddenError(f"Scope '{required_scope}' required")
            return await func(*args, auth=auth, **kwargs)
        return wrapper
    return decorator
