# MM Agents - Market Maker Bots

AI 做市商机器人示例，用于 P2P 永续合约交易。

## 🤖 可用策略

### 1. Conservative MM (`conservative_mm.py`)
保守型做市商，适合新手和低风险偏好者。

**特点：**
- 宽价差 (1-2%)
- 低杠杆限制 (≤20x)
- 小仓位限额 ($5k)
- 只做主流币 (BTC, ETH)

```bash
python conservative_mm.py
```

### 2. Aggressive MM (`aggressive_mm.py`)
激进型做市商，追求高成交量。

**特点：**
- 窄价差 (0.3-0.5%)
- 高杠杆容忍
- 大仓位 ($50k)
- 所有市场
- 对冲意识定价

```bash
python aggressive_mm.py
```

### 3. Arbitrage MM (`arbitrage_mm.py`)
套利型做市商，基于外部交易所价格定价。

**特点：**
- 实时价格源 (Hyperliquid)
- 只在有套利空间时报价
- 设计用于跨平台对冲
- 低风险高效率

```bash
python arbitrage_mm.py
```

## 🚀 运行

### 前置条件

1. 确保 Trade Router 正在运行：
```bash
cd ../trade-router
cargo run
```

2. 安装 Python 依赖：
```bash
pip install aiohttp websockets
cd ../agent-sdk/python
pip install -e .
```

### 启动做市商

```bash
# 单个做市商
python conservative_mm.py

# 或者同时运行多个
python conservative_mm.py &
python aggressive_mm.py &
```

### 环境变量

```bash
export WS_URL=ws://localhost:8080/ws
export REST_URL=http://localhost:8080
```

## 📊 自定义策略

继承 `MarketMakerAgent` 类创建自己的策略：

```python
from ai_perp_dex.p2p import MarketMakerAgent, TradeRequest

class MyCustomMM(MarketMakerAgent):
    def should_quote(self, request: TradeRequest) -> bool:
        # 你的过滤逻辑
        return True
    
    def calculate_funding_rate(self, request: TradeRequest) -> float:
        # 你的定价逻辑
        return 0.005  # 0.5%
```

## ⚠️ 风险警告

这些是示例代码，不是投资建议。做市涉及重大财务风险：

- 价格波动可能导致损失
- 高杠杆放大风险
- 流动性风险
- 智能合约风险

请在理解风险后谨慎操作。
