# Redis 扩容任务

## 目标
将内存数据库替换为 Redis，支持 1 万 Agent 并发

## 需要修改的文件

### 1. 新建 redis_store.py
位置: `trading-hub/db/redis_store.py`

```python
import redis.asyncio as redis
import json
from typing import Optional, Dict, List
from datetime import datetime

class RedisStore:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(url)
    
    # Agent 相关
    async def save_agent(self, agent_id: str, data: dict):
        await self.redis.hset(f"agent:{agent_id}", mapping=data)
    
    async def get_agent(self, agent_id: str) -> Optional[dict]:
        data = await self.redis.hgetall(f"agent:{agent_id}")
        return {k.decode(): v.decode() for k, v in data.items()} if data else None
    
    async def list_agents(self) -> List[str]:
        keys = await self.redis.keys("agent:*")
        return [k.decode().split(":")[1] for k in keys]
    
    # 余额相关
    async def set_balance(self, agent_id: str, balance: float):
        await self.redis.set(f"balance:{agent_id}", str(balance))
    
    async def get_balance(self, agent_id: str) -> float:
        val = await self.redis.get(f"balance:{agent_id}")
        return float(val) if val else 0.0
    
    # API Key 相关 (重启后保持有效!)
    async def save_api_key(self, key: str, agent_id: str):
        await self.redis.set(f"apikey:{key}", agent_id)
    
    async def get_agent_by_api_key(self, key: str) -> Optional[str]:
        agent_id = await self.redis.get(f"apikey:{key}")
        return agent_id.decode() if agent_id else None
    
    # Intent 相关
    async def save_intent(self, intent_id: str, data: dict):
        await self.redis.hset(f"intent:{intent_id}", mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in data.items()
        })
        # 添加到 agent 的 intent 列表
        await self.redis.lpush(f"agent_intents:{data['agent_id']}", intent_id)
    
    # Position 相关
    async def save_position(self, position_id: str, data: dict):
        await self.redis.hset(f"position:{position_id}", mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in data.items()
        })
        await self.redis.sadd(f"agent_positions:{data['agent_id']}", position_id)
    
    async def get_agent_positions(self, agent_id: str) -> List[str]:
        return [p.decode() for p in await self.redis.smembers(f"agent_positions:{agent_id}")]
```

### 2. 修改 middleware/auth.py
- 将 `api_key_store` 改为使用 Redis
- 添加 `async` 支持

### 3. 修改 server.py
- 导入 RedisStore
- 在 startup 时连接 Redis
- 修改 deposit/withdraw 使用 Redis

### 4. 添加 docker-compose.yml
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  api:
    build: .
    ports:
      - "8082:8082"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis_data:
```

### 5. 添加 requirements
在 requirements.txt 添加:
```
redis>=5.0.0
```

## 验证
1. `docker-compose up -d redis`
2. 运行测试确保 API Key 重启后仍有效
3. 运行 50 Agent 压力测试

完成后运行: clawdbot gateway wake --text "Done: Redis 扩容完成" --mode now
