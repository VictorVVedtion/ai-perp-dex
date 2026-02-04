# 🤖 AI Perp DEX

> The first perpetual futures DEX designed specifically for AI agents

## Vision

**"Hyperliquid meets Moltbook"** - A high-performance orderbook DEX with native AI agent integration.

## ✅ Project Status

| Component | Status | Description |
|-----------|--------|-------------|
| Matching Engine | ✅ Complete | Rust high-performance orderbook |
| Solana Program | ✅ Complete | Anchor settlement program |
| TypeScript SDK | ✅ Complete | Client library with all methods |
| Oracle Integration | 🚧 Code Ready | Pyth integration (pending toolchain update) |
| Frontend | ✅ Complete | Next.js + TailwindCSS |
| Devnet Deploy | ⏳ Pending | Awaiting airdrop rate limit reset |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Perp DEX                          │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Frontend (Next.js + TailwindCSS)              │
│  - Market listing, Trading UI, Portfolio, Wallet        │
├─────────────────────────────────────────────────────────┤
│  Layer 4: TypeScript SDK                                │
│  - AiPerpDexClient, Types, PDA helpers                  │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Oracle Layer (Pyth Network)                   │
│  - BTC/USD, ETH/USD, SOL/USD price feeds               │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Matching Engine (Rust, Off-chain)             │
│  - Price-time priority orderbook, Sub-ms matching       │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Settlement Layer (Solana/Anchor)              │
│  - On-chain settlement, Margin accounts, Liquidations   │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
ai-perp-dex/
├── matching-engine/     # Rust high-performance orderbook ✅
│   └── src/
│       ├── orderbook.rs # Price-time priority orderbook
│       ├── engine.rs    # Matching engine
│       ├── agent.rs     # Agent identity & registry
│       └── api.rs       # REST/WebSocket API
├── solana-program/      # Anchor settlement program ✅
│   └── programs/ai-perp-dex/
│       └── src/
│           ├── lib.rs           # Program entry
│           ├── state.rs         # Account structures
│           ├── instructions/    # All instructions
│           ├── oracle.rs        # Pyth price parsing
│           └── errors.rs        # Custom errors
├── sdk/                 # TypeScript SDK ✅
│   └── src/
│       ├── client.ts    # AiPerpDexClient class
│       ├── types.ts     # TypeScript types
│       └── pdas.ts      # PDA derivation helpers
├── frontend/            # Next.js dashboard ✅
│   └── src/
│       ├── app/         # Pages (home, trade, portfolio)
│       ├── components/  # UI components
│       └── providers.tsx # Wallet providers
├── docs/                # Documentation
│   ├── DEPLOYMENT.md    # Devnet deployment guide
│   └── ORACLE.md        # Oracle integration docs
└── PRD.md               # Product requirements
```

## Quick Start

### 1. Matching Engine
```bash
cd matching-engine
cargo build --release
cargo run --release
# Server runs on http://localhost:8080
```

### 2. TypeScript SDK
```bash
cd sdk
npm install
npm run build

# Example usage
npx ts-node examples/basic-usage.ts
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

## Solana Program

**Program ID:** `GsHk7vwtvtg7BpURNmqjFApezFvJpixS5enNUYFe1iAk`

### Instructions

| Instruction | Description |
|-------------|-------------|
| `initialize` | Initialize exchange with fee rate |
| `register_agent` | Register new trading agent |
| `deposit` | Deposit USDC collateral |
| `withdraw` | Withdraw collateral |
| `open_position` | Open leveraged position |
| `close_position` | Close position at price |
| `liquidate` | Liquidate underwater position |
| `settle_pnl` | Settle realized PnL |
| `create_market` | Create market with oracle |
| `update_position_pnl` | Update PnL from oracle |

### SDK Usage

```typescript
import { AiPerpDexClient, MarketIndex } from "@ai-perp-dex/sdk";

// Create client
const client = AiPerpDexClient.fromKeypair(connection, keypair);

// Register agent
await client.registerAgent("MyAgent");

// Deposit collateral
await client.deposit(1000); // 1000 USDC

// Open position
await client.openPosition(MarketIndex.BTC, 0.1, 95000);

// Close position
await client.closePosition(MarketIndex.BTC, 96000);
```

## Markets

| Market | Symbol | Max Leverage | Initial Margin |
|--------|--------|--------------|----------------|
| Bitcoin | BTC-PERP | 10x | 10% |
| Ethereum | ETH-PERP | 10x | 10% |
| Solana | SOL-PERP | 10x | 10% |

## API Endpoints

### REST API (Matching Engine)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /markets | List markets |
| GET | /markets/:market/orderbook | Get orderbook |
| GET | /markets/:market/bbo | Get best bid/offer |
| POST | /orders | Place order |
| DELETE | /orders/:id | Cancel order |
| WS | /ws | Real-time updates |

### Place Order Example
```bash
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-001",
    "market": "BTC-PERP",
    "side": "buy",
    "order_type": "limit",
    "price": 95000,
    "quantity": 0.1,
    "time_in_force": "GTC"
  }'
```

## Oracle Integration (Pyth Network)

| Market | Pyth Devnet Feed |
|--------|------------------|
| BTC/USD | `HovQMDrbAgAYPCmHVSrezcSmkMtXSSUsLDFANExrZh2J` |
| ETH/USD | `EdVCmQ9FSPcVe5YySXDPCRmc8aDQLKJ9xvYBMZPie1Vw` |
| SOL/USD | `J83w4HKfqxwcq3BEMMkPFSppX3gqekLyLJBexebFVkix` |

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions.

```bash
# Configure Solana CLI
solana config set --url devnet

# Airdrop SOL
solana airdrop 2

# Deploy program
cd solana-program
anchor deploy --provider.cluster devnet
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Matching Engine | Rust |
| Settlement | Solana/Anchor |
| SDK | TypeScript |
| Frontend | Next.js + TailwindCSS |
| Wallet | Phantom, Solflare |
| Oracle | Pyth Network |

## Known Issues

1. **Solana Program Build**: Currently blocked by `constant_time_eq v0.4.2` requiring edition2024, which isn't supported by SBF toolchain (Rust 1.84). Code is complete; awaiting toolchain update.

2. **Devnet Airdrop**: Rate limited. Use https://faucet.solana.com/ for manual SOL requests.

## Roadmap

### Phase 1: Core DEX ✅
- [x] Orderbook matching engine
- [x] Solana settlement program
- [x] TypeScript SDK
- [x] Basic frontend

### Phase 2: Production Ready 🔄
- [ ] Devnet deployment
- [ ] Oracle integration (pending toolchain)
- [ ] Cross-margin system
- [ ] Stop/Take-profit orders

### Phase 3: Agent Ecosystem
- [ ] Reputation system
- [ ] Strategy marketplace
- [ ] Copy trading
- [ ] PvP arena

## License

MIT

---

*Built for AI Agents 🤖*
