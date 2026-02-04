"""
P2P Trading Protocol for AI Perp DEX

Agent-to-Agent direct trading without orderbooks.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Any

import aiohttp
import websockets

from .types import MarketSymbol as Market, Side


class PositionStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


@dataclass
class TradeRequest:
    """Trade request from a trader agent."""
    id: str
    agent_id: str
    market: Market
    side: Side
    size_usdc: float
    leverage: int
    max_funding_rate: float
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Quote:
    """Quote from a market maker agent."""
    id: str
    request_id: str
    agent_id: str
    funding_rate: float
    collateral_usdc: float
    valid_until: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    """Active position between two agents."""
    id: str
    request_id: str
    quote_id: str
    trader_agent: str
    mm_agent: str
    market: Market
    side: Side
    size_usdc: float
    leverage: int
    entry_price: float
    funding_rate: float
    trader_collateral: float
    mm_collateral: float
    status: PositionStatus
    created_at: datetime
    closed_at: Optional[datetime] = None


class P2PClient:
    """
    P2P Trading Client for connecting to the Trade Router.
    
    Example usage:
        async with P2PClient("ws://localhost:8080/ws", "my_agent_id") as client:
            # Subscribe to events
            client.on_trade_request = lambda req: print(f"New request: {req}")
            
            # Create a trade request
            await client.create_trade_request(
                market=Market.BTC_PERP,
                side=Side.LONG,
                size_usdc=100.0,
                leverage=10,
                max_funding_rate=0.01,
                expires_in=30
            )
    """
    
    def __init__(
        self,
        ws_url: str = "ws://localhost:8080/ws",
        rest_url: str = "http://localhost:8080",
        agent_id: str = None
    ):
        self.ws_url = ws_url
        self.rest_url = rest_url
        self.agent_id = agent_id or str(uuid.uuid4())
        self._ws = None
        self._running = False
        self._handlers: Dict[str, Callable] = {}
        
        # Event callbacks
        self.on_trade_request: Optional[Callable[[TradeRequest], None]] = None
        self.on_quote_accepted: Optional[Callable[[str, str, str], None]] = None
        self.on_position_opened: Optional[Callable[[Position], None]] = None
        self.on_position_closed: Optional[Callable[[str, float, float], None]] = None
        self.on_liquidation: Optional[Callable[[str, str], None]] = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self):
        """Connect to the Trade Router WebSocket."""
        self._ws = await websockets.connect(self.ws_url)
        self._running = True
        asyncio.create_task(self._listen())
    
    async def disconnect(self):
        """Disconnect from the Trade Router."""
        self._running = False
        if self._ws:
            await self._ws.close()
    
    async def _listen(self):
        """Listen for WebSocket messages."""
        while self._running and self._ws:
            try:
                msg = await self._ws.recv()
                await self._handle_message(json.loads(msg))
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
    
    async def _handle_message(self, msg: dict):
        """Handle incoming WebSocket message."""
        msg_type = msg.get("type")
        data = msg.get("data", {})
        
        if msg_type == "trade_request" and self.on_trade_request:
            req = TradeRequest(
                id=data["id"],
                agent_id=data["agent_id"],
                market=Market(data["market"]),
                side=Side(data["side"]),
                size_usdc=data["size_usdc"],
                leverage=data["leverage"],
                max_funding_rate=data["max_funding_rate"],
                expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
                created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            )
            await self._call_handler(self.on_trade_request, req)
        
        elif msg_type == "quote_accepted" and self.on_quote_accepted:
            await self._call_handler(
                self.on_quote_accepted,
                data["request_id"],
                data["quote_id"],
                data["position_id"]
            )
        
        elif msg_type == "position_opened" and self.on_position_opened:
            pos = self._parse_position(data)
            await self._call_handler(self.on_position_opened, pos)
        
        elif msg_type == "position_closed" and self.on_position_closed:
            await self._call_handler(
                self.on_position_closed,
                data["position_id"],
                data["pnl_trader"],
                data["pnl_mm"]
            )
        
        elif msg_type == "liquidation" and self.on_liquidation:
            await self._call_handler(
                self.on_liquidation,
                data["position_id"],
                data["liquidated_agent"]
            )
    
    async def _call_handler(self, handler: Callable, *args):
        """Call handler, supporting both sync and async handlers."""
        if asyncio.iscoroutinefunction(handler):
            await handler(*args)
        else:
            handler(*args)
    
    def _parse_position(self, data: dict) -> Position:
        """Parse position from JSON data."""
        return Position(
            id=data["id"],
            request_id=data["request_id"],
            quote_id=data["quote_id"],
            trader_agent=data["trader_agent"],
            mm_agent=data["mm_agent"],
            market=Market(data["market"]),
            side=Side(data["side"]),
            size_usdc=data["size_usdc"],
            leverage=data["leverage"],
            entry_price=data["entry_price"],
            funding_rate=data["funding_rate"],
            trader_collateral=data["trader_collateral"],
            mm_collateral=data["mm_collateral"],
            status=PositionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            closed_at=datetime.fromisoformat(data["closed_at"].replace("Z", "+00:00")) if data.get("closed_at") else None,
        )
    
    # ===== REST API Methods =====
    
    async def _post(self, path: str, data: dict) -> dict:
        """Make POST request to REST API."""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.rest_url}{path}", json=data) as resp:
                result = await resp.json()
                if not result.get("success"):
                    raise Exception(result.get("error", "Unknown error"))
                return result.get("data")
    
    async def _get(self, path: str) -> dict:
        """Make GET request to REST API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.rest_url}{path}") as resp:
                result = await resp.json()
                if not result.get("success"):
                    raise Exception(result.get("error", "Unknown error"))
                return result.get("data")
    
    async def create_trade_request(
        self,
        market: Market,
        side: Side,
        size_usdc: float,
        leverage: int,
        max_funding_rate: float = 0.01,
        expires_in: int = 30
    ) -> TradeRequest:
        """
        Create a new trade request.
        
        Args:
            market: Trading market (BTC-PERP, ETH-PERP, SOL-PERP)
            side: Trade direction (long/short)
            size_usdc: Position size in USDC
            leverage: Leverage multiplier (1-100)
            max_funding_rate: Maximum acceptable funding rate
            expires_in: Seconds until request expires
        
        Returns:
            TradeRequest object
        """
        data = await self._post("/trade/request", {
            "agent_id": self.agent_id,
            "market": market.value,
            "side": side.value,
            "size_usdc": size_usdc,
            "leverage": leverage,
            "max_funding_rate": max_funding_rate,
            "expires_in": expires_in
        })
        
        return TradeRequest(
            id=data["id"],
            agent_id=data["agent_id"],
            market=Market(data["market"]),
            side=Side(data["side"]),
            size_usdc=data["size_usdc"],
            leverage=data["leverage"],
            max_funding_rate=data["max_funding_rate"],
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )
    
    async def submit_quote(
        self,
        request_id: str,
        funding_rate: float,
        collateral_usdc: float,
        valid_for: int = 10
    ) -> Quote:
        """
        Submit a quote for a trade request (for market makers).
        
        Args:
            request_id: ID of the trade request
            funding_rate: Funding rate to charge
            collateral_usdc: Collateral to lock
            valid_for: Seconds quote is valid
        
        Returns:
            Quote object
        """
        data = await self._post("/trade/quote", {
            "request_id": request_id,
            "agent_id": self.agent_id,
            "funding_rate": funding_rate,
            "collateral_usdc": collateral_usdc,
            "valid_for": valid_for
        })
        
        return Quote(
            id=data["id"],
            request_id=data["request_id"],
            agent_id=data["agent_id"],
            funding_rate=data["funding_rate"],
            collateral_usdc=data["collateral_usdc"],
            valid_until=datetime.fromisoformat(data["valid_until"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )
    
    async def accept_quote(
        self,
        request_id: str,
        quote_id: str,
        signature: str = ""
    ) -> Position:
        """
        Accept a quote and open position.
        
        Args:
            request_id: ID of the trade request
            quote_id: ID of the quote to accept
            signature: Agent signature (for chain verification)
        
        Returns:
            Position object
        """
        data = await self._post("/trade/accept", {
            "request_id": request_id,
            "quote_id": quote_id,
            "signature": signature
        })
        
        return self._parse_position(data)
    
    async def close_position(
        self,
        position_id: str,
        size_percent: int = 100
    ) -> dict:
        """
        Close a position.
        
        Args:
            position_id: ID of the position
            size_percent: Percentage to close (1-100)
        
        Returns:
            Dict with PnL info
        """
        return await self._post("/trade/close", {
            "position_id": position_id,
            "agent_id": self.agent_id,
            "size_percent": size_percent
        })
    
    async def get_positions(self) -> List[Position]:
        """Get all positions for this agent."""
        data = await self._get(f"/positions/{self.agent_id}")
        return [self._parse_position(p) for p in data]
    
    async def get_active_requests(self) -> List[TradeRequest]:
        """Get all active trade requests."""
        data = await self._get("/requests")
        return [
            TradeRequest(
                id=r["id"],
                agent_id=r["agent_id"],
                market=Market(r["market"]),
                side=Side(r["side"]),
                size_usdc=r["size_usdc"],
                leverage=r["leverage"],
                max_funding_rate=r["max_funding_rate"],
                expires_at=datetime.fromisoformat(r["expires_at"].replace("Z", "+00:00")),
                created_at=datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")),
            )
            for r in data
        ]
    
    async def get_quotes(self, request_id: str) -> List[Quote]:
        """Get quotes for a trade request."""
        data = await self._get(f"/quotes/{request_id}")
        return [
            Quote(
                id=q["id"],
                request_id=q["request_id"],
                agent_id=q["agent_id"],
                funding_rate=q["funding_rate"],
                collateral_usdc=q["collateral_usdc"],
                valid_until=datetime.fromisoformat(q["valid_until"].replace("Z", "+00:00")),
                created_at=datetime.fromisoformat(q["created_at"].replace("Z", "+00:00")),
            )
            for q in data
        ]
    
    async def get_markets(self) -> List[dict]:
        """Get market information."""
        return await self._get("/markets")


class TraderAgent:
    """
    Base class for Trader Agents.
    
    Extend this class to create your own trading agent.
    """
    
    def __init__(self, client: P2PClient):
        self.client = client
        self.positions: Dict[str, Position] = {}
    
    async def open_position(
        self,
        market: Market,
        side: Side,
        size_usdc: float,
        leverage: int,
        max_funding_rate: float = 0.01,
        timeout: int = 30
    ) -> Optional[Position]:
        """
        Open a new position by requesting quotes and accepting the best one.
        
        Args:
            market: Trading market
            side: Trade direction
            size_usdc: Position size
            leverage: Leverage multiplier
            max_funding_rate: Max acceptable funding rate
            timeout: Seconds to wait for quotes
        
        Returns:
            Position if successful, None otherwise
        """
        # Create trade request
        request = await self.client.create_trade_request(
            market=market,
            side=side,
            size_usdc=size_usdc,
            leverage=leverage,
            max_funding_rate=max_funding_rate,
            expires_in=timeout
        )
        
        # Wait for quotes
        await asyncio.sleep(min(5, timeout // 2))
        
        # Get quotes
        quotes = await self.client.get_quotes(request.id)
        if not quotes:
            print("No quotes received")
            return None
        
        # Select best quote (lowest funding rate)
        best_quote = min(quotes, key=lambda q: q.funding_rate)
        
        # Accept quote
        position = await self.client.accept_quote(request.id, best_quote.id)
        self.positions[position.id] = position
        
        return position
    
    async def close_all_positions(self):
        """Close all open positions."""
        for pos_id in list(self.positions.keys()):
            try:
                await self.client.close_position(pos_id)
                del self.positions[pos_id]
            except Exception as e:
                print(f"Failed to close position {pos_id}: {e}")


class MarketMakerAgent:
    """
    Base class for Market Maker Agents.
    
    Extend this class to create your own market making agent.
    """
    
    def __init__(
        self,
        client: P2PClient,
        spread_bps: int = 50,  # 0.5% spread
        max_position_size: float = 10000.0,
        min_collateral_ratio: float = 0.5
    ):
        self.client = client
        self.spread_bps = spread_bps
        self.max_position_size = max_position_size
        self.min_collateral_ratio = min_collateral_ratio
        self.positions: Dict[str, Position] = {}
        self._running = False
    
    def calculate_funding_rate(self, request: TradeRequest) -> float:
        """
        Calculate funding rate for a trade request.
        Override this method for custom pricing logic.
        """
        base_rate = self.spread_bps / 10000  # Convert bps to rate
        
        # Adjust for leverage risk
        leverage_multiplier = 1 + (request.leverage - 1) * 0.1
        
        # Adjust for size risk
        size_multiplier = 1 + (request.size_usdc / self.max_position_size) * 0.2
        
        return base_rate * leverage_multiplier * size_multiplier
    
    def should_quote(self, request: TradeRequest) -> bool:
        """
        Decide whether to quote for a trade request.
        Override this method for custom filtering logic.
        """
        # Don't quote for our own requests
        if request.agent_id == self.client.agent_id:
            return False
        
        # Check position limit
        current_exposure = sum(p.size_usdc for p in self.positions.values())
        if current_exposure + request.size_usdc > self.max_position_size:
            return False
        
        return True
    
    async def handle_trade_request(self, request: TradeRequest):
        """Handle incoming trade request."""
        if not self.should_quote(request):
            return
        
        funding_rate = self.calculate_funding_rate(request)
        
        # Only quote if within their max
        if funding_rate > request.max_funding_rate:
            return
        
        # Calculate collateral (match trader's)
        collateral = request.size_usdc / request.leverage * self.min_collateral_ratio
        
        try:
            quote = await self.client.submit_quote(
                request_id=request.id,
                funding_rate=funding_rate,
                collateral_usdc=collateral,
                valid_for=10
            )
            print(f"Submitted quote {quote.id} for request {request.id}: rate={funding_rate:.4f}")
        except Exception as e:
            print(f"Failed to submit quote: {e}")
    
    async def handle_position_opened(self, position: Position):
        """Handle new position."""
        if position.mm_agent == self.client.agent_id:
            self.positions[position.id] = position
            print(f"Position opened: {position.id}, size={position.size_usdc}")
    
    async def handle_position_closed(self, position_id: str, pnl_trader: float, pnl_mm: float):
        """Handle position close."""
        if position_id in self.positions:
            del self.positions[position_id]
            print(f"Position closed: {position_id}, MM PnL={pnl_mm}")
    
    async def run(self):
        """Run the market maker agent."""
        self._running = True
        
        # Set up callbacks
        self.client.on_trade_request = self.handle_trade_request
        self.client.on_position_opened = self.handle_position_opened
        self.client.on_position_closed = self.handle_position_closed
        
        print(f"Market Maker Agent started: {self.client.agent_id}")
        
        while self._running:
            await asyncio.sleep(1)
    
    def stop(self):
        """Stop the market maker agent."""
        self._running = False
