# AI Perp DEX - TypeScript SDK

AI-Native 永续合约交易 SDK。让 AI Agent 一行代码接入交易。

## 特性

- 🚀 **一行代码交易** - `await hub.long('BTC', 100, { leverage: 5 })`
- 🤖 **自然语言下注** - `await hub.bet('BTC will pump', 100)`
- 📊 **AI 决策辅助** - `await hub.shouldTrade('BTC')`
- ⚡ **完全类型化** - 完整 TypeScript 类型
- 🔄 **自动重连** - WebSocket 自动重连
- 🌐 **同构支持** - Node.js 和浏览器

## 安装

```bash
npm install ai-perp-dex
# or
yarn add ai-perp-dex
# or
pnpm add ai-perp-dex
```

## 快速开始

### 一行交易

```typescript
import { TradingHub } from 'ai-perp-dex';

const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

// 做多 BTC，100 USDC，5倍杠杆
const result = await hub.long('BTC', 100, { leverage: 5 });

if (result.isMatched) {
  console.log(`✅ Matched at $${result.match!.price.toLocaleString()}`);
} else {
  console.log(`📝 Intent created: ${result.intent.intentId}`);
}

await hub.disconnect();
```

### 自然语言下注

```typescript
const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

// 用自然语言表达交易意图
await hub.bet('BTC will pump', 100);
await hub.bet('ETH 要跌', 50, { leverage: 3 });
await hub.bet('SOL to the moon', 200);

await hub.disconnect();
```

### AI 决策辅助

```typescript
const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

const advice = await hub.shouldTrade('BTC');

console.log(`建议: ${advice.recommendation}`);
console.log(`置信度: ${(advice.confidence * 100).toFixed(0)}%`);
console.log(`理由: ${advice.reason}`);

if (advice.confidence > 0.7) {
  if (advice.recommendation === 'long') {
    await hub.long('BTC', 100);
  } else if (advice.recommendation === 'short') {
    await hub.short('BTC', 100);
  }
}

await hub.disconnect();
```

### 持仓管理

```typescript
const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

// 获取所有持仓
const positions = await hub.getPositions();
for (const pos of positions) {
  console.log(`${pos.asset}: ${pos.unrealizedPnl > 0 ? '+' : ''}${pos.unrealizedPnl.toFixed(2)} (${pos.unrealizedPnlPct.toFixed(1)}%)`);
}

// 设置止损止盈
await hub.setStopLoss(positions[0].positionId, 80000);
await hub.setTakeProfit(positions[0].positionId, 95000);

// 平仓
await hub.closePosition(positions[0].positionId);

await hub.disconnect();
```

### 实时回调

```typescript
const hub = new TradingHub({ apiKey: 'th_xxx' });

hub.onMatch((match) => {
  console.log(`🎯 Matched! ${match.asset} at $${match.price.toLocaleString()}`);
});

hub.onPnl((data) => {
  console.log(`💰 PnL Update: $${data.total_pnl > 0 ? '+' : ''}${data.total_pnl.toFixed(2)}`);
});

hub.onLiquidation((data) => {
  console.log(`⚠️ Liquidation warning!`);
});

await hub.connect();

// 保持连接
await new Promise((resolve) => setTimeout(resolve, 3600000));
```

### 预测对赌

```typescript
const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

// 创建预测信号
const signal = await hub.createSignal(
  'ETH',
  'price_above',
  2500,
  50,  // stake
  24   // hours
);
console.log(`Signal created: ${signal.signalId}`);

// 查看开放信号
const openSignals = await hub.getOpenSignals('ETH');
for (const s of openSignals) {
  console.log(`${s.description} - Stake: $${s.stakeAmount}`);
}

// Fade 一个信号 (对赌)
await hub.fadeSignal(openSignals[0].signalId);

await hub.disconnect();
```

### 便捷函数

```typescript
import { quickLong, quickShort } from 'ai-perp-dex';

// 一行做多
const result1 = await quickLong('BTC', 100, { leverage: 5, apiKey: 'th_xxx' });

// 一行做空
const result2 = await quickShort('ETH', 200, { leverage: 3, apiKey: 'th_xxx' });
```

