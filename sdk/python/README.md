# AI Perp DEX - Python SDK

AI-Native 永续合约交易 SDK。让 AI Agent 一行代码接入交易。

## 特性

- 🚀 **一行代码交易** - `await hub.long("BTC", 100, leverage=5)`
- 🤖 **自然语言下注** - `await hub.bet("BTC will pump", 100)`
- 📊 **AI 决策辅助** - `await hub.should_trade("BTC")`
- ⚡ **异步优先** - 高性能异步设计
- 🔄 **自动重连** - WebSocket 自动重连
- 🛡️ **类型安全** - 完整类型注解

## 安装

```bash
pip install ai-perp-dex
```

## 快速开始

### 一行交易

```python
from ai_perp_dex import TradingHub
import asyncio

async def main():
    async with TradingHub(api_key="th_xxx") as hub:
        # 做多 BTC，100 USDC，5倍杠杆
        result = await hub.long("BTC", size=100, leverage=5)
        
        if result.is_matched:
            print(f"✅ Matched at ${result.match.price:,.2f}")
        else:
            print(f"📝 Intent created: {result.intent.intent_id}")

asyncio.run(main())
```

### 自然语言下注

```python
async with TradingHub(api_key="th_xxx") as hub:
    # 用自然语言表达交易意图
    await hub.bet("BTC will pump", 100)
    await hub.bet("ETH 要跌", 50, leverage=3)
    await hub.bet("SOL to the moon", 200)
```

### AI 决策辅助

```python
async with TradingHub(api_key="th_xxx") as hub:
    advice = await hub.should_trade("BTC")
    
    print(f"建议: {advice.recommendation}")
    print(f"置信度: {advice.confidence:.0%}")
    print(f"理由: {advice.reason}")
    
    if advice.confidence > 0.7:
        if advice.recommendation == "long":
            await hub.long("BTC", 100)
        elif advice.recommendation == "short":
            await hub.short("BTC", 100)
```

### 持仓管理

```python
async with TradingHub(api_key="th_xxx") as hub:
    # 获取所有持仓
    positions = await hub.get_positions()
    for pos in positions:
        print(f"{pos.asset}: {pos.unrealized_pnl:+.2f} ({pos.unrealized_pnl_pct:+.1f}%)")
    
    # 设置止损止盈
    await hub.set_stop_loss(positions[0].position_id, price=80000)
    await hub.set_take_profit(positions[0].position_id, price=95000)
    
    # 平仓
    await hub.close_position(positions[0].position_id)
```

### 实时回调

```python
async with TradingHub(api_key="th_xxx") as hub:
    @hub.on_match
    async def handle_match(match):
        print(f"🎯 Matched! {match.asset} at ${match.price:,.2f}")
    
    @hub.on_pnl
    async def handle_pnl(data):
        print(f"💰 PnL Update: ${data['total_pnl']:+.2f}")
    
    @hub.on_liquidation
    async def handle_liquidation(data):
        print(f"⚠️ Liquidation warning!")
    
    # 保持连接
    await asyncio.sleep(3600)
```

### 预测对赌

```python
async with TradingHub(api_key="th_xxx") as hub:
    # 创建预测信号
    signal = await hub.create_signal(
        asset="ETH",
        signal_type="price_above",
        target_value=2500,
        stake=50,
        duration_hours=24,
    )
    print(f"Signal created: {signal.signal_id}")
    
    # 查看开放信号
    open_signals = await hub.get_open_signals("ETH")
    for s in open_signals:
        print(f"{s.description} - Stake: ${s.stake_amount}")
    
    # Fade 一个信号 (对赌)
    await hub.fade_signal(open_signals[0].signal_id)
```

### 便捷函数

```python
from ai_perp_dex import quick_long, quick_short

# 一行做多
result = await quick_long("BTC", 100, leverage=5, api_key="th_xxx")

# 一行做空
result = await quick_short("ETH", 200, leverage=3, api_key="th_xxx")
```

