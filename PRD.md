# AI Perp DEX - Product Requirements Document

> **核心理念：用户是程序，不是人**

## 1. 产品定位

AI-Native Perpetual DEX 是一个专为 AI Agent 设计的永续合约交易所。

**不是**给人用的网站，**是**给 Agent 调用的 API 服务。

## 2. 目标用户

- **AI Trading Agents** - 自动执行交易策略
- **Hedging Agents** - 对冲链上资产风险
- **Arbitrage Bots** - 跨市场套利
- **LP Agents** - 提供流动性赚取费用
- **Treasury Agents** - 管理 DAO/协议资金

## 3. 核心设计原则

### 3.1 API 优先
- REST API for 同步操作
- WebSocket for 实时数据推送
- gRPC for 高性能场景
- 严格的 JSON Schema
- 版本化端点 (`/v1/`, `/v2/`)

### 3.2 确定性执行
- 明确的撮合规则 (价格-时间优先)
- 可预测的费用模型
- 清晰的 MEV/优先级策略
- 完整事件日志，支持回放验证

### 3.3 程序化风控
- Per-agent 风险预算
- 断路器 (Circuit Breaker) 防止 AI 幻觉
- Kill-switch 紧急停止
- 最大杠杆/仓位限制
- 每日最大亏损限制

### 3.4 Agent 身份
- 加密身份 (Keypair)
- 信誉评分系统
- 信用额度 (可选)

## 4. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Perp DEX Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Agent A   │     │   Agent B   │     │   Agent C   │   │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘   │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                     ┌───────▼───────┐                       │
│                     │   API Gateway │                       │
│                     │  (REST/WS/gRPC)│                       │
│                     └───────┬───────┘                       │
│                             │                               │
│         ┌───────────────────┼───────────────────┐           │
│         │                   │                   │           │
│  ┌──────▼──────┐    ┌───────▼───────┐   ┌──────▼──────┐    │
│  │    Risk     │    │   Matching    │   │   Oracle    │    │
│  │   Engine    │    │    Engine     │   │   Service   │    │
│  └──────┬──────┘    └───────┬───────┘   └──────┬──────┘    │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                     ┌───────▼───────┐                       │
│                     │  Settlement   │                       │
│                     │   (Solana)    │                       │
│                     └───────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 5. 核心模块

### 5.1 API Gateway
- 身份验证 (Keypair 签名)
- 速率限制
- 请求路由
- 响应格式化

### 5.2 Matching Engine
- CLOB (Central Limit Order Book)
- 价格-时间优先撮合
- 支持订单类型: Market, Limit, Stop, Stop-Limit
- 部分成交支持
- 订单簿深度查询

### 5.3 Risk Engine
- 实时保证金计算
- 强平价格监控
- 断路器逻辑
- Per-agent 风险限制
- 系统级风险监控

### 5.4 Oracle Service
- 多源价格聚合 (Pyth, Chainlink, Binance)
- 异常值过滤
- 价格延迟监控
- Mark Price 计算
- Index Price 计算

### 5.5 Settlement Layer
- Solana 程序 (主网)
- 支持多链扩展
- Gas 抽象 (从保证金扣除)
- 批量结算优化

## 6. API 设计

### 6.1 Agent 管理
```
POST   /v1/agent/register      # 注册 Agent
GET    /v1/agent/info          # 获取 Agent 信息
PUT    /v1/agent/risk-params   # 设置风险参数
```

### 6.2 交易
```
POST   /v1/order               # 提交订单
DELETE /v1/order/{id}          # 取消订单
GET    /v1/orders              # 获取订单列表
GET    /v1/order/{id}          # 获取订单详情
```

### 6.3 持仓
```
GET    /v1/positions           # 获取所有持仓
GET    /v1/position/{market}   # 获取特定持仓
POST   /v1/position/close      # 平仓
PUT    /v1/position/modify     # 修改持仓 (止盈止损)
```

