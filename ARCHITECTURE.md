# AI Perp DEX - 架构重新思考

## 核心问题

**这个产品是给谁用的？**

| 角色 | 需要什么 |
|------|----------|
| AI Trader Agent | API/SDK 下单、管理持仓 |
| AI MM Agent | API/SDK 提供报价、管理风险 |
| Agent 运营者 (人类) | 监控面板、Agent 管理、风控配置 |
| 观察者 (人类) | 看看网络活动、统计数据 |

**关键洞察：AI Agent 不需要网页 UI，只需要 API。**

---

## 抽象层次

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Dashboard (给人类)                                 │
│  - 监控 Agent 状态                                           │
│  - 查看交易历史                                              │
│  - 管理 Agent 配置                                           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Agent SDK (给 Agent)                              │
│  Python: trader.open_long("BTC", 1000, leverage=10)         │
│  Python: mm.quote_request(req_id, spread=0.1)               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Trade Router (协调层)                              │
│  - REST API + WebSocket                                      │
│  - 消息路由                                                  │
│  - 状态管理                                                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Protocol (核心协议)                                │
│  - 数据结构定义                                              │
│  - 签名验证                                                  │
│  - 结算逻辑                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 当前后端 Review

### ✅ 已有
```
POST /trade/request   - Trader 发起交易请求
POST /trade/quote     - MM 提供报价
POST /trade/accept    - Trader 接受报价
POST /trade/close     - 平仓
GET  /positions/:id   - 查询持仓
GET  /requests        - 查询所有请求
GET  /quotes/:id      - 查询某请求的报价
GET  /markets         - 市场列表
WS   /ws              - 实时推送
```

### ❌ 缺失
1. **Agent 身份**
   - 没有注册流程
   - 没有身份验证 (Keypair 签名)
   - 没有权限控制

2. **资金管理**
   - 没有保证金系统
   - 没有结算逻辑
   - 没有清算机制

3. **发现机制**
   - MM 如何广播自己在线？
   - Trader 如何找到最佳 MM？

4. **风控**
   - 没有单 Agent 限额
   - 没有系统级熔断

---

## 重新设计

### 1. Protocol Layer (核心类型)

```rust
// 所有层共享的核心类型
pub struct AgentId(pub String);  // 公钥或唯一标识

pub struct TradeRequest {
    pub id: Uuid,
    pub trader: AgentId,
    pub market: String,
    pub side: Side,
    pub size_usdc: f64,
    pub leverage: u8,
    pub max_slippage_bps: u16,  // 最大滑点
    pub expires_at: Timestamp,
    pub signature: Signature,   // 签名
}

pub struct Quote {
    pub id: Uuid,
    pub request_id: Uuid,
    pub mm: AgentId,
    pub price: f64,
    pub spread_bps: u16,
    pub expires_at: Timestamp,
    pub signature: Signature,
}

pub struct Position {
    pub id: Uuid,
    pub trader: AgentId,
    pub mm: AgentId,
    pub market: String,
    pub side: Side,
    pub size_usdc: f64,
    pub entry_price: f64,
    pub leverage: u8,
    pub created_at: Timestamp,
}
```

### 2. Trade Router (协调层)

**职责：**
- 消息路由 (不是撮合，只是转发)
- 状态持久化
- WebSocket 广播
- 基础风控

**不负责：**
- 资金托管
- 结算执行
- 身份管理 (交给 Agent 自己)

### 3. Agent SDK

```python
from ai_perp_dex import TradingAgent, MarketMaker

# Trader
trader = TradingAgent(
    private_key="...",
    router_url="http://localhost:8080"
)

# 开仓
position = await trader.open_position(
    market="BTC-PERP",
    side="long",
    size=1000,
    leverage=10,
    max_slippage_bps=50
)

# 查看持仓
positions = await trader.get_positions()

# 平仓
await trader.close_position(position.id)


# Market Maker
mm = MarketMaker(
    private_key="...",
    router_url="http://localhost:8080"
)

# 监听请求并自动报价
@mm.on_request
async def handle_request(request):
    if should_quote(request):
        price = get_fair_price(request.market)
        spread = calculate_spread(request)
        return mm.quote(request, price, spread)

mm.run()
```

### 4. Dashboard (监控层)

**给谁用：** Agent 运营者

**功能：**
```
/                     - 网络概览 (在线 Agent 数、总交易量)
/my-agents            - 我的 Agent 列表
/my-agents/:id        - 单个 Agent 详情 (持仓、PnL、配置)
/my-agents/:id/config - 配置 Agent 参数
/network              - 网络活动 (公开数据)
/docs                 - API 文档
```

---

## 下一步行动

### Phase 1: 完善后端 (1-2天)
- [ ] 添加 Agent 注册 API
- [ ] 添加签名验证
- [ ] 添加 Agent 状态 (在线/离线)
- [ ] 完善 WebSocket 消息类型

### Phase 2: Agent SDK (1-2天)
- [ ] Python SDK
- [ ] Trader 接口
- [ ] MM 接口
- [ ] 签名工具

### Phase 3: Dashboard 重做 (1天)
- [ ] 简化为监控工具
- [ ] 我的 Agent 管理
- [ ] 去掉无用的花哨设计

### Phase 4: 测试验证 (1天)
- [ ] 跑两个 Agent 互相交易
- [ ] 验证整个流程

---

## 思考

**真正的 AI-native 是什么？**

不是"给 AI 用的"，而是"AI 能自然使用的"：
- API first，不是 UI first
- 结构化输入输出，不是自然语言
- 可编程，可自动化
- 去中心化，Agent 之间直接交互

**这个项目的价值：**
- 证明 AI Agent 可以进行复杂金融活动
- 探索 Agent 间协作的模式
- 为未来 Agent Economy 提供基础设施
