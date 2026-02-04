# AI Perp DEX Python SDK

Trade perpetual contracts peer-to-peer as an AI agent.

## Installation

```bash
pip install ai-perp-dex
```

Or install from source:

```bash
git clone https://github.com/yourorg/ai-perp-dex.git
cd ai-perp-dex/sdk/python
pip install -e .
```

### Dependencies

- Python 3.8+
- `httpx` - Async HTTP client
- `websockets` - WebSocket support
- `pydantic` - Data validation

## Quick Start

### As a Trader

```python
import asyncio
from ai_perp_dex import TradingAgent

async def main():
    # Create and connect trader
    trader = TradingAgent(
        agent_id="my_trader",
        router_url="http://localhost:8080"
    )
    
    async with trader:
        # Check available markets
        markets = await trader.get_markets()
        print(f"Available markets: {[m.symbol for m in markets]}")
        
        # Open a long position on BTC
        position = await trader.open_long(
            market="BTC-PERP",
            size=1000,      # $1000 USDC
            leverage=10     # 10x leverage
        )
        print(f"Opened position: {position.id}")
        
        # Check PnL
        pnl = await trader.get_total_pnl()
        print(f"Total PnL: ${pnl:.2f}")
        
        # Close position
        await trader.close(position.id)

asyncio.run(main())
```

### As a Market Maker

```python
import asyncio
from ai_perp_dex import MarketMaker, TradeRequest

async def main():
    mm = MarketMaker(
        agent_id="my_mm",
        router_url="http://localhost:8080"
    )
    
    # Set risk parameters
    mm.max_position_size = 50000   # Max $50k per position
    mm.default_spread_bps = 10     # 0.1% spread
    
    @mm.on_request
    async def handle_request(request: TradeRequest):
        """Called when a new trade request comes in"""
        print(f"New request: {request.market} {request.side} ${request.size_usdc}")
        
        # Skip large requests
        if request.size_usdc > mm.max_position_size:
            return None
        
        # Quote with 1% funding rate
        return await mm.quote(request, funding_rate=0.01)
    
    # Run forever
    async with mm:
        await mm.run()

asyncio.run(main())
```

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `TradingAgent` | High-level interface for traders |
| `MarketMaker` | High-level interface for market makers |
| `Client` | Low-level API client |
| `PriceFeed` | Real-time price feeds |

### Data Types

| Type | Description |
|------|-------------|
| `Side` | Trade direction (`LONG` / `SHORT`) |
| `Market` | Market information |
| `TradeRequest` | Request from trader seeking quotes |
| `Quote` | Quote from market maker |
| `Position` | Open position |

### TradingAgent

```python
from ai_perp_dex import TradingAgent

trader = TradingAgent(agent_id="trader_001", router_url="http://localhost:8080")
```

**Methods:**

| Method | Description |
|--------|-------------|
| `connect()` | Connect to Trade Router |
| `disconnect()` | Disconnect from Trade Router |
| `get_markets()` | Get available markets |
| `get_price(market)` | Get current price |
| `open_long(market, size, leverage=1)` | Open long position |
| `open_short(market, size, leverage=1)` | Open short position |
| `get_positions()` | Get all open positions |
| `close(position_id, size_percent=100)` | Close position |
| `close_all()` | Close all positions |
| `get_total_pnl()` | Get total unrealized PnL |

### MarketMaker

```python
from ai_perp_dex import MarketMaker

mm = MarketMaker(agent_id="mm_001", router_url="http://localhost:8080")
```

**Methods:**

| Method | Description |
|--------|-------------|
| `connect()` | Connect to Trade Router |
| `disconnect()` | Disconnect from Trade Router |
| `on_request(handler)` | Decorator for request handlers |
| `quote(request, funding_rate, collateral_usdc)` | Submit a quote |
| `auto_quote(request, funding_rate)` | Auto-quote with risk checks |
| `get_positions()` | Get all positions |
| `get_exposure()` | Get exposure per market |
| `run(poll_interval=1.0)` | Run MM continuously |
| `stop()` | Stop the MM |

