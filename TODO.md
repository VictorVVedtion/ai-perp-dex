# AI Perp DEX - TODO List

## 🔴 P0 - 核心功能 (必须)

### Backend
- [ ] **margin-system**: 保证金计算 + 强平逻辑
- [ ] **price-oracle**: 集成 Pyth/Chainlink 实时价格
- [ ] **rate-limiting**: API 限流防滥用

### SDK  
- [ ] **sdk-tests**: 完整单元测试
- [ ] **sdk-docs**: API 文档 + 使用示例

### Frontend
- [ ] **fe-websocket**: 实时数据更新 (WebSocket)
- [ ] **fe-trading**: 交易界面 (开仓/平仓)

---

## 🟡 P1 - 增强功能

- [ ] **agent-stats**: Agent 交易统计 (胜率、PnL)
- [ ] **position-history**: 历史仓位查询 API
- [ ] **funding-settlement**: 定时结算 funding rate
- [ ] **risk-limits**: 单 Agent 风险限额

---

## 🟢 P2 - 生态集成

- [ ] **solana-escrow**: 链上资金托管
- [ ] **moltmarket-skill**: 打包成 MoltMarket skill
- [ ] **multi-market**: 支持更多交易对

---

## 分配规则

**可并行 (Codex/子Agent):**
- sdk-tests
- sdk-docs  
- fe-websocket
- agent-stats
- position-history

**需要我 (主 Agent):**
- margin-system (核心逻辑)
- price-oracle (架构决策)
- solana-escrow (链上集成)
