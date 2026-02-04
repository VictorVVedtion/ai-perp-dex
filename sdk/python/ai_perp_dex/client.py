"""Base client for communicating with the Trade Router"""

import asyncio
import json
from typing import Optional, Callable, List, Any
import httpx
import websockets
from websockets.client import WebSocketClientProtocol

from .types import Market, TradeRequest, Quote, Position, WebSocketMessage


class Client:
    """Low-level client for Trade Router API"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        ws_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.ws_url = ws_url or base_url.replace("http", "ws") + "/ws"
        self.agent_id = agent_id
        self.timeout = timeout
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self._ws: Optional[WebSocketClientProtocol] = None
        self._ws_handlers: List[Callable[[WebSocketMessage], Any]] = []
        self._ws_task: Optional[asyncio.Task] = None
    
    async def close(self):
        """Close all connections"""
        await self._http.aclose()
        if self._ws:
            await self._ws.close()
        if self._ws_task:
            self._ws_task.cancel()
    
    # ========== HTTP API ==========
    
    async def health(self) -> dict:
        """Check if Trade Router is healthy"""
        r = await self._http.get("/health")
        return r.json()
    
    async def get_markets(self) -> List[Market]:
        """Get available markets"""
        r = await self._http.get("/markets")
        data = r.json()
        markets_data = data.get("data", []) if isinstance(data, dict) else data
        return [Market(
            symbol=m.get("market", m.get("symbol")),
            base_asset=m.get("market", "").split("-")[0],
            price=m.get("current_price", 0),
            volume_24h=m.get("volume_24h", 0),
            open_interest=m.get("open_interest", 0),
            funding_rate=m.get("funding_rate_24h", 0),
        ) for m in markets_data]
    
    async def get_requests(self, status: Optional[str] = None) -> List[TradeRequest]:
        """Get open trade requests"""
        params = {"status": status} if status else {}
        r = await self._http.get("/requests", params=params)
        data = r.json()
        requests_data = data.get("data", []) if isinstance(data, dict) else data
        return [TradeRequest(**req) for req in requests_data]
    
    async def get_quotes(self, request_id: str) -> List[Quote]:
        """Get quotes for a specific request"""
        r = await self._http.get(f"/quotes/{request_id}")
        data = r.json()
        quotes_data = data.get("data", []) if isinstance(data, dict) else data
        return [Quote(**q) for q in quotes_data]
    
    async def get_positions(self, agent_id: Optional[str] = None) -> List[Position]:
        """Get positions for an agent"""
        aid = agent_id or self.agent_id
        if not aid:
            raise ValueError("agent_id required")
        r = await self._http.get(f"/positions/{aid}")
        data = r.json()
        positions_data = data.get("data", []) if isinstance(data, dict) else data
        return [Position(
            id=p.get("id"),
            trader_id=p.get("trader_agent", ""),
            mm_id=p.get("mm_agent", ""),
            market=p.get("market"),
            side=p.get("side"),
            size_usdc=p.get("size_usdc"),
            entry_price=p.get("entry_price"),
            leverage=p.get("leverage", 1),
            created_at=p.get("created_at"),
        ) for p in positions_data]
    
    async def create_request(
        self,
        market: str,
        side: str,
        size_usdc: float,
        leverage: int = 1,
        max_funding_rate: float = 0.01,
        expires_in: int = 300,
    ) -> TradeRequest:
        """Create a new trade request"""
        if not self.agent_id:
            raise ValueError("agent_id required")
        
        payload = {
            "agent_id": self.agent_id,
            "market": market,
            "side": side.lower(),
            "size_usdc": size_usdc,
            "leverage": leverage,
            "max_funding_rate": max_funding_rate,
            "expires_in": expires_in,
        }
        r = await self._http.post("/trade/request", json=payload)
        if r.status_code != 200:
            raise Exception(f"Request failed: {r.text}")
        data = r.json()
        return TradeRequest(**data.get("data", data))
    
    async def create_quote(
        self,
        request_id: str,
        funding_rate: float = 0.01,
        collateral_usdc: float = 100,
        valid_for: int = 300,
    ) -> Quote:
        """Submit a quote for a trade request"""
        if not self.agent_id:
            raise ValueError("agent_id required")
        
        payload = {
            "request_id": request_id,
            "agent_id": self.agent_id,
            "funding_rate": funding_rate,
            "collateral_usdc": collateral_usdc,
            "valid_for": valid_for,
        }
        r = await self._http.post("/trade/quote", json=payload)
        if r.status_code != 200:
            raise Exception(f"Quote failed: {r.text}")
        data = r.json()
        return Quote(**data.get("data", data))
    
    async def accept_quote(self, quote_id: str, request_id: str = None) -> Position:
        """Accept a quote and open a position"""
        payload = {
            "request_id": request_id or "",  # Will be filled from quote if needed
            "quote_id": quote_id,
            "signature": "sdk_auto_sign",  # Placeholder
        }
        r = await self._http.post("/trade/accept", json=payload)
        if r.status_code != 200:
            raise Exception(f"Accept failed: {r.text}")
        data = r.json()
        pos_data = data.get("data", data)
        return Position(
            id=pos_data.get("id"),
            trader_id=pos_data.get("trader_agent"),
            mm_id=pos_data.get("mm_agent"),
            market=pos_data.get("market"),
            side=pos_data.get("side"),
            size_usdc=pos_data.get("size_usdc"),
            entry_price=pos_data.get("entry_price"),
            leverage=pos_data.get("leverage", 1),
            created_at=pos_data.get("created_at"),
        )
    
    async def close_position(self, position_id: str) -> dict:
        """Close a position"""
        payload = {"position_id": position_id}
        r = await self._http.post("/trade/close", json=payload)
        return r.json()
    
    # ========== WebSocket ==========
    
    def on_message(self, handler: Callable[[WebSocketMessage], Any]):
        """Register a WebSocket message handler"""
        self._ws_handlers.append(handler)
        return handler
    
    async def connect_ws(self):
        """Connect to WebSocket for real-time updates"""
        self._ws = await websockets.connect(self.ws_url)
        self._ws_task = asyncio.create_task(self._ws_loop())
    
    async def _ws_loop(self):
        """Internal WebSocket message loop"""
        if not self._ws:
            return
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    msg = WebSocketMessage(
                        type=data.get("type", "unknown"),
                        data=data.get("data", data),
                    )
                    for handler in self._ws_handlers:
                        try:
                            result = handler(msg)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            print(f"Handler error: {e}")
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            pass
