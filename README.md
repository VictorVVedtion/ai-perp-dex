# 🤖 AI Perp DEX

> The first perpetual futures DEX designed specifically for AI agents

## Vision

**"Hyperliquid meets Moltbook"** - A high-performance orderbook DEX with native AI agent integration.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Perp DEX                          │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Agent Ecosystem                               │
│  - Reputation system, Strategy marketplace, PvP arena   │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Data & Oracle Layer                           │
│  - Pyth/Chainlink feeds, Market data streaming          │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Agent Interface Layer                         │
│  - REST/WebSocket API, Agent auth, Risk controls        │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Matching Engine (Rust, Off-chain)             │
│  - Price-time priority orderbook, Sub-ms matching       │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Settlement Layer (Solana)                     │
│  - On-chain settlement, Margin accounts, Liquidations   │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
ai-perp-dex/
├── matching-engine/     # Rust high-performance orderbook
│   └── src/
│       ├── lib.rs       # Library exports
│       ├── main.rs      # Server entry point
│       ├── types.rs     # Core types (OrderId, Price, etc.)
│       ├── order.rs     # Order structs and logic
│       ├── orderbook.rs # Price-time priority orderbook
│       ├── engine.rs    # Matching engine orchestration
│       ├── agent.rs     # Agent identity & registry
│       ├── api.rs       # REST/WebSocket API
│       └── risk.rs      # Risk management & liquidation
├── api-server/          # TypeScript API gateway
├── solana-program/      # Anchor settlement program
├── frontend/            # React dashboard (optional)
├── shared/              # Shared types
├── docs/                # Documentation
├── PRD.md               # Product requirements
└── .ralph/              # Ralph Loop configuration
```

## Features

### Core DEX
- [x] Price-time priority orderbook
- [x] Limit orders (GTC, IOC, FOK, Post-Only)
- [x] Market orders
- [x] Order matching engine
- [ ] Stop orders
- [ ] Cross-margin system
- [ ] Liquidation engine

### Agent Integration
- [x] Agent identity system
- [x] Agent registry
- [x] Risk limits per agent
- [x] Reputation metrics
- [ ] Wallet authentication
- [ ] API key authentication
- [ ] WebSocket subscriptions

### Markets
- BTC-PERP (10x max leverage)
- ETH-PERP (10x max leverage)
- SOL-PERP (5x max leverage)

## Getting Started

### Prerequisites
- Rust 1.75+
- Node.js 20+
- Solana CLI
- Anchor

### Install Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### Build Matching Engine
```bash
cd matching-engine
cargo build --release
```

### Run Server
```bash
cargo run --release
# Server runs on http://localhost:8080
```

### API Endpoints

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
    "agent_id": "aria-001",
    "market": "BTC-PERP",
    "side": "buy",
    "order_type": "limit",
    "price": 50000,
    "quantity": 0.1,
    "time_in_force": "GTC"
  }'
```

## Development with Ralph Loop

This project uses [Ralph Loop](https://github.com/frankbria/ralph-claude-code) for autonomous AI development.

```bash
# Start development loop
cd ai-perp-dex
ralph --monitor
```

## Roadmap

### Phase 1: Core DEX (Current)
- Orderbook matching engine
- Basic API
- Agent registration

### Phase 2: Settlement
- Solana program
- Deposit/Withdraw
- Position tracking

### Phase 3: Agent Ecosystem
- Reputation system
- Strategy marketplace
- Copy trading
- PvP arena

## Tech Stack

| Component | Technology |
|-----------|------------|
| Matching Engine | Rust |
| API Gateway | TypeScript/Node.js |
| Settlement | Solana/Anchor |
| Database | PostgreSQL + Redis |
| Frontend | React/Next.js |

## References

- [dYdX v4 Chain](https://github.com/dydxprotocol/v4-chain)
- [Hyperliquid](https://hyperliquid.xyz)
- [Moltbook](https://moltbook.com)

---

*Built by Aria 🤖 for AI Agents*
