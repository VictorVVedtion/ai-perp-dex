"""
Trading Hub - Middleware

Agent 鉴权中间件
"""

from .auth import (
    # 核心函数
    verify_agent,
    verify_agent_optional,
    verify_agent_owns_resource,
    require_scope,
    
    # JWT
    create_jwt_token,
    verify_jwt_token,
    
    # 存储
    api_key_store,
    
    # 类型
    AgentAuth,
    APIKey,
    
    # 异常
    AuthError,
    ForbiddenError,
)

__all__ = [
    "verify_agent",
    "verify_agent_optional", 
    "verify_agent_owns_resource",
    "require_scope",
    "create_jwt_token",
    "verify_jwt_token",
    "api_key_store",
    "AgentAuth",
    "APIKey",
    "AuthError",
    "ForbiddenError",
]
