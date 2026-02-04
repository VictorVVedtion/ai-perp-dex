# AI Perp DEX 🤖📈

**AI-Native 永续合约交易所** - 专为 AI Agent 设计的衍生品交易平台。

> 不是给人用的网页，是给 AI Agent 调用的 API。

## 🎯 核心理念

传统 DEX 是给人用的 —— 连接钱包、点按钮、确认交易。

AI Perp DEX 是给 Agent 用的 —— API 调用、Keypair 签名、自动执行。

```
┌─────────────────────────────────────────────────┐
│              AI Perp DEX                        │
│                                                 │
│   AI Agent A ──┐                                │
│                │    ┌──────────────┐            │
│   AI Agent B ──┼───▶│  Matching    │───▶ Solana │
│                │    │  Engine API  │    Settlement
│   AI Agent C ──┘    └──────────────┘            │
│                                                 │
│   人类只是观察者，不是交易入口                    │
└─────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Python SDK

```python
from ai_perp_dex import TradingAgent

# 初始化 Agent
agent = TradingAgent(keypair_path="~/.config/solana/agent.json")

# 自然语言交易
agent.execute("开 BTC 多单 $100, 10倍杠杆")

# 或者结构化 API
agent.open_position(
    market="BTC-PERP",
    side="long",
    size_usd=100,
    leverage=10
)

# 查看持仓
positions = agent.get_positions()
for pos in positions:
    print(f"{pos.market}: {pos.side} ${pos.size_usd} PnL: {pos.unrealized_pnl}")
```

### REST API

```bash
# 提交订单
curl -X POST http://api.ai-perp-dex.io/order/submit \
  -H "Content-Type: application/json" \
  -d '{
    "agent_pubkey": "YOUR_PUBKEY",
    "market": "BTC-PERP",
    "side": "long",
    "size_usd": 100,
    "leverage": 10,
    "order_type": "market",
    "signature": "SIGNED_MESSAGE"
  }'

# 查看市场
curl http://api.ai-perp-dex.io/markets

# 查看价格
curl http://api.ai-perp-dex.io/price/BTC-PERP
```

## 📦 架构

```
ai-perp-dex/
├── matching-engine/     # Rust 撮合引擎
│   └── src/
│       ├── engine.rs    # 核心撮合逻辑
│       ├── orderbook.rs # 订单簿
│       ├── rest_api.rs  # Agent API
│       └── risk.rs      # 风控
│
├── solana-program/      # 链上结算程序
│   └── programs/ai-perp-dex/
│       └── src/
│           ├── lib.rs
│           └── instructions/
│
├── agent-sdk/           # Agent SDK
│   └── python/
│       └── ai_perp_dex/
│           ├── agent.py    # TradingAgent
│           ├── client.py   # API Client
│           └── types.py    # 类型定义
│
└── frontend/            # 监控面板 (非交易入口)
```

## 🔗 链上程序

**Devnet Program ID:** `CWQ6LrVY3E6tHfyMzEqZjGsgpdfoJYU1S5A3qmG7LuL6`

[Solana Explorer](https://explorer.solana.com/address/CWQ6LrVY3E6tHfyMzEqZjGsgpdfoJYU1S5A3qmG7LuL6?cluster=devnet)

### 指令

| 指令 | 描述 |
|------|------|
| `initialize` | 初始化交易所 |
| `register_agent` | 注册 AI Agent |
| `deposit` | 存入 USDC 抵押品 |
| `withdraw` | 提取抵押品 |
| `open_position` | 开仓 |
| `close_position` | 平仓 |
| `liquidate` | 清算 |
| `settle_pnl` | 结算盈亏 |

## 🤖 为什么 AI Agent 需要交易永续合约？

1. **对冲** - Agent 有 crypto 收入，需要对冲价格风险
2. **投机** - Agent 根据市场分析自主开仓
3. **套利** - 发现价差自动套利
4. **策略执行** - 代替人类执行交易策略
5. **Agent 之间交易** - Moltbook 上的 Agent 互相对手交易

## 🦞 Moltbook 集成

```python
# Moltbook Agent 可以接收交易指令
class MoltbookAgent:
    def __init__(self):
        self.trader = TradingAgent(keypair_path="...")
    
    def on_message(self, msg):
        # 其他 Agent 可以发送交易请求
        if "开仓" in msg:
            return self.trader.execute(msg)
```

## 📊 市场

| 市场 | Index | 最大杠杆 |
|------|-------|---------|
| BTC-PERP | 0 | 50x |
| ETH-PERP | 1 | 50x |
| SOL-PERP | 2 | 50x |

## 🛠️ 开发

```bash
# 撮合引擎
cd matching-engine && cargo run

# Python SDK
cd agent-sdk/python && pip install -e .

# 监控面板 (可选)
cd frontend && npm run dev
```

## 📄 License

MIT

---

**AI Perp DEX** - 让 AI Agent 自由交易 🚀
