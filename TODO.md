# AI Perp DEX - TODO List

## 🔴 P0 - 核心功能 (必须)

### Backend
- [x] ~~**margin-system**: 保证金计算 + 强平逻辑~~ ✅
- [x] ~~**price-oracle**: 实时价格 (CoinGecko 30s 更新)~~ ✅
- [ ] **rate-limiting**: API 限流防滥用
- [x] ~~**liquidation-engine**: 自动强平检测~~ ✅

### SDK  
- [x] ~~**sdk-tests**: 完整单元测试~~ ✅ (53 tests)
- [x] ~~**sdk-docs**: API 文档 + 使用示例~~ ✅ (1000+ 行)

### Frontend
- [x] ~~**fe-websocket**: 实时数据更新~~ ✅
- [x] ~~**fe-trading**: 交易界面~~ ✅

---

## 🟡 P1 - 增强功能

- [x] ~~**agent-stats**: Agent 交易统计~~ ✅
- [x] ~~**position-history**: 历史仓位查询 API~~ ✅
- [ ] **funding-settlement**: 定时结算 funding rate
- [ ] **risk-limits**: 单 Agent 风险限额

---

## 🟢 P2 - 生态集成

- [ ] **solana-escrow**: 链上资金托管
- [ ] **moltmarket-skill**: 打包成 MoltMarket skill
- [ ] **multi-market**: 支持更多交易对

---

## 进度统计
- 完成: 10/15 (67%)
- 待办: 5
