"""High-level Market Maker interface"""

import asyncio
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime

from .client import Client
from .types import Side, Market, TradeRequest, Quote, Position, WebSocketMessage


class MarketMaker:
    """
    High-level interface for AI Market Maker Agents.
    
    Example:
        mm = MarketMaker(agent_id="my_mm", router_url="http://localhost:8080")
        
        @mm.on_request
        async def handle_request(request: TradeRequest) -> Optional[Quote]:
            # Decide whether to quote
            if request.size_usdc > 10000:
                return None  # Too large
            
            price = await get_fair_price(request.market)
            spread = 10  # 0.1% spread
            
            return await mm.quote(request, price, spread_bps=spread)
        
        await mm.run()
    """
    
    def __init__(
        self,
        agent_id: str,
        router_url: str = "http://localhost:8080",
        private_key: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.private_key = private_key
        self._client = Client(base_url=router_url, agent_id=agent_id)
        self._request_handlers: List[Callable[[TradeRequest], Any]] = []
        self._running = False
        self._markets_cache: Dict[str, Market] = {}
        
        # Risk parameters
        self.max_position_size: float = 100000  # Max position per market
        self.max_total_exposure: float = 500000  # Max total exposure
        self.default_spread_bps: int = 10  # Default spread
        self.min_spread_bps: int = 5  # Minimum spread
    
    async def connect(self):
        """Connect to Trade Router"""
        health = await self._client.health()
        if health.get("status") != "healthy":
            raise ConnectionError("Trade Router is not healthy")
        
        # Cache markets
        markets = await self._client.get_markets()
        self._markets_cache = {m.symbol: m for m in markets}
        
        # Connect WebSocket
        await self._client.connect_ws()
        
        # Register handler for new requests
        @self._client.on_message
        async def handle_ws(msg: WebSocketMessage):
            if msg.type == "request":
                request = TradeRequest(**msg.data)
                await self._handle_request(request)
    
    async def disconnect(self):
        """Disconnect from Trade Router"""
        self._running = False
        await self._client.close()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.disconnect()
    
    # ========== Request Handling ==========
    
    def on_request(self, handler: Callable[[TradeRequest], Any]):
        """
        Decorator to register a request handler.
        
        The handler receives a TradeRequest and can return:
        - None: Don't quote this request
        - A Quote: The quote to submit
        """
        self._request_handlers.append(handler)
        return handler
    
    async def _handle_request(self, request: TradeRequest):
        """Internal request handler"""
        for handler in self._request_handlers:
            try:
                result = handler(request)
                if asyncio.iscoroutine(result):
                    result = await result
                # Result is handled by the handler itself
            except Exception as e:
                print(f"Request handler error: {e}")
    
    # ========== Quoting ==========
    
    async def quote(
        self,
        request: TradeRequest,
        funding_rate: float = 0.01,
        collateral_usdc: Optional[float] = None,
    ) -> Quote:
        """
        Submit a quote for a trade request.
        
        Args:
            request: The trade request to quote
            funding_rate: The funding rate to charge
            collateral_usdc: Collateral amount (defaults to request size / 10)
        
        Returns:
            The submitted Quote
        """
        collateral = collateral_usdc or (request.size_usdc / 10)
        
        return await self._client.create_quote(
            request_id=request.id,
            funding_rate=funding_rate,
            collateral_usdc=collateral,
        )
    
    async def auto_quote(
        self,
        request: TradeRequest,
        funding_rate: float = 0.01,
    ) -> Optional[Quote]:
        """
        Automatically quote a request.
        
        Returns None if the request fails risk checks.
        """
        # Risk checks
        if not self._check_risk(request):
            return None
        
        # Calculate collateral (10% of size)
        collateral = request.size_usdc / 10
        
        return await self.quote(request, funding_rate=funding_rate, collateral_usdc=collateral)
    
    def _check_risk(self, request: TradeRequest) -> bool:
        """Check if request passes risk parameters"""
        # Check max position size
        if request.size_usdc > self.max_position_size:
            return False
        
        # TODO: Check total exposure
        # TODO: Check per-market limits
        
        return True
    
    # ========== Position Management ==========
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        return await self._client.get_positions()
    
    async def get_exposure(self) -> Dict[str, float]:
        """Get current exposure per market"""
        positions = await self.get_positions()
        exposure: Dict[str, float] = {}
        
        for p in positions:
            current = exposure.get(p.market, 0)
            if p.side == Side.LONG:
                exposure[p.market] = current + p.size_usdc
            else:
                exposure[p.market] = current - p.size_usdc
        
        return exposure
    
    async def get_total_exposure(self) -> float:
        """Get total absolute exposure"""
        exposure = await self.get_exposure()
        return sum(abs(v) for v in exposure.values())
    
    # ========== Running ==========
    
    async def run(self, poll_interval: float = 1.0):
        """
        Run the market maker continuously.
        
        This will:
        1. Poll for new requests
        2. Call registered handlers
        3. Update market prices
        """
        self._running = True
        
        while self._running:
            try:
                # Update markets cache
                markets = await self._client.get_markets()
                self._markets_cache = {m.symbol: m for m in markets}
                
                # Poll for new requests
                requests = await self._client.get_requests(status="pending")
                
                for request in requests:
                    await self._handle_request(request)
                
            except Exception as e:
                print(f"MM loop error: {e}")
            
            await asyncio.sleep(poll_interval)
    
    def stop(self):
        """Stop the market maker"""
        self._running = False


# ========== Helper: Simple Auto-Quoting MM ==========

class SimpleMarketMaker(MarketMaker):
    """
    A simple market maker that auto-quotes all requests within risk limits.
    
    Example:
        mm = SimpleMarketMaker(agent_id="simple_mm", spread_bps=15)
        await mm.run()
    """
    
    def __init__(
        self,
        agent_id: str,
        router_url: str = "http://localhost:8080",
        spread_bps: int = 10,
        max_position: float = 50000,
    ):
        super().__init__(agent_id, router_url)
        self.default_spread_bps = spread_bps
        self.max_position_size = max_position
        
        # Register auto-quote handler
        @self.on_request
        async def auto_quote_handler(request: TradeRequest):
            return await self.auto_quote(request)
