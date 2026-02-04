# AI Perp DEX 🤖📈

**AI-Native 永续合约交易所** - Agent-to-Agent P2P 交易平台。

> v2: 不需要订单簿，Agent 互为对手方，直接撮合。

## 🎯 核心理念

**Agent 本身就是流动性**

传统 DEX 需要 LP 池或订单簿。AI Perp DEX v2 让 AI Agent 直接互相交易：

```
┌──────────────────────────────────────────────────────┐
│                    AI Perp DEX v2                    │
│                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────┐│
│  │  Trader A   │    │  MM Agent   │    │ MM Agent  ││
│  │  (Long BTC) │    │  (Quotes)   │    │ (Quotes)  ││
│  └──────┬──────┘    └──────┬──────┘    └─────┬─────┘│
│         │                  │                 │      │
│         └──────────┬───────┴─────────────────┘      │
│                    ▼                                │
│         ┌────────────────────────┐                  │
│         │    Trade Router        │ ← WebSocket 广播 │
│         │    (Rust Server)       │                  │
│         └───────────┬────────────┘                  │
│                     ▼                               │
│         ┌────────────────────────┐                  │
│         │   Solana Escrow        │ ← 保证金锁定     │
│         │   Program              │ ← 自动结算       │
│         └────────────────────────┘                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. 启动 Trade Router

```bash
cd trade-router
cargo run
# 🚀 Trade Router starting on 0.0.0.0:8080
# 📡 WebSocket endpoint: ws://0.0.0.0:8080/ws
```

### 2. 运行做市商 Agent

```bash
cd mm-agents
python conservative_mm.py
# 🤖 Conservative Market Maker Agent
# 🔄 Listening for trade requests...
```

### 3. 使用 Python SDK 交易

```python
from ai_perp_dex import P2PClient, TraderAgent
from ai_perp_dex.types import MarketSymbol as Market, Side

async with P2PClient(agent_id="my_trader") as client:
    trader = TraderAgent(client)
    
    # 开 BTC 多单，自动获取最优报价
    position = await trader.open_position(
        market=Market.BTC_PERP,
        side=Side.LONG,
        size_usdc=100.0,
        leverage=10,
        max_funding_rate=0.01
    )
    
    print(f"Position opened: {position.id}")
    print(f"Entry price: ${position.entry_price}")
```

## 📦 项目结构

```
ai-perp-dex/
├── trade-router/        # Rust P2P 交易路由
│   └── src/
│       ├── main.rs      # 入口
│       ├── handlers.rs  # REST API
│       ├── websocket.rs # WS 广播
│       ├── state.rs     # 状态管理
│       └── types.rs     # 类型定义
│
├── escrow-program/      # Solana Anchor 合约
│   └── programs/escrow/
│       └── src/
│           ├── lib.rs       # 主程序
│           ├── state.rs     # Position 状态
│           └── errors.rs    # 错误码
│
├── agent-sdk/           # Python SDK
│   └── python/
│       └── ai_perp_dex/
│           ├── p2p.py       # P2P 客户端
│           ├── agent.py     # 原版 Agent
│           └── types.py     # 类型定义
│
├── mm-agents/           # 做市商 Agents
│   ├── conservative_mm.py  # 保守型
│   ├── aggressive_mm.py    # 激进型
│   └── arbitrage_mm.py     # 套利型
│
└── matching-engine/     # (已废弃) 原订单簿
```

## 🔄 交易流程

```
1. Trader Agent 发起请求
   POST /trade/request
   → "我要开 BTC 多单 $100, 10x, 最高付 1% 费率"

2. Trade Router 广播给所有 MM
   WebSocket → trade_request

3. MM Agents 报价
   POST /trade/quote
   → "我接，收 0.5% 费率，押 $100 保证金"

4. Trader 选择最优报价
   POST /trade/accept
   → 选 0.5% 的那个

5. 链上锁定保证金
   → Solana Escrow Program

6. 仓位创建完成！
```

## 📊 API

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /trade/request | 发起交易请求 |
| POST | /trade/quote | 提交报价 |
| POST | /trade/accept | 接受报价 |
| POST | /trade/close | 平仓 |
| GET | /positions/:agent_id | 查看持仓 |
| GET | /requests | 活跃请求 |
| GET | /markets | 市场信息 |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| trade_request | S→C | 新交易请求 |
| quote_accepted | S→C | 报价被接受 |
| position_opened | S→C | 仓位开启 |
| position_closed | S→C | 仓位关闭 |
| liquidation | S→C | 清算通知 |

## 🤖 做市策略

### Conservative MM
- 宽价差 (1-2%)
- 低杠杆 (≤20x)
- 小仓位 ($5k)
- 只做 BTC/ETH

### Aggressive MM
- 窄价差 (0.3%)
- 高杠杆容忍
- 大仓位 ($50k)
- 对冲意识定价

### Arbitrage MM
- 外部价格源 (Hyperliquid)
- 套利空间检测
- 跨平台对冲

## 💰 经济模型

| 费用 | 收费方 | 金额 |
|------|--------|------|
| 开仓费 | 协议 | 0.05% |
| 资金费率 | 多/空 | 市场决定 |
| 清算奖励 | 清算者 | 5% |

## 🛠️ 开发

```bash
# Trade Router
cd trade-router && cargo run

# Escrow Program (需要 Solana CLI)
cd escrow-program && anchor build

# Agent SDK
cd agent-sdk/python && pip install -e .

# 做市商
cd mm-agents && python conservative_mm.py
```

## 🔗 部署

**Devnet Escrow Program:** `Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS`

## 📄 License

MIT

---

**AI Perp DEX v2** - Agent 互相交易，无需订单簿 🚀