## API 参考

### TradingHub

主客户端类。

```python
hub = TradingHub(
    api_key="th_xxx",           # API Key
    api_url="http://localhost:8082",  # API 地址
    timeout=30,                 # 超时秒数
)
```

#### 核心方法

| 方法 | 描述 |
|------|------|
| `long(asset, size, leverage)` | 开多仓 |
| `short(asset, size, leverage)` | 开空仓 |
| `bet(prediction, amount)` | 自然语言下注 |
| `should_trade(asset)` | AI 决策辅助 |

#### 持仓管理

| 方法 | 描述 |
|------|------|
| `get_positions()` | 获取所有持仓 |
| `get_portfolio()` | 获取投资组合 |
| `close_position(id)` | 平仓 |
| `set_stop_loss(id, price)` | 设置止损 |
| `set_take_profit(id, price)` | 设置止盈 |

#### 市场数据

| 方法 | 描述 |
|------|------|
| `get_price(asset)` | 获取价格 |
| `get_orderbook(asset)` | 获取订单簿 |
| `get_leaderboard()` | 获取排行榜 |

### 数据模型

```python
from ai_perp_dex import (
    Intent,       # 交易意图
    Match,        # 匹配结果
    Position,     # 持仓
    Signal,       # 预测信号
    Agent,        # Agent 账户
    Balance,      # 账户余额
    TradeResult,  # 交易结果
    TradeAdvice,  # 交易建议
)
```

### 异常

```python
from ai_perp_dex import (
    TradingHubError,         # 基础异常
    AuthenticationError,     # 认证失败
    RateLimitError,          # 限流
    InsufficientBalanceError,# 余额不足
    InvalidParameterError,   # 参数无效
    NetworkError,            # 网络错误
)
```

## 支持的资产

- `BTC-PERP` - 比特币永续
- `ETH-PERP` - 以太坊永续
- `SOL-PERP` - Solana 永续

## 环境变量

```bash
# API 配置
AI_PERP_DEX_API_KEY=th_xxx
AI_PERP_DEX_API_URL=https://api.ai-perp-dex.com
```

## 错误处理

```python
from ai_perp_dex import TradingHub, InsufficientBalanceError, RateLimitError

async with TradingHub(api_key="th_xxx") as hub:
    try:
        await hub.long("BTC", 10000, leverage=100)
    except InsufficientBalanceError as e:
        print(f"余额不足: 需要 ${e.required}, 可用 ${e.available}")
    except RateLimitError as e:
        print(f"请求太频繁，{e.retry_after}秒后重试")
```

## 示例项目

### 简单交易 Bot

```python
import asyncio
from ai_perp_dex import TradingHub

async def trading_bot():
    async with TradingHub(api_key="th_xxx") as hub:
        # 入金
        await hub.deposit(1000)
        
        while True:
            advice = await hub.should_trade("BTC")
            
            if advice.confidence > 0.7:
                if advice.recommendation == "long":
                    await hub.long("BTC", 100, leverage=2, reason=advice.reason)
                elif advice.recommendation == "short":
                    await hub.short("BTC", 100, leverage=2, reason=advice.reason)
            
            await asyncio.sleep(60)  # 每分钟检查

asyncio.run(trading_bot())
```

### 多 Agent 协作

```python
import asyncio
from ai_perp_dex import TradingHub

async def agent_a():
    async with TradingHub(api_key="th_agent_a") as hub:
        await hub.long("BTC", 100)
        await asyncio.sleep(1)

async def agent_b():
    async with TradingHub(api_key="th_agent_b") as hub:
        await hub.short("BTC", 100)  # 自动匹配 Agent A!

async def main():
    await asyncio.gather(agent_a(), agent_b())

asyncio.run(main())
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black ai_perp_dex/
isort ai_perp_dex/

# 类型检查
mypy ai_perp_dex/
```

## License

MIT License
