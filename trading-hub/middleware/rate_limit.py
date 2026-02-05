"""
速率限制中间件

基于 IP 和 Agent ID 的双重限制
"""
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件
    
    配置:
    - requests_per_second: 每秒请求数
    - burst_size: 突发容量
    """
    
    def __init__(
        self,
        app,
        requests_per_second: int = 10,
        burst_size: int = 20,
    ):
        super().__init__(app)
        self.rps = requests_per_second
        self.burst = burst_size
        
        # Token bucket: {key: (tokens, last_update)}
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (self.burst, time.time())
        )
    
    def _get_key(self, request: Request) -> str:
        """获取限流 key (IP + Agent ID)"""
        client_ip = request.client.host if request.client else "unknown"
        agent_id = request.headers.get("X-Agent-ID", "")
        return f"{client_ip}:{agent_id}"
    
    def _check_rate(self, key: str) -> bool:
        """检查是否允许请求"""
        tokens, last_update = self._buckets[key]
        now = time.time()
        
        # 补充 token
        elapsed = now - last_update
        tokens = min(self.burst, tokens + elapsed * self.rps)
        
        if tokens >= 1:
            self._buckets[key] = (tokens - 1, now)
            return True
        else:
            self._buckets[key] = (tokens, now)
            return False
    
    async def dispatch(self, request: Request, call_next):
        # 白名单路径 (不限流)
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        key = self._get_key(request)
        
        if not self._check_rate(key):
            raise HTTPException(
                429, 
                "Rate limit exceeded. Please slow down.",
                headers={"Retry-After": "1"}
            )
        
        return await call_next(request)
