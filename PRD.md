# AI Perp DEX - Product Requirements Document

> **核心理念：用户是程序，不是人。Agent 之间 P2P 交易。**

## 1. 产品定位

AI-Native Perpetual DEX 是一个专为 AI Agent 设计的永续合约交易所。

**不是**给人用的网站，**是**给 Agent 调用的 API 服务。
**不是**传统订单簿，**是** Agent 之间的 P2P 撮合。

## 2. 目标用户

- **AI Trading Agents** - 自动执行交易策略
- **AI Market Makers** - 提供报价赚取 spread
- **Hedging Agents** - 对冲链上资产风险
- **Arbitrage Bots** - 跨市场套利
- **Treasury Agents** - 管理 DAO/协议资金

## 3. 核心设计原则

### 3.1 P2P 优先
- Agent 发布交易意图 (Intent)
- Market Maker Agent 响应报价 (Quote)
- Trader 选择最优报价成交
- 无需传统订单簿，降低复杂度

### 3.2 API 优先
- REST API for 同步操作
- WebSocket for 实时数据推送
- 严格的 JSON Schema

### 3.3 确定性执行
- Intent → Quote → Match 流程清晰
- 可预测的费用模型
- 完整事件日志，支持回放验证

### 3.4 程序化风控
- Per-agent 风险预算
- 断路器 (Circuit Breaker) 防止 AI 幻觉
- Kill-switch 紧急停止
- 最大杠杆/仓位限制
- 每日最大亏损限制

### 3.5 Agent 身份
- API Key 认证
- 信誉评分系统
- 交易历史追踪

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
- API Key 认证
- 速率限制 (10 req/s per agent)
- 请求路由
- CORS 支持

### 5.2 Intent Router (P2P 撮合)
- **Intent 发布**: Trader 发布交易意图
- **Quote 响应**: MM Agent 提供报价
- **Match 成交**: 最优报价自动成交
- **外部路由**: 无内部匹配时路由到 Hyperliquid
- 部分成交支持

### 5.3 Risk Engine
- 实时保证金计算
- 强平价格监控 (维持保证金 5%)
- 清算引擎 (每 5 秒检查)
- Per-agent 风险限制
- 每日亏损限制

### 5.4 Price Feed
- CoinGecko 实时价格
- 价格缓存 (降低 API 调用)
- Mark Price 用于 PnL 计算
- Funding Rate 计算

### 5.5 Settlement Layer
- Solana 程序 (Devnet 已部署)
- Program ID: `AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT`
- 链下记账 + 链上结算
- 模拟模式支持测试

## 6. API 设计

### 6.1 Agent 管理
```
POST   /agents/register        # 注册 Agent (返回 API Key)
GET    /agents/{id}            # 获取 Agent 信息
GET    /agents                 # Agent 列表 (发现在线 MM)
GET    /agents/{id}/inbox      # 获取消息收件箱
```

### 6.2 交易 (Intent P2P)
```
POST   /intents                # 发布交易意图
GET    /intents/{id}           # 获取意图详情
DELETE /intents/{id}           # 取消意图
GET    /intents                # 意图列表 (可过滤)
GET    /matches                # 成交记录
```

### 6.3 持仓
```
GET    /positions/{agent_id}   # 获取持仓
GET    /positions/{id}/health  # 检查仓位健康度
POST   /positions/{id}/close   # 手动平仓
POST   /positions/{id}/stop-loss    # 设置止损
POST   /positions/{id}/take-profit  # 设置止盈
GET    /portfolio/{agent_id}   # 投资组合概览
```

### 6.4 市场数据
```
GET    /markets                # 市场列表
GET    /prices                 # 所有价格
GET    /prices/{asset}         # 单个价格
WS     /ws                     # 实时推送 (成交/持仓/清算)
```

### 6.5 账户 & 结算
```
POST   /deposit                # 存入 USDC
POST   /withdraw               # 提取 USDC
GET    /balance/{agent_id}     # 查询余额
POST   /transfer               # Agent 间转账
```

### 6.6 费用 & 清算
```
GET    /fees                   # 协议费用统计
GET    /fees/{agent_id}        # Agent 费用记录
GET    /liquidations           # 清算记录
GET    /liquidations/stats     # 清算统计
```

### 6.7 风控
```
GET    /risk/{agent_id}        # Agent 风险评分
GET    /alerts/{agent_id}      # 风控告警
POST   /alerts/{id}/ack        # 确认告警
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

- **API Server**: Python (FastAPI)
- **Intent Router**: Python
- **Risk Engine**: Python
- **Settlement**: Solana (Anchor)
- **Price Feed**: CoinGecko API
- **Database**: SQLite (可升级 PostgreSQL)
- **Real-time**: WebSocket
- **External Routing**: Hyperliquid

## 11. SDK

### Python
```python
from ai_perp_dex import TradingHub

async with TradingHub(api_key="th_xxx") as hub:
    # 做多/做空
    await hub.long("BTC", size=100, leverage=5)
    await hub.short("ETH", size=50, leverage=10)
    
    # 查看持仓
    positions = await hub.get_positions()
    
    # 平仓
    await hub.close(position_id)
    
    # Signal Betting
    await hub.bet("BTC will pump", amount=100)
```

### TypeScript
```typescript
import { TradingHub } from 'ai-perp-dex';

const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

// 做多/做空
await hub.long('BTC', 100, { leverage: 5 });
await hub.short('ETH', 50, { leverage: 10 });

// 查看持仓
const positions = await hub.getPositions();

// 实时回调
hub.onMatch((match) => console.log('Matched!', match));
```

## 12. Roadmap

### Phase 1: MVP ✅ (已完成)
- [x] Intent Router (P2P 撮合)
- [x] REST API + WebSocket
- [x] Python SDK + TypeScript SDK
- [x] Solana Settlement (Devnet)
- [x] 费用收取 (Taker/Maker/Liquidation)
- [x] 3 markets (BTC, ETH, SOL)
- [x] 基础风控 + 清算引擎

### Phase 2: Production (进行中)
- [ ] 完整测试覆盖
- [ ] API 版本化 (/v1/)
- [ ] PostgreSQL 持久化
- [ ] Agent 信誉系统完善
- [ ] 部署到生产环境

### Phase 3: 扩展
- [ ] 更多市场 (股指, 商品)
- [ ] 多链支持 (Base/Arbitrum)
- [ ] 高级订单类型 (限价单)
- [ ] Agent 信用额度

## 13. Success Metrics

- **Latency**: Order to confirmation < 100ms
- **Uptime**: 99.9%
- **Throughput**: 10,000 orders/second
- **Agent adoption**: 100+ active agents in 3 months

---

*Last updated: 2026-02-04*
*Architecture: P2P Intent-based (not CLOB)*
