# AI Perp DEX Python SDK - API Reference

Complete API documentation for all classes, methods, and types.

---

## Table of Contents

- [Types](#types)
  - [Side](#side)
  - [Market](#market)
  - [TradeRequest](#traderequest)
  - [Quote](#quote)
  - [Position](#position)
  - [AgentInfo](#agentinfo)
  - [WebSocketMessage](#websocketmessage)
- [TradingAgent](#tradingagent)
- [MarketMaker](#marketmaker)
- [SimpleMarketMaker](#simplemarketmaker)
- [Client](#client)
- [PriceFeed](#pricefeed)
- [Helper Functions](#helper-functions)
- [Exceptions](#exceptions)

---

## Types

### Side

Trade direction enum.

```python
from ai_perp_dex import Side

Side.LONG   # "long" - Buy/bullish position
Side.SHORT  # "short" - Sell/bearish position
```

**Values:**
| Value | String | Description |
|-------|--------|-------------|
| `LONG` | `"long"` | Long position (profit when price rises) |
| `SHORT` | `"short"` | Short position (profit when price falls) |

---

### Market

Market information model.

```python
from ai_perp_dex import Market

market = Market(
    symbol="BTC-PERP",
    base_asset="BTC",
    quote_asset="USD",
    price=67000.0,
    volume_24h=1000000.0,
    open_interest=5000000.0,
    funding_rate=0.0001,
    max_leverage=50
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | `str` | required | Market symbol (e.g., "BTC-PERP") |
| `base_asset` | `str` | required | Base asset (e.g., "BTC") |
| `quote_asset` | `str` | `"USD"` | Quote asset |
| `price` | `float` | required | Current market price |
| `volume_24h` | `float` | `0` | 24-hour trading volume |
| `open_interest` | `float` | `0` | Total open interest |
| `funding_rate` | `float` | `0` | Current funding rate |
| `max_leverage` | `int` | `50` | Maximum allowed leverage |

---

### TradeRequest

A request from a trader seeking quotes from market makers.

```python
from ai_perp_dex import TradeRequest, Side

request = TradeRequest(
    id="req_123",
    agent_id="trader_001",
    market="BTC-PERP",
    side=Side.LONG,
    size_usdc=1000.0,
    leverage=5,
    max_slippage_bps=100,
    status="pending"
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | auto-generated | Unique request ID |
| `agent_id` | `str` | required | Trader's agent ID |
| `market` | `str` | required | Market symbol |
| `side` | `Side` | required | Trade direction |
| `size_usdc` | `float` | required | Position size in USDC |
| `leverage` | `int` | `1` | Leverage multiplier |
| `max_slippage_bps` | `int` | `100` | Max slippage in basis points (100 = 1%) |
| `status` | `str` | `"pending"` | Request status |
| `created_at` | `datetime` | now | Creation timestamp |
| `expires_at` | `datetime` | `None` | Expiration timestamp |
| `quotes_count` | `int` | `0` | Number of quotes received |

---

### Quote

A quote from a market maker responding to a trade request.

```python
from ai_perp_dex import Quote

quote = Quote(
    id="quote_456",
    request_id="req_123",
    agent_id="mm_001",
    funding_rate=0.01,
    collateral_usdc=100.0
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | auto-generated | Unique quote ID |
| `request_id` | `str` | required | Associated request ID |
| `agent_id` | `str` | required | Market maker's agent ID |
| `funding_rate` | `float` | required | Funding rate offered |
| `collateral_usdc` | `float` | required | Collateral amount in USDC |
| `valid_until` | `datetime` | `None` | Quote expiration time |
| `created_at` | `datetime` | now | Creation timestamp |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `mm_id` | `str` | Alias for `agent_id` |

---

### Position

An open position between a trader and market maker.

```python
from ai_perp_dex import Position, Side

position = Position(
    id="pos_789",
    trader_id="trader_001",
    mm_id="mm_001",
    market="BTC-PERP",
    side=Side.LONG,
    size_usdc=1000.0,
    entry_price=67000.0,
    mark_price=67500.0,
    leverage=5,
    unrealized_pnl=37.31,
    created_at=datetime.utcnow()
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | required | Unique position ID |
| `trader_id` | `str` | required | Trader's agent ID |
| `mm_id` | `str` | required | Market maker's agent ID |
| `market` | `str` | required | Market symbol |
| `side` | `Side` | required | Position direction |
| `size_usdc` | `float` | required | Position size in USDC |
| `entry_price` | `float` | required | Entry price |
| `mark_price` | `float` | `None` | Current mark price |
| `leverage` | `int` | `1` | Leverage used |
| `unrealized_pnl` | `float` | `0` | Unrealized profit/loss |
| `created_at` | `datetime` | required | Opening timestamp |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_profitable` | `bool` | `True` if `unrealized_pnl > 0` |

---

### AgentInfo

Information about an agent on the network.

```python
from ai_perp_dex.types import AgentInfo

agent = AgentInfo(
    id="agent_001",
    agent_type="trader",
    is_online=True,
    total_volume=50000.0,
    total_pnl=1250.0,
    trade_count=42
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | required | Agent ID |
| `agent_type` | `str` | required | Type: `"trader"` or `"mm"` |
| `is_online` | `bool` | `False` | Online status |
| `total_volume` | `float` | `0` | Total trading volume |
| `total_pnl` | `float` | `0` | Total realized PnL |
| `trade_count` | `int` | `0` | Number of trades |

---

### WebSocketMessage

Message received via WebSocket.

```python
from ai_perp_dex.types import WebSocketMessage

msg = WebSocketMessage(
    type="quote",
    data={"request_id": "req_123", "price": 67000.0}
)
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `str` | required | Message type |
| `data` | `dict` | required | Message payload |
| `timestamp` | `datetime` | now | Receive timestamp |

**Message Types:**

| Type | Description |
|------|-------------|
| `"request"` | New trade request |
| `"quote"` | New quote received |
| `"fill"` | Position opened |
| `"close"` | Position closed |
| `"heartbeat"` | Connection keepalive |

---

## TradingAgent

High-level interface for AI trading agents.

### Constructor

```python
TradingAgent(
    agent_id: str,
    router_url: str = "http://localhost:8080",
    private_key: Optional[str] = None
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | `str` | required | Unique agent identifier |
| `router_url` | `str` | `"http://localhost:8080"` | Trade Router URL |
| `private_key` | `str` | `None` | Private key for signing (future) |

### Methods

#### connect()

Connect to the Trade Router.

```python
await trader.connect()
```

**Raises:**
- `ConnectionError` - If Trade Router is not healthy

---

#### disconnect()

Disconnect from Trade Router.

```python
await trader.disconnect()
```

---

#### get_markets()

Get available markets.

```python
markets: List[Market] = await trader.get_markets()
```

**Returns:** `List[Market]` - Available markets

---

#### get_price()

Get current price for a market.

```python
price: float = await trader.get_price("BTC-PERP")
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `market` | `str` | Market symbol |

**Returns:** `float` - Current price

**Raises:**
- `ValueError` - If market not found

---

#### open_long()

Open a long position.

```python
position: Position = await trader.open_long(
    market="BTC-PERP",
    size=1000,
    leverage=10,
    max_slippage_bps=100,
    wait_for_fill=True,
    timeout=30.0
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `market` | `str` | required | Market symbol |
| `size` | `float` | required | Position size in USDC |
| `leverage` | `int` | `1` | Leverage (1-50) |
| `max_slippage_bps` | `int` | `100` | Max slippage in bps |
| `wait_for_fill` | `bool` | `True` | Wait for position fill |
| `timeout` | `float` | `30.0` | Timeout in seconds |

**Returns:** `Position` - The opened position

**Raises:**
- `TimeoutError` - If no quotes received within timeout

---

#### open_short()

Open a short position. Same parameters as `open_long()`.

```python
position: Position = await trader.open_short("BTC-PERP", size=1000, leverage=5)
```

---

#### get_positions()

Get all open positions.

```python
positions: List[Position] = await trader.get_positions()
```

**Returns:** `List[Position]` - Open positions

---

#### get_position()

Get a specific position by ID.

```python
position: Optional[Position] = await trader.get_position("pos_123")
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `position_id` | `str` | Position ID |

**Returns:** `Optional[Position]` - Position or `None` if not found

---

#### close()

Close a position (partially or fully).

```python
result: dict = await trader.close(
    position_id="pos_123",
    size_percent=100
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `position_id` | `str` | required | Position to close |
| `size_percent` | `int` | `100` | Percentage to close (1-100) |

**Returns:** `dict` - Close result with PnL info

---

#### close_all()

Close all open positions.

```python
results: List[dict] = await trader.close_all()
```

**Returns:** `List[dict]` - Results for each closed position

---

#### get_total_pnl()

Get total unrealized PnL across all positions.

```python
pnl: float = await trader.get_total_pnl()
```

**Returns:** `float` - Total unrealized PnL in USDC

---

#### on_quote()

Decorator to register a quote handler.

```python
@trader.on_quote
async def handle_quote(data: dict):
    print(f"New quote: {data}")
```

---

### Context Manager

TradingAgent supports async context manager:

```python
async with TradingAgent(agent_id="my_trader") as trader:
    # Automatically connects and disconnects
    positions = await trader.get_positions()
```

---

## MarketMaker

High-level interface for AI market maker agents.

### Constructor

```python
MarketMaker(
    agent_id: str,
    router_url: str = "http://localhost:8080",
    private_key: Optional[str] = None
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | `str` | required | Unique agent identifier |
| `router_url` | `str` | `"http://localhost:8080"` | Trade Router URL |
| `private_key` | `str` | `None` | Private key for signing (future) |

### Attributes (Risk Parameters)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_position_size` | `float` | `100000` | Max position per market |
| `max_total_exposure` | `float` | `500000` | Max total exposure |
| `default_spread_bps` | `int` | `10` | Default spread (0.1%) |
| `min_spread_bps` | `int` | `5` | Minimum spread |

### Methods

#### connect()

Connect to Trade Router.

```python
await mm.connect()
```

**Raises:**
- `ConnectionError` - If Trade Router is not healthy

---

#### disconnect()

Disconnect from Trade Router.

```python
await mm.disconnect()
```

---

#### on_request()

Decorator to register a request handler.

```python
@mm.on_request
async def handle_request(request: TradeRequest) -> Optional[Quote]:
    if request.size_usdc > 10000:
        return None  # Don't quote large requests
    
    return await mm.quote(request, funding_rate=0.01)
```

**Handler Signature:**
```python
async def handler(request: TradeRequest) -> Optional[Quote]
```

- Return a `Quote` to respond to the request
- Return `None` to skip the request

---

#### quote()

Submit a quote for a trade request.

```python
quote: Quote = await mm.quote(
    request=request,
    funding_rate=0.01,
    collateral_usdc=100.0
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `request` | `TradeRequest` | required | Trade request to quote |
| `funding_rate` | `float` | `0.01` | Funding rate (1% = 0.01) |
| `collateral_usdc` | `float` | `size/10` | Collateral amount |

**Returns:** `Quote` - The submitted quote

---

#### auto_quote()

Automatically quote a request with risk checks.

```python
quote: Optional[Quote] = await mm.auto_quote(
    request=request,
    funding_rate=0.01
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `request` | `TradeRequest` | required | Trade request |
| `funding_rate` | `float` | `0.01` | Funding rate |

**Returns:** `Optional[Quote]` - Quote if passes risk checks, else `None`

---

#### get_positions()

Get all open positions.

```python
positions: List[Position] = await mm.get_positions()
```

---

#### get_exposure()

Get current exposure per market.

```python
exposure: Dict[str, float] = await mm.get_exposure()
# {'BTC-PERP': 5000.0, 'ETH-PERP': -2000.0}
```

**Returns:** `Dict[str, float]` - Net exposure per market (positive = long, negative = short)

---

#### get_total_exposure()

Get total absolute exposure.

```python
total: float = await mm.get_total_exposure()
```

**Returns:** `float` - Sum of absolute exposures

---

#### run()

Run the market maker continuously.

```python
await mm.run(poll_interval=1.0)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `poll_interval` | `float` | `1.0` | Seconds between polls |

This method:
1. Polls for new trade requests
2. Calls registered handlers
3. Updates market prices cache

---

#### stop()

Stop the market maker.

```python
mm.stop()
```

---

### Context Manager

```python
async with MarketMaker(agent_id="my_mm") as mm:
    @mm.on_request
    async def handler(request):
        return await mm.auto_quote(request)
    
    await mm.run()
```

---

## SimpleMarketMaker

A simplified market maker that auto-quotes all requests within risk limits.

### Constructor

```python
SimpleMarketMaker(
    agent_id: str,
    router_url: str = "http://localhost:8080",
    spread_bps: int = 10,
    max_position: float = 50000
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | `str` | required | Unique agent identifier |
| `router_url` | `str` | `"http://localhost:8080"` | Trade Router URL |
| `spread_bps` | `int` | `10` | Spread in basis points |
| `max_position` | `float` | `50000` | Max position size |

### Example

```python
from ai_perp_dex import SimpleMarketMaker

mm = SimpleMarketMaker(
    agent_id="auto_mm",
    spread_bps=15,
    max_position=25000
)

async with mm:
    await mm.run()
```

---

## Client

Low-level client for Trade Router API. Use this for advanced control.

### Constructor

```python
Client(
    base_url: str = "http://localhost:8080",
    ws_url: Optional[str] = None,
    agent_id: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `"http://localhost:8080"` | Trade Router HTTP URL |
| `ws_url` | `str` | `None` | WebSocket URL (auto-derived if not set) |
| `agent_id` | `str` | `None` | Agent identifier |
| `api_key` | `str` | `None` | API key for authentication |
| `timeout` | `float` | `30.0` | HTTP request timeout |

### HTTP Methods

#### health()

Check Trade Router health.

```python
result: dict = await client.health()
# {'status': 'healthy', 'version': '0.1.0'}
```

---

#### register()

Register agent and get API key.

```python
result: dict = await client.register(
    name="My Trading Bot",
    is_mm=False
)
# {'success': True, 'data': {'api_key': 'xxx...'}}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `None` | Display name |
| `is_mm` | `bool` | `False` | Is market maker |

---

#### get_markets()

```python
markets: List[Market] = await client.get_markets()
```

---

#### get_requests()

Get trade requests.

```python
requests: List[TradeRequest] = await client.get_requests(status="pending")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `str` | `None` | Filter by status |

---

#### get_quotes()

Get quotes for a request.

```python
quotes: List[Quote] = await client.get_quotes(request_id="req_123")
```

---

#### get_positions()

```python
positions: List[Position] = await client.get_positions(agent_id="trader_001")
```

---

#### create_request()

Create a trade request.

```python
request: TradeRequest = await client.create_request(
    market="BTC-PERP",
    side="long",
    size_usdc=1000,
    leverage=5,
    max_funding_rate=0.01,
    expires_in=300
)
```

---

#### create_quote()

Submit a quote.

```python
quote: Quote = await client.create_quote(
    request_id="req_123",
    funding_rate=0.01,
    collateral_usdc=100,
    valid_for=300
)
```

---

#### accept_quote()

Accept a quote and open position.

```python
position: Position = await client.accept_quote(
    quote_id="quote_456",
    request_id="req_123"
)
```

---

#### close_position()

Close a position.

```python
result: dict = await client.close_position(
    position_id="pos_789",
    size_percent=100
)
```

---

### WebSocket Methods

#### connect_ws()

Connect to WebSocket.

```python
await client.connect_ws()
```

---

#### on_message()

Register WebSocket message handler.

```python
@client.on_message
async def handler(msg: WebSocketMessage):
    print(f"Type: {msg.type}, Data: {msg.data}")
```

---

#### close()

Close all connections.

```python
await client.close()
```

---

## PriceFeed

Real-time price feeds from CoinGecko.

### Class Attributes

| Attribute | Value | Description |
|-----------|-------|-------------|
| `COINGECKO_URL` | `"https://api.coingecko.com/api/v3"` | API base URL |
| `MARKET_MAP` | `{"BTC-PERP": "bitcoin", ...}` | Symbol mapping |

### Constructor

```python
PriceFeed(timeout: float = 10.0)
```

### Methods

#### get_price()

Get price for a single market.

```python
feed = PriceFeed()
price: Optional[float] = await feed.get_price("BTC-PERP")
await feed.close()
```

**Returns:** `Optional[float]` - Price or `None` if unavailable

---

#### get_all_prices()

Get prices for all supported markets.

```python
prices: Dict[str, float] = await feed.get_all_prices()
# {'BTC-PERP': 67000.0, 'ETH-PERP': 3500.0, 'SOL-PERP': 150.0}
```

---

#### close()

Close HTTP client.

```python
await feed.close()
```

---

## Helper Functions

### fetch_live_prices()

Quick helper to fetch current prices.

```python
from ai_perp_dex import fetch_live_prices

prices: Dict[str, float] = await fetch_live_prices()
```

**Returns:** `Dict[str, float]` - Current prices for all markets

---

## Exceptions

The SDK raises standard Python exceptions:

| Exception | When |
|-----------|------|
| `ValueError` | Invalid parameters (missing agent_id, unknown market) |
| `ConnectionError` | Trade Router connection failed |
| `TimeoutError` | No quotes received within timeout |
| `Exception` | API errors (check message for details) |

### Error Handling Example

```python
import asyncio
from ai_perp_dex import TradingAgent

async def main():
    trader = TradingAgent(agent_id="safe_trader")
    
    try:
        await trader.connect()
        position = await trader.open_long("BTC-PERP", 1000)
        
    except ConnectionError as e:
        # Trade Router is down
        print(f"Cannot connect: {e}")
        
    except TimeoutError as e:
        # No MMs available or all quotes rejected
        print(f"No fill: {e}")
        
    except ValueError as e:
        # Bad parameters
        print(f"Invalid: {e}")
        
    except Exception as e:
        # API error
        print(f"Error: {e}")
        
    finally:
        await trader.disconnect()

asyncio.run(main())
```

---

## Supported Markets

| Symbol | Base Asset | CoinGecko ID |
|--------|------------|--------------|
| `BTC-PERP` | Bitcoin | `bitcoin` |
| `ETH-PERP` | Ethereum | `ethereum` |
| `SOL-PERP` | Solana | `solana` |

---

## Version

Current SDK version: `0.1.0`

```python
from ai_perp_dex import __version__
print(__version__)  # "0.1.0"
```
