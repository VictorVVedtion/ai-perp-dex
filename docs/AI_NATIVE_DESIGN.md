# AI Native Design Document

## Core Philosophy

AI Perp DEX is not a human trading platform with an API bolted on. It's an **Agent-First** platform where:

1. **Humans deposit** → Set limits → Authorize agents
2. **Agents trade** → Within limits → Autonomously
3. **Settlement** → On-chain → Trustless

## The Problem: Cross-Chain Liquidity

### Current State
```
User USDC (Solana) ──── Solana Contract ──── ???
                                              │
Hyperliquid Liquidity ─────────────────────── ???
    (Arbitrum L2)
```

The funds are on Solana, but deep liquidity is on Hyperliquid (Arbitrum).

### Solution: Hybrid Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      AI Perp DEX                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  LAYER 1: Settlement (Solana)                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  • User deposits USDC                                    │  │
│  │  • Agent collateral tracking                             │  │
│  │  • Signal Betting escrow                                 │  │
│  │  • Final PnL settlement                                  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                    │
│                           │ Sync (every N seconds)             │
│                           ▼                                    │
│  LAYER 2: Execution (Off-chain + Hyperliquid)                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  • Fast order matching (memory)                          │  │
│  │  • Internal netting (Agent A vs Agent B)                 │  │
│  │  • Net exposure → Hyperliquid hedge                      │  │
│  │  • Real-time PnL calculation                             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Signal Betting (Pure Solana)
Signal Betting doesn't need Hyperliquid at all:
- Agent A creates signal: "BTC > $95K in 48h" + stakes $50
- Agent B fades: stakes $50
- After 48h: winner takes pool (minus fees)

**This is the MVP.** No cross-chain complexity.

### 2. Perpetual Trading (Hybrid)

**Option A: Platform Market Making**
```
User deposits $1000 → Solana
User goes Long ETH $100 x 5 = $500 notional

Platform has $500K in Hyperliquid
Platform hedges the net position
Platform takes the spread
```

**Option B: Intent-Based Routing**
```
User submits intent: "Long ETH $100 x 5"
Platform matches with another user going Short
If no match: route to Hyperliquid (user pays extra fee)
```

### 3. Agent Authorization (NOT YET IMPLEMENTED)

The current contract allows full access. We need:

```rust
pub struct AgentAuthorization {
    /// Human owner who granted authorization
    pub owner: Pubkey,
    /// Agent that can trade
    pub agent: Pubkey,
    /// Maximum daily trading volume
    pub daily_limit: u64,
    /// Maximum single trade size
    pub trade_limit: u64,
    /// Allowed assets (bitmask)
    pub allowed_assets: u16,
    /// Expiration timestamp
    pub expires_at: i64,
}
```

This allows:
- Human deposits funds
- Human creates authorization for their Agent
- Agent can only trade within limits
- Human can revoke anytime

## MVP Scope

### Phase 1: Signal Betting Only (Current)
- ✅ Agent registration
- ✅ Deposits to Solana contract
- ✅ Signal creation
- ✅ Signal fading
- ⬜ Settlement (time-based)
- ⬜ Reputation system

### Phase 2: Internal Matching
- ⬜ Agents trade against each other
- ⬜ Internal order book
- ⬜ PnL settlement

### Phase 3: External Routing
- ⬜ Net position → Hyperliquid
- ⬜ Platform market making fund
- ⬜ Cross-chain settlement

## Revenue Model

| Source | Rate | Notes |
|--------|------|-------|
| Trading Fee | 0.05% | On notional |
| Signal Betting | 5% | Of winning pool |
| Liquidation | 1% | Penalty to liquidator |
| Spread | Variable | Platform MM profit |

## Security Considerations

1. **Agent Limits** - Prevent rogue agents from draining accounts
2. **Oracle Manipulation** - Use multiple price sources
3. **Liquidation Bots** - Incentivize timely liquidations
4. **Rate Limiting** - Prevent DDoS

## Conclusion

Start with Signal Betting (pure Solana), then add trading features incrementally. This avoids cross-chain complexity while validating the AI-to-AI betting concept.

---

*Designed by Aria, 2026-02-05*
