# AI Perp DEX 万级 Agent 扩容方案

## 当前状态
- ❌ 50 并发崩溃
- ❌ 平均响应 1.5s
- ❌ 内存数据库

## 目标
- ✅ 10,000 Agent 同时在线
- ✅ 响应 < 100ms
- ✅ 99.9% 可用性

---

## 1. 数据层 (P0)

### 现状
```python
# 内存字典
agents: Dict[str, Agent] = {}
positions: Dict[str, Position] = {}
```

### 方案
```python
# Redis 缓存 + PostgreSQL 持久化
redis = Redis(cluster=True)
db = PostgreSQL(read_replicas=3)
```

| 数据 | 存储 | 原因 |
|------|------|------|
| Agent 状态 | Redis | 高频读写 |
| 价格 | Redis | 实时更新 |
| 持仓 | Redis + PG | 热数据+持久化 |
| 历史交易 | PostgreSQL | 查询分析 |
| Thoughts | TimescaleDB | 时序数据 |

---

## 2. 撮合引擎 (P0)

### 现状
- 单线程 Python
- O(n) 匹配

### 方案
```
                    ┌─────────────┐
                    │  API Layer  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │ BTC队列 │  │ ETH队列 │  │ SOL队列 │
         └────┬───┘  └────┬───┘  └────┬───┘
              │           │           │
              ▼           ▼           ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │Matcher1│  │Matcher2│  │Matcher3│
         └────────┘  └────────┘  └────────┘
```

- 按资产分片
- Rust 重写 Matcher
- LMAX Disruptor 模式

---

## 3. API 层 (P1)

### 现状
- 单实例 Uvicorn
- 同步阻塞

### 方案
```yaml
# docker-compose.yml
services:
  api:
    replicas: 10
    
  nginx:
    load_balance: least_conn
    
  redis:
    cluster: true
    nodes: 6
```

- 10 个 API 实例
- Nginx 负载均衡
- 连接池优化

---

## 4. WebSocket (P1)

### 现状
- 内存维护连接
- 广播 O(n)

### 方案
```
Redis Pub/Sub
     │
     ├── WS Server 1 (2500 连接)
     ├── WS Server 2 (2500 连接)
     ├── WS Server 3 (2500 连接)
     └── WS Server 4 (2500 连接)
```

- Redis Pub/Sub 分发
- 4 个 WS 节点，每个 2500 连接

---

## 5. 快速修复 (今天可做)

### 5.1 添加保证金检查
```python
def check_margin(agent_id, size, leverage):
    balance = get_balance(agent_id)
    required_margin = size / leverage
    if required_margin > balance * 0.8:  # 80% 限制
        raise InsufficientMargin()
```

### 5.2 禁止同向开仓
```python
def check_existing_position(agent_id, asset, side):
    existing = get_positions(agent_id, asset)
    for pos in existing:
        if pos.side != side:
            raise ConflictingPosition("Cannot long and short same asset")
```

### 5.3 并发限流
```python
# 每 Agent 10 req/s
rate_limiter = RateLimiter(
    per_agent=10,
    global_limit=1000,  # 全局 1000/s
)
```

---

## 6. 实施阶段

| 阶段 | 目标 | 时间 |
|------|------|------|
| Phase 1 | 修复 P0 bug | 今天 |
| Phase 2 | Redis 缓存 | 1-2 天 |
| Phase 3 | 多实例部署 | 2-3 天 |
| Phase 4 | Rust Matcher | 1 周 |
| Phase 5 | 压测 1 万 | 验收 |

---

## 7. 预估资源

| 资源 | 规格 | 成本/月 |
|------|------|---------|
| API Servers | 4x 2C4G | $80 |
| Redis Cluster | 3x 2G | $60 |
| PostgreSQL | 1x 4C8G | $50 |
| Load Balancer | 1x | $20 |
| **Total** | | **$210** |

---

## 8. 今天可以先做

1. ✅ 保证金检查
2. ✅ 禁止对冲
3. ✅ 全局限流
4. ✅ 连接池优化

这些不需要架构改动，可以立即提升稳定性。
