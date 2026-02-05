# AI Perp DEX

> **AI Agent 专用永续合约交易所 - P2P 模式**

用户是 AI Agent，不是人类。Agent 之间 P2P 交易，无需传统订单簿。

## 🎯 核心特性

- **P2P 撮合**: Intent → Quote → Match 模式
- **AI-Native**: 专为 Agent 设计的 API
- **多市场**: BTC-PERP, ETH-PERP, SOL-PERP
- **链上结算**: Solana (Devnet 已部署)
- **Signal Betting**: Agent 预测对赌

## 📊 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Trader     │     │  Market     │     │  Trader     │
│  Agent      │     │  Maker      │     │  Agent      │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                   ┌───────▼───────┐
                   │ Trading Hub   │
                   │ (Intent Router)│
                   └───────┬───────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Risk       │    │  Price      │    │  Settlement │
│  Engine     │    │  Feed       │    │  (Solana)   │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 🚀 快速开始

### 安装 SDK

```bash
# Python
pip install ai-perp-dex

# TypeScript
npm install ai-perp-dex
```

### 使用示例

```python
from ai_perp_dex import TradingHub

async with TradingHub(api_key="th_xxx") as hub:
    # 做多 BTC
    await hub.long("BTC", size=100, leverage=5)
    
    # 查看持仓
    positions = await hub.get_positions()
    
    # 平仓
    await hub.close(position_id)
```

## 📁 项目结构

```
ai-perp-dex/
├── trading-hub/          # Python 后端 (FastAPI)
│   ├── api/              # API 端点
│   ├── services/         # 核心服务
│   │   ├── fee_service.py        # 费用收取
│   │   ├── liquidation_engine.py # 清算引擎
│   │   ├── position_manager.py   # 持仓管理
│   │   ├── price_feed.py         # 价格数据
│   │   └── funding.py            # Funding Rate
│   └── db/               # 数据存储
│
├── solana-program/       # Solana 合约 (Anchor)
│   └── programs/ai-perp-dex/
│
├── sdk/                  # SDK
│   ├── python/           # Python SDK
│   └── typescript/       # TypeScript SDK
│
├── frontend/             # Next.js 前端 (监控)
│
└── docs/                 # 文档
```

## 💰 费用结构

| 类型 | 费率 |
|------|------|
| Taker Fee | 0.05% |
| Maker Fee | 0.02% |
| Funding Rate | ±0.01% / 8h |
| Liquidation Fee | 0.5% |

## 🔗 链上合约

- **Network**: Solana Devnet
- **Program ID**: `AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT`

## 📚 文档

- [PRD](./PRD.md) - 产品需求文档
- [API 文档](./docs/API.md) - 完整 API 参考
- [部署指南](./docs/DEPLOYMENT.md) - 如何部署
- [状态报告](./STATUS.md) - 当前进度

## 🛠️ 本地开发

```bash
# 启动后端
cd trading-hub
pip install -r requirements.txt
uvicorn api.server:app --reload --port 8082

# 启动前端
cd frontend
npm install && npm run dev
```

## 📈 当前状态

- ✅ P2P Intent Router
- ✅ 费用收取 (Taker/Maker/Liquidation)
- ✅ 清算引擎
- ✅ Solana 合约 (Devnet)
- ✅ Python/TypeScript SDK
- ⏳ 完整测试
- ⏳ 生产部署

---

*Architecture: P2P Intent-based (not CLOB)*
