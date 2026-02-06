"""High-level Trading Agent interface (Legacy Trade Router)

DEPRECATED: 此模块是 Trade Router 时代的遗留接口。
生产环境请使用: from ai_perp_dex import TradingHub
"""

import asyncio
import warnings
from typing import Optional, List, Callable, Any
from datetime import datetime, timedelta

try:
    from .types import Side, Market, TradeRequest, Quote, Position, WebSocketMessage
except ImportError:
    Side = Market = TradeRequest = Quote = Position = WebSocketMessage = None

# Legacy: TradingAgent 依赖的 Client 类不再存在
# 使用 TradingHub 代替
Client = None


class TradingAgent:
    """
    High-level interface for AI Trading Agents.
    
    Example:
        trader = TradingAgent(agent_id="my_trader", router_url="http://localhost:8080")
        await trader.connect()
        
        # Open a long position
        position = await trader.open_long("BTC-PERP", size=1000, leverage=10)
        
        # Check positions
        positions = await trader.get_positions()
        
        # Close position
        await trader.close(position.id)
    """
    
    def __init__(
        self,
        agent_id: str,
        router_url: str = "http://localhost:8080",
        private_key: Optional[str] = None,  # For future signing
    ):
        warnings.warn(
            "TradingAgent is deprecated. Use TradingHub instead: "
            "from ai_perp_dex import TradingHub",
            DeprecationWarning,
            stacklevel=2,
        )
        self.agent_id = agent_id
        self.private_key = private_key
        self._client = None  # Legacy Client removed
        self._quote_handlers: List[Callable] = []
    
    async def connect(self):
        """Connect to the Trade Router"""
        # Verify connection
        health = await self._client.health()
        if health.get("status") != "healthy":
            raise ConnectionError("Trade Router is not healthy")
        
        # Connect WebSocket for real-time updates
        await self._client.connect_ws()
        
        # Register internal handler for quotes
        @self._client.on_message
        async def handle_ws(msg: WebSocketMessage):
            if msg.type == "quote" and msg.data.get("request_agent_id") == self.agent_id:
                # New quote for our request
                for handler in self._quote_handlers:
                    try:
                        result = handler(msg.data)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        pass
    
    async def disconnect(self):
        """Disconnect from Trade Router"""
        await self._client.close()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.disconnect()
    
    # ========== Market Data ==========
    
    async def get_markets(self) -> List[Market]:
        """Get available markets"""
        return await self._client.get_markets()
    
    async def get_price(self, market: str) -> float:
        """Get current price for a market"""
        markets = await self.get_markets()
        for m in markets:
            if m.symbol == market:
                return m.price
        raise ValueError(f"Market {market} not found")
    
    # ========== Trading ==========
    
    async def open_long(
        self,
        market: str,
        size: float,
        leverage: int = 1,
        max_slippage_bps: int = 100,
        wait_for_fill: bool = True,
        timeout: float = 30.0,
    ) -> Position:
        """
        Open a long position.
        
        Args:
            market: Market symbol (e.g., "BTC-PERP")
            size: Position size in USDC
            leverage: Leverage multiplier (1-20)
            max_slippage_bps: Maximum slippage in basis points
            wait_for_fill: Wait for the position to be filled
            timeout: Timeout in seconds
        
        Returns:
            The opened Position
        """
        return await self._open_position(
            market=market,
            side=Side.LONG,
            size=size,
            leverage=leverage,
            max_slippage_bps=max_slippage_bps,
            wait_for_fill=wait_for_fill,
            timeout=timeout,
        )
    
    async def open_short(
        self,
        market: str,
        size: float,
        leverage: int = 1,
        max_slippage_bps: int = 100,
        wait_for_fill: bool = True,
        timeout: float = 30.0,
    ) -> Position:
        """Open a short position."""
        return await self._open_position(
            market=market,
            side=Side.SHORT,
            size=size,
            leverage=leverage,
            max_slippage_bps=max_slippage_bps,
            wait_for_fill=wait_for_fill,
            timeout=timeout,
        )
    
    async def _open_position(
        self,
        market: str,
        side: Side,
        size: float,
        leverage: int,
        max_slippage_bps: int,
        wait_for_fill: bool,
        timeout: float,
    ) -> Position:
        """Internal method to open a position"""
        # Create trade request
        request = await self._client.create_request(
            market=market,
            side=side.value,
            size_usdc=size,
            leverage=leverage,
            max_slippage_bps=max_slippage_bps,
        )
        
        if not wait_for_fill:
            # Return immediately, let caller handle quotes
            return None
        
        # Wait for quotes and accept best one
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        best_quote = None
        
        while datetime.utcnow() < deadline:
            quotes = await self._client.get_quotes(request.id)
            
            if quotes:
                # Sort by price (best for our side)
                if side == Side.LONG:
                    # For long, lower price is better
                    quotes.sort(key=lambda q: q.price)
                else:
                    # For short, higher price is better
                    quotes.sort(key=lambda q: -q.price)
                
                best_quote = quotes[0]
                break
            
            await asyncio.sleep(0.5)
        
        if not best_quote:
            raise TimeoutError(f"No quotes received for request {request.id}")
        
        # Accept the best quote
        position = await self._client.accept_quote(best_quote.id)
        return position
    
    # ========== Position Management ==========
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        return await self._client.get_positions()
    
    async def get_position(self, position_id: str) -> Optional[Position]:
        """Get a specific position"""
        positions = await self.get_positions()
        for p in positions:
            if p.id == position_id:
                return p
        return None
    
    async def close(self, position_id: str) -> dict:
        """Close a position

        Returns:
            Close result with PnL info and full position data
        """
        return await self._client.close_position(position_id)

    async def close_all(self) -> List[dict]:
        """Close all positions"""
        positions = await self.get_positions()
        results = []
        for p in positions:
            result = await self.close(p.id)
            results.append(result)
        return results

    # ========== PnL ==========

    async def get_total_pnl(self) -> float:
        """Get total unrealized PnL across all positions"""
        positions = await self.get_positions()
        return sum(p.unrealized_pnl for p in positions)

    # ========== Event Handlers ==========

    def on_quote(self, handler: Callable):
        """Register handler for incoming quotes"""
        self._quote_handlers.append(handler)
        return handler
    
    # ========== Simple Trading Interface ==========
    
    async def long(
        self,
        market: str,
        size: float,
        leverage: int = 1,
        max_wait_secs: float = 10,
    ) -> "Position":
        """
        Open a long position - simple one-liner interface.
        
        This will:
        1. Create a trade request
        2. Wait for MM quotes
        3. Accept the best quote
        4. Return the opened position
        
        Args:
            market: Market symbol (e.g., "BTC-PERP")
            size: Size in USDC
            leverage: Leverage (1-20)
            max_wait_secs: Max time to wait for quotes
        
        Returns:
            The opened Position
            
        Example:
            pos = await trader.long("BTC-PERP", 500, leverage=5)
        """
        return await self._execute_trade(market, "long", size, leverage, max_wait_secs)
    
    async def short(
        self,
        market: str,
        size: float,
        leverage: int = 1,
        max_wait_secs: float = 10,
    ) -> "Position":
        """Open a short position - simple one-liner interface."""
        return await self._execute_trade(market, "short", size, leverage, max_wait_secs)
    
    async def _execute_trade(
        self,
        market: str,
        side: str,
        size: float,
        leverage: int,
        max_wait_secs: float,
    ) -> "Position":
        """Execute a trade end-to-end"""
        import asyncio
        
        # 1. Create request
        request = await self._client.create_request(
            market=market,
            side=side,
            size_usdc=size,
            leverage=leverage,
        )
        
        # 2. Wait for quotes
        start = asyncio.get_event_loop().time()
        quotes = []
        
        while asyncio.get_event_loop().time() - start < max_wait_secs:
            quotes = await self._client.get_quotes(request.id)
            if quotes:
                break
            await asyncio.sleep(0.5)
        
        if not quotes:
            raise TimeoutError(f"No quotes received within {max_wait_secs}s")
        
        # 3. Accept best quote (lowest funding rate)
        best = min(quotes, key=lambda q: q.funding_rate)
        position = await self._client.accept_quote(best.id, request_id=request.id)
        
        return position