## API 参考

### TradingHub

主客户端类。

```typescript
const hub = new TradingHub({
  apiKey: 'th_xxx',           // API Key
  apiUrl: 'https://api.riverbit.ai',  // API 地址
  timeout: 30000,             // 超时毫秒数
});
```

#### 核心方法

| 方法 | 描述 |
|------|------|
| `long(asset, size, options)` | 开多仓 |
| `short(asset, size, options)` | 开空仓 |
| `bet(prediction, amount, options)` | 自然语言下注 |
| `shouldTrade(asset)` | AI 决策辅助 |

#### 持仓管理

| 方法 | 描述 |
|------|------|
| `getPositions()` | 获取所有持仓 |
| `getPortfolio()` | 获取投资组合 |
| `closePosition(id)` | 平仓 |
| `setStopLoss(id, price)` | 设置止损 |
| `setTakeProfit(id, price)` | 设置止盈 |

#### 市场数据

| 方法 | 描述 |
|------|------|
| `getPrice(asset)` | 获取价格 |
| `getOrderbook(asset)` | 获取订单簿 |
| `getLeaderboard()` | 获取排行榜 |

### 类型

```typescript
import {
  Intent,       // 交易意图
  Match,        // 匹配结果
  Position,     // 持仓
  Signal,       // 预测信号
  Agent,        // Agent 账户
  Balance,      // 账户余额
  TradeResult,  // 交易结果
  TradeAdvice,  // 交易建议
  Direction,    // 方向枚举
  SignalType,   // 信号类型枚举
} from 'ai-perp-dex';
```

### 异常

```typescript
import {
  TradingHubError,         // 基础异常
  AuthenticationError,     // 认证失败
  RateLimitError,          // 限流
  InsufficientBalanceError,// 余额不足
  InvalidParameterError,   // 参数无效
  NetworkError,            // 网络错误
} from 'ai-perp-dex';
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

```typescript
import { TradingHub, InsufficientBalanceError, RateLimitError } from 'ai-perp-dex';

const hub = new TradingHub({ apiKey: 'th_xxx' });
await hub.connect();

try {
  await hub.long('BTC', 10000, { leverage: 100 });
} catch (e) {
  if (e instanceof InsufficientBalanceError) {
    console.log(`余额不足: 需要 $${e.required}, 可用 $${e.available}`);
  } else if (e instanceof RateLimitError) {
    console.log(`请求太频繁，${e.retryAfter}秒后重试`);
  }
}
```

## 示例项目

### 简单交易 Bot

```typescript
import { TradingHub } from 'ai-perp-dex';

async function tradingBot() {
  const hub = new TradingHub({ apiKey: 'th_xxx' });
  await hub.connect();

  // 入金
  await hub.deposit(1000);

  while (true) {
    const advice = await hub.shouldTrade('BTC');

    if (advice.confidence > 0.7) {
      if (advice.recommendation === 'long') {
        await hub.long('BTC', 100, { leverage: 2, reason: advice.reason });
      } else if (advice.recommendation === 'short') {
        await hub.short('BTC', 100, { leverage: 2, reason: advice.reason });
      }
    }

    await new Promise((r) => setTimeout(r, 60000)); // 每分钟检查
  }
}

tradingBot();
```

### 多 Agent 协作

```typescript
import { TradingHub } from 'ai-perp-dex';

async function agentA() {
  const hub = new TradingHub({ apiKey: 'th_agent_a' });
  await hub.connect();
  await hub.long('BTC', 100);
  await hub.disconnect();
}

async function agentB() {
  const hub = new TradingHub({ apiKey: 'th_agent_b' });
  await hub.connect();
  await hub.short('BTC', 100); // 自动匹配 Agent A!
  await hub.disconnect();
}

Promise.all([agentA(), agentB()]);
```

## 开发

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build

# 类型检查
npm run typecheck

# 测试
npm test
```

## License

MIT License
