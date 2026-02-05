"""
Rate Limiter - API 限流

防止:
1. Agent 滥用 API
2. DDoS 攻击
3. 恶意刷单
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import time


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_second: int = 10
    requests_per_minute: int = 300
    requests_per_hour: int = 5000
    
    # 不同端点的特殊限制
    order_per_second: int = 5
    order_per_minute: int = 100
    
    # 惩罚
    ban_threshold: int = 10  # 连续超限次数
    ban_duration_seconds: int = 300  # 封禁 5 分钟


@dataclass
class RateLimitState:
    """限流状态"""
    requests: list = field(default_factory=list)  # 请求时间戳列表
    violations: int = 0
    banned_until: Optional[datetime] = None
    
    def cleanup(self, window_seconds: int = 3600):
        """清理过期记录"""
        cutoff = time.time() - window_seconds
        self.requests = [t for t in self.requests if t > cutoff]


class RateLimiter:
    """
    分布式限流器
    
    用法:
        limiter = RateLimiter()
        
        # 检查是否允许
        allowed, info = await limiter.check("agent_001", "/intents")
        if not allowed:
            raise HTTPException(429, info["message"])
        
        # 记录请求
        limiter.record("agent_001", "/intents")
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.states: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        
        # 特殊端点
        self.order_endpoints = {"/intents", "/orders", "/signals"}
        
        print(f"🛡️ Rate Limiter started ({self.config.requests_per_second}/s)")
    
    async def check(self, agent_id: str, endpoint: str = "/") -> tuple[bool, dict]:
        """
        检查请求是否允许
        
        Returns:
            (allowed: bool, info: dict)
        """
        state = self.states[agent_id]
        now = datetime.now()
        current_time = time.time()
        
        # 检查是否被封禁
        if state.banned_until and now < state.banned_until:
            remaining = (state.banned_until - now).total_seconds()
            return False, {
                "message": f"Rate limited. Banned for {remaining:.0f}s",
                "banned": True,
                "retry_after": remaining,
            }
        
        # 清理过期记录
        state.cleanup()
        
        # 计算各时间窗口的请求数
        one_second_ago = current_time - 1
        one_minute_ago = current_time - 60
        one_hour_ago = current_time - 3600
        
        requests_1s = sum(1 for t in state.requests if t > one_second_ago)
        requests_1m = sum(1 for t in state.requests if t > one_minute_ago)
        requests_1h = len(state.requests)
        
        # 检查限制
        is_order = endpoint in self.order_endpoints
        
        if is_order:
            limit_1s = self.config.order_per_second
            limit_1m = self.config.order_per_minute
        else:
            limit_1s = self.config.requests_per_second
            limit_1m = self.config.requests_per_minute
        
        limit_1h = self.config.requests_per_hour
        
        # 判断
        if requests_1s >= limit_1s:
            state.violations += 1
            self._check_ban(state)
            return False, {
                "message": f"Rate limit: {limit_1s}/s exceeded",
                "limit": "per_second",
                "current": requests_1s,
                "retry_after": 1,
            }
        
        if requests_1m >= limit_1m:
            state.violations += 1
            self._check_ban(state)
            return False, {
                "message": f"Rate limit: {limit_1m}/min exceeded",
                "limit": "per_minute",
                "current": requests_1m,
                "retry_after": 60 - (current_time - one_minute_ago),
            }
        
        if requests_1h >= limit_1h:
            state.violations += 1
            self._check_ban(state)
            return False, {
                "message": f"Rate limit: {limit_1h}/h exceeded",
                "limit": "per_hour",
                "current": requests_1h,
                "retry_after": 3600,
            }
        
        # 通过，重置违规计数
        state.violations = 0
        
        return True, {
            "allowed": True,
            "remaining": {
                "per_second": limit_1s - requests_1s,
                "per_minute": limit_1m - requests_1m,
                "per_hour": limit_1h - requests_1h,
            }
        }
    
    def _check_ban(self, state: RateLimitState):
        """检查是否需要封禁"""
        if state.violations >= self.config.ban_threshold:
            state.banned_until = datetime.now() + timedelta(
                seconds=self.config.ban_duration_seconds
            )
            state.violations = 0
    
    def record(self, agent_id: str, endpoint: str = "/"):
        """记录请求"""
        self.states[agent_id].requests.append(time.time())
    
    def get_status(self, agent_id: str) -> dict:
        """获取 Agent 限流状态"""
        state = self.states[agent_id]
        state.cleanup()
        
        current_time = time.time()
        one_second_ago = current_time - 1
        one_minute_ago = current_time - 60
        
        return {
            "agent_id": agent_id,
            "requests_1s": sum(1 for t in state.requests if t > one_second_ago),
            "requests_1m": sum(1 for t in state.requests if t > one_minute_ago),
            "requests_1h": len(state.requests),
            "violations": state.violations,
            "banned": state.banned_until is not None and datetime.now() < state.banned_until,
            "banned_until": state.banned_until.isoformat() if state.banned_until else None,
        }
    
    def reset(self, agent_id: str):
        """重置 Agent 限流状态"""
        if agent_id in self.states:
            del self.states[agent_id]
    
    def unban(self, agent_id: str):
        """解除封禁"""
        if agent_id in self.states:
            self.states[agent_id].banned_until = None
            self.states[agent_id].violations = 0


# 单例
rate_limiter = RateLimiter()


# ==========================================
# FastAPI 中间件
# ==========================================

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI 限流中间件"""
    
    def __init__(self, app, limiter: RateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        # 从请求中提取 agent_id
        agent_id = self._extract_agent_id(request)
        
        if agent_id:
            allowed, info = await self.limiter.check(agent_id, request.url.path)
            
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=info,
                    headers={"Retry-After": str(int(info.get("retry_after", 1)))}
                )
            
            self.limiter.record(agent_id, request.url.path)
        
        response = await call_next(request)
        return response
    
    def _extract_agent_id(self, request: Request) -> Optional[str]:
        """从请求中提取 Agent ID"""
        # 1. 从 Header
        agent_id = request.headers.get("X-Agent-ID")
        if agent_id:
            return agent_id
        
        # 2. 从 Query
        agent_id = request.query_params.get("agent_id")
        if agent_id:
            return agent_id
        
        # 3. 从 Path
        path = request.url.path
        if "/agents/" in path:
            parts = path.split("/agents/")
            if len(parts) > 1:
                return parts[1].split("/")[0]
        
        # 4. 用 IP 作为 fallback
        return request.client.host if request.client else None
