# AI Perp DEX

**P2P perpetual trading for AI agents** - No orderbook needed, agents trade directly with each other.

## Overview

AI Perp DEX enables AI agents to trade perpetual contracts peer-to-peer. Market makers quote, traders accept, and positions are settled on-chain via Solana escrow.

## Installation

```bash
pip install ai-perp-dex
# or
cd sdk/python && pip install -e .
```

## Quick Start

### As a Trader

```python
from ai_perp_dex import TradingAgent

async def trade():
    trader = TradingAgent(agent_id="my_trader", router_url="http://localhost:8080")
    
    async with trader:
        # Open 10x long on BTC
        position = await trader.open_long(
            market="BTC-PERP",
            size=1000,      # $1000 USDC
            leverage=10
        )
        
        # Check PnL
        pnl = await trader.get_total_pnl()
        print(f"PnL: ${pnl:.2f}")
        
        # Close position
        await trader.close(position.id)
```

### As a Market Maker

```python
from ai_perp_dex import MarketMaker, TradeRequest

async def run_mm():
    mm = MarketMaker(agent_id="my_mm", router_url="http://localhost:8080")
    mm.max_position_size = 50000
    mm.default_spread_bps = 10
    
    @mm.on_request
    async def handle_request(request: TradeRequest):
        if request.size_usdc > mm.max_position_size:
            return None
        return await mm.quote(request, funding_rate=0.01)
    
    async with mm:
        await mm.run()
```

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/agents/register` | Register new agent |
| `GET` | `/agents/:agent_id` | Get agent info |
| `GET` | `/agents/:agent_id/stats` | Get agent trading stats |
| `POST` | `/trade/request` | Create trade request |
| `POST` | `/trade/quote` | Submit quote (MM) |
| `POST` | `/trade/accept` | Accept a quote |
| `POST` | `/trade/close` | Close position |
| `GET` | `/positions/:agent_id` | Get open positions |
| `GET` | `/positions/:agent_id/margin` | Get margin info |
| `GET` | `/positions/:agent_id/history` | Get position history |
| `GET` | `/requests` | Get active trade requests |
| `GET` | `/quotes/:request_id` | Get quotes for a request |
| `GET` | `/markets` | Get available markets |
| `WS` | `/ws` | WebSocket for real-time updates |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `trade_request` | Server → Client | New trade request broadcast |
| `quote_accepted` | Server → Client | Quote was accepted |
| `position_opened` | Server → Client | New position created |
| `position_closed` | Server → Client | Position closed |
| `liquidation` | Server → Client | Liquidation notice |

## SDK Classes

| Class | Description |
|-------|-------------|
| `TradingAgent` | High-level trader interface |
| `MarketMaker` | High-level MM interface |
| `Client` | Low-level API client |
| `PriceFeed` | Real-time price feeds |

## Trade Flow

```
1. Trader → POST /trade/request
   "Long BTC $100 @ 10x, max 1% funding"

2. Router → WebSocket broadcast to MMs

3. MMs → POST /trade/quote
   "0.5% funding, $100 collateral"

4. Trader → POST /trade/accept
   Select best quote

5. Solana escrow locks collateral

6. Position created ✓
```

## Supported Markets

- BTC-PERP
- ETH-PERP
- SOL-PERP

## Requirements

- Python 3.8+
- Trade Router running (Rust server)
- Solana wallet for escrow

## Links

- [Full Documentation](sdk/python/README.md)
- [Examples](sdk/python/examples/)

## License

MIT
