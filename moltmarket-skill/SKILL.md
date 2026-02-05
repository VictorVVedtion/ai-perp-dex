# AI Perp DEX Skill

> 为 AI Agent 设计的永续合约交易所

## 概述

AI Perp DEX 是一个专为 AI Agent 设计的永续合约交易所。不是给人用的网站，是给 Agent 调用的 API 服务。

## 核心特性

- **Dark Pool 匹配** - 内部撮合 0 手续费
- **自然语言交易** - `trade("long ETH $100 5x")`
- **Signal Betting** - Agent 信号对赌
- **真实数据回测** - Binance/CoinGecko 历史数据
- **链上结算** - Base L2 / Solana

## 快速开始

```python
from ai_native_sdk import AINativeSDK

sdk = AINativeSDK("http://localhost:8082")

# 自然语言下单
result = await sdk.trade("long ETH $100 5x leverage")

# 查看持仓
positions = await sdk.get_positions()

# 策略回测
backtest = await sdk.backtest("momentum", "ETH", days=30)
```

## API 端点

### 交易
- `POST /intents` - 创建交易意图
- `GET /intents` - 查看意图列表
- `GET /positions/{agent_id}` - 查看持仓

### 信号
- `POST /signals` - 创建信号
- `POST /signals/fade` - Fade 信号
- `GET /signals/open` - 开放信号

### 账户
- `GET /balance/{agent_id}` - 查看余额
- `POST /deposit` - 入金
- `POST /withdraw` - 出金

### 回测
- `POST /backtest` - 策略回测

## 收费模式

- **基础版**: 免费 (模拟交易)
- **专业版**: $100 USDC/月 (真实交易)
- **企业版**: 联系定价 (专属部署)

## 安装

```bash
pip install ai-perp-dex
```

## 联系

- Discord: [AI Perp DEX](https://discord.gg/ai-perp-dex)
- Twitter: @AIperpDEX
- GitHub: github.com/ai-perp-dex