### 6.4 市场数据
```
GET    /v1/markets             # 获取市场列表
GET    /v1/price/{market}      # 获取价格
GET    /v1/orderbook/{market}  # 获取订单簿
WS     /v1/stream/trades       # 实时成交
WS     /v1/stream/orderbook    # 实时订单簿
WS     /v1/stream/positions    # 实时持仓更新
```

### 6.5 账户
```
GET    /v1/account             # 获取账户信息
POST   /v1/account/deposit     # 存入抵押品
POST   /v1/account/withdraw    # 提取抵押品
GET    /v1/account/history     # 交易历史
```

## 7. 风控规则

### 7.1 Agent 级别
| 参数 | 默认值 | 可配置范围 |
|------|--------|-----------|
| 最大杠杆 | 10x | 1-50x |
| 单笔最大仓位 | $10,000 | $100-$1M |
| 每日最大亏损 | $1,000 | $10-$100K |
| 最大持仓数 | 10 | 1-50 |

### 7.2 断路器
- 单笔亏损 > 50% 保证金 → 暂停交易 1 小时
- 每日亏损 > 限额 → 暂停交易至次日
- 连续 3 笔亏损 → 需要 cooldown
- 异常大额订单 → 人工审核

### 7.3 系统级别
- 单市场最大持仓集中度 < 30%
- 全系统最大杠杆敞口限制
- 异常波动时自动降杠杆

## 8. 市场

### Phase 1 (MVP)
| 市场 | Index | 最大杠杆 |
|------|-------|---------|
| BTC-PERP | 0 | 50x |
| ETH-PERP | 1 | 50x |
| SOL-PERP | 2 | 30x |

### Phase 2
- 更多加密货币 perp
- 股指 perp (SPY, QQQ)
- 商品 perp (Gold, Oil)

## 9. 费用结构

| 类型 | 费率 |
|------|------|
| Taker Fee | 0.05% |
| Maker Fee | 0.02% |
| Funding Rate | ±0.01% / 8h |
| Liquidation Fee | 0.5% |

## 10. 技术栈

- **API Gateway**: Rust (Axum)
- **Matching Engine**: Rust
- **Risk Engine**: Rust
- **Settlement**: Solana (Anchor)
- **Oracle**: Pyth Network
- **Database**: PostgreSQL + Redis
- **Message Queue**: Kafka

## 11. SDK

### Python
```python
from ai_perp_dex import TradingAgent

agent = TradingAgent(keypair_path="~/.config/solana/agent.json")

# 自然语言
agent.execute("开 BTC 多单 $100, 10x")

# 结构化
agent.open_position("BTC-PERP", "long", 100, leverage=10)
```

### JavaScript/TypeScript
```typescript
import { TradingAgent } from '@ai-perp-dex/sdk';

const agent = new TradingAgent({ keypairPath: '~/.config/solana/agent.json' });

await agent.openPosition({
  market: 'BTC-PERP',
  side: 'long',
  sizeUsd: 100,
  leverage: 10,
});
```

### Rust
```rust
use ai_perp_dex::TradingAgent;

let agent = TradingAgent::new(keypair_path)?;
agent.open_position("BTC-PERP", Side::Long, 100.0, 10)?;
```

## 12. Roadmap

### Phase 1: MVP (4 weeks)
- [ ] Matching Engine (CLOB)
- [ ] REST API
- [ ] Python SDK
- [ ] Solana Settlement
- [ ] Basic Risk Engine
- [ ] 3 markets (BTC, ETH, SOL)

### Phase 2: Production (4 weeks)
- [ ] WebSocket streaming
- [ ] Advanced Risk Engine
- [ ] Agent reputation system
- [ ] More markets
- [ ] Performance optimization

### Phase 3: Multi-chain (4 weeks)
- [ ] Base/Arbitrum support
- [ ] Cross-chain settlement
- [ ] Advanced order types
- [ ] Agent credit system

## 13. Success Metrics

- **Latency**: Order to confirmation < 100ms
- **Uptime**: 99.9%
- **Throughput**: 10,000 orders/second
- **Agent adoption**: 100+ active agents in 3 months

---

*Last updated: 2026-02-04*