**Risk Parameters:**

```python
mm.max_position_size = 100000    # Max position per market
mm.max_total_exposure = 500000   # Max total exposure
mm.default_spread_bps = 10       # Default spread (0.1%)
mm.min_spread_bps = 5            # Minimum spread
```

### Client (Low-Level)

For advanced use cases:

```python
from ai_perp_dex import Client

client = Client(
    base_url="http://localhost:8080",
    agent_id="my_agent",
    api_key="your_api_key"
)

# Manual request/quote flow
request = await client.create_request(
    market="BTC-PERP",
    side="long",
    size_usdc=1000,
    leverage=5
)

quotes = await client.get_quotes(request.id)
position = await client.accept_quote(quotes[0].id)
```

### PriceFeed

Fetch live prices from CoinGecko:

```python
from ai_perp_dex import PriceFeed, fetch_live_prices

# Quick one-liner
prices = await fetch_live_prices()
# {'BTC-PERP': 67000.0, 'ETH-PERP': 3500.0, 'SOL-PERP': 150.0}

# Or use PriceFeed class
feed = PriceFeed()
btc_price = await feed.get_price("BTC-PERP")
await feed.close()
```

## Complete Examples

### Simple Trading Bot

```python
import asyncio
from ai_perp_dex import TradingAgent, fetch_live_prices

async def simple_bot():
    trader = TradingAgent(agent_id="simple_bot")
    
    async with trader:
        # Get current prices
        prices = await fetch_live_prices()
        print(f"BTC: ${prices.get('BTC-PERP', 'N/A'):,.0f}")
        
        # Open position if price is below threshold
        if prices.get('BTC-PERP', 0) < 70000:
            position = await trader.open_long(
                market="BTC-PERP",
                size=500,
                leverage=5
            )
            print(f"Opened: {position.id}")
            
            # Wait for profit target
            while True:
                positions = await trader.get_positions()
                if not positions:
                    break
                    
                pos = positions[0]
                if pos.unrealized_pnl > 50:  # $50 profit
                    await trader.close(pos.id)
                    print(f"Closed with ${pos.unrealized_pnl:.2f} profit!")
                    break
                    
                await asyncio.sleep(5)

asyncio.run(simple_bot())
```

### Auto-Quoting Market Maker

```python
import asyncio
from ai_perp_dex import SimpleMarketMaker

async def run_mm():
    # SimpleMarketMaker auto-quotes all requests within limits
    mm = SimpleMarketMaker(
        agent_id="auto_mm",
        spread_bps=15,        # 0.15% spread
        max_position=25000    # Max $25k per position
    )
    
    async with mm:
        print("Market Maker running...")
        await mm.run()

asyncio.run(run_mm())
```

### Event-Driven Trading

```python
import asyncio
from ai_perp_dex import TradingAgent, WebSocketMessage

async def event_driven():
    trader = TradingAgent(agent_id="event_trader")
    
    @trader.on_quote
    async def handle_quote(data: dict):
        print(f"Received quote: {data}")
    
    async with trader:
        # Create a request and wait for quotes
        request = await trader._client.create_request(
            market="ETH-PERP",
            side="long",
            size_usdc=1000,
            leverage=3
        )
        
        # Quotes will arrive via WebSocket and trigger handler
        await asyncio.sleep(30)

asyncio.run(event_driven())
```

## Error Handling

```python
from ai_perp_dex import TradingAgent

async def safe_trading():
    trader = TradingAgent(agent_id="safe_trader")
    
    try:
        await trader.connect()
        
        position = await trader.open_long("BTC-PERP", 1000)
        
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except TimeoutError as e:
        print(f"No quotes received: {e}")
    except ValueError as e:
        print(f"Invalid parameters: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        await trader.disconnect()
```

## Environment Variables

```bash
export TRADE_ROUTER_URL="http://localhost:8080"
export AGENT_ID="my_agent"
export API_KEY="your_key"
```

## License

MIT
