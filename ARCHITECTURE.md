# AI Perp DEX - 架构文档

## 核心理念

> **用户是 AI Agent，不是人类。Agent 之间 P2P 交易。**

传统 DEX 为人类设计：订单簿、K线图、钱包确认。
AI Agent 不需要这些：直接表达意图，实时成交。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Agents                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   Trader    │     │   Market    │     │   Trader    │    │
│  │   Agent     │     │   Maker     │     │   Agent     │    │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘    │
│         │                   │                   │            │
└─────────┼───────────────────┼───────────────────┼────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                      ┌───────▼───────┐
                      │  API Gateway  │
                      │  (FastAPI)    │
                      └───────┬───────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐    ┌───────▼───────┐   ┌──────▼──────┐
   │   Intent    │    │    Risk       │   │   Price     │
   │   Router    │    │   Engine      │   │   Feed      │
   └──────┬──────┘    └───────┬───────┘   └──────┬──────┘
          │                   │                   │
          │           ┌───────▼───────┐           │
          │           │  Liquidation  │           │
          │           │    Engine     │           │
          │           └───────┬───────┘           │
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                      ┌───────▼───────┐
                      │  Settlement   │
                      │   (Solana)    │
                      └───────────────┘
```

---

## 交易流程 (P2P)

```
Trader              Intent Router           Market Maker
   │                      │                      │
   │──create_intent──────>│                      │
   │                      │──broadcast───────────>│
   │                      │                      │
   │                      │<──create_quote────────│
   │<──get_quotes─────────│                      │
   │                      │                      │
   │──accept_quote───────>│                      │
   │                      │──notify─────────────>│
   │                      │                      │
   │<──position_created───│                      │
```

### 外部路由 (无内部匹配时)

```
Trader              Intent Router           Hyperliquid
   │                      │                      │
   │──create_intent──────>│                      │
   │                      │  (no internal match) │
   │                      │──route_external─────>│
   │                      │<──fill───────────────│
   │<──position_created───│                      │
```

---

## 核心模块

### 1. API Gateway (`api/server.py`)
- FastAPI 实现
- API Key 认证
- 速率限制 (10 req/s per agent)
- WebSocket 实时推送

### 2. Intent Router (`services/`)
- **Intent 管理**: 创建、取消、过期处理
- **匹配引擎**: 找最优对手方
- **外部路由**: Hyperliquid 备用

### 3. Risk Engine
- **Position Manager**: 持仓管理
- **Margin Calculator**: 保证金计算
- **Liquidation Engine**: 清算执行

### 4. Fee Service (`services/fee_service.py`)
```python
TAKER_FEE = 0.0005      # 0.05%
MAKER_FEE = 0.0002      # 0.02%
LIQUIDATION_FEE = 0.005 # 0.5%
```

### 5. Price Feed (`services/price_feed.py`)
- CoinGecko API
- 价格缓存
- 实时更新

### 6. Settlement (`solana-program/`)
- Solana Anchor 合约
- 链上资金托管
- PnL 结算

---

## 数据模型

### Agent
```python
@dataclass
class Agent:
    agent_id: str
    wallet_address: str
    display_name: str
    api_key_hash: str
    status: AgentStatus
    reputation_score: float
    created_at: datetime
```

### Intent
```python
@dataclass
class TradingIntent:
    intent_id: str
    agent_id: str
    intent_type: IntentType  # long, short
    asset: str               # BTC-PERP
    size_usdc: float
    leverage: int
    max_slippage: float
    status: IntentStatus
    created_at: datetime
```

### Position
```python
@dataclass
class Position:
    position_id: str
    agent_id: str
    asset: str
    side: str
    size_usdc: float
    entry_price: float
    leverage: int
    liquidation_price: float
    unrealized_pnl: float
    margin_used: float
```

### Match
```python
@dataclass
class Match:
    match_id: str
    intent_a_id: str
    intent_b_id: str
    agent_a_id: str
    agent_b_id: str
    asset: str
    size_usdc: float
    price: float
    created_at: datetime
```

---

## 费用流转

```
交易成交
    │
    ├──> Taker 付 0.05% ──> Protocol Treasury
    │
    └──> Maker 付 0.02% ──> Protocol Treasury

清算发生
    │
    └──> 被清算方付 0.5% ──> Protocol Treasury
```

---

## 风控机制

### Agent 级别
| 参数 | 默认值 |
|------|--------|
| 最大杠杆 | 10x |
| 单笔最大仓位 | $10,000 |
| 每日最大亏损 | 10% |
| 最大持仓数 | 10 |

### 清算条件
- 维持保证金率: 5%
- 健康度 < 5% → 触发清算
- 清算费: 0.5%

### 检查频率
- 清算检查: 每 5 秒
- 价格更新: 实时
- Funding 结算: 每 8 小时

---

## 技术栈

| 组件 | 技术 |
|------|------|
| API Server | Python, FastAPI |
| 数据库 | SQLite (可升级 PostgreSQL) |
| 实时通信 | WebSocket |
| 合约 | Solana, Anchor |
| 价格源 | CoinGecko |
| 外部路由 | Hyperliquid |

---

## 部署架构

```
┌─────────────────────────────────────────┐
│                 Client                   │
│  (SDK / Frontend / Agent)               │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            Load Balancer                 │
│           (Nginx / Fly.io)              │
└────────────────────┬────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  API 1  │  │  API 2  │  │  API 3  │
   └────┬────┘  └────┬────┘  └────┬────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │    Database (Redis)    │
        └────────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   Solana (Settlement)  │
        └────────────────────────┘
```

---

*架构: P2P Intent-based (非 CLOB)*
*更新: 2026-02-04*
