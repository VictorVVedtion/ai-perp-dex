"""
PerpDexClient - API Client for AI Perp DEX

Connects to the AI Perp DEX REST API server.
"""

import json
import time
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import asdict
from pathlib import Path

import httpx

from .types import (
    Side, OrderType, Position, Order, TradeResult,
    AccountInfo, Market, OrderStatus
)


class PerpDexClient:
    """
    API Client for AI Perp DEX
    
    Handles all communication with the REST API server.
    """
    
    def __init__(
        self,
        keypair_path: Optional[str] = None,
        private_key: Optional[str] = None,
        api_url: str = "http://localhost:8080",
    ):
        """
        Initialize API client.
        
        Args:
            keypair_path: Path to Solana keypair JSON file
            private_key: Or provide private key directly (base58)
            api_url: AI Perp DEX API server URL
        """
        self.api_url = api_url.rstrip('/')
        self.http = httpx.Client(timeout=30)
        
        # Load keypair
        if keypair_path:
            path = Path(keypair_path).expanduser()
            if path.exists():
                with open(path) as f:
                    secret = json.load(f)
                # First 32 bytes are private key, last 32 are public key
                self._private_key = bytes(secret[:32])
                self._public_key = bytes(secret[32:64])
            else:
                # Generate new keypair for testing
                import secrets
                self._private_key = secrets.token_bytes(32)
                self._public_key = secrets.token_bytes(32)
        elif private_key:
            import base58
            self._private_key = base58.b58decode(private_key)[:32]
            self._public_key = base58.b58decode(private_key)[32:64]
        else:
            # Generate random keypair for testing
            import secrets
            self._private_key = secrets.token_bytes(32)
            self._public_key = secrets.token_bytes(32)
        
        import base58
        self.pubkey = base58.b58encode(self._public_key).decode()
        self._registered = False
    
    def _sign_message(self, message: bytes) -> str:
        """Sign a message with the agent's private key."""
        # Simplified signature for now
        # In production, use proper Ed25519 signing
        import hashlib
        import base58
        sig = hashlib.sha256(self._private_key + message).digest() * 2
        return base58.b58encode(sig).decode()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{self.api_url}{endpoint}"
        
        try:
            if method == "GET":
                response = self.http.get(url, params=params)
            elif method == "POST":
                response = self.http.post(url, json=data)
            elif method == "PUT":
                response = self.http.put(url, json=data)
            elif method == "DELETE":
                response = self.http.delete(url, params=params)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    # ==================== Agent Management ====================
    
    def register_agent(self, name: str) -> bool:
        """Register as a trading agent."""
        result = self._request("POST", "/v1/agent/register", {
            "pubkey": self.pubkey,
            "name": name,
        })
        self._registered = result.get("success", False)
        return self._registered
    
    def get_agent_info(self) -> Dict:
        """Get agent information."""
        return self._request("GET", "/v1/agent/info", params={"pubkey": self.pubkey})
    
    def set_risk_params(
        self,
        max_leverage: int = 10,
        max_position_size_usd: float = 10000,
        max_daily_loss_usd: float = 1000,
        max_positions: int = 10,
    ) -> bool:
        """Set risk parameters."""
        result = self._request("PUT", "/v1/agent/risk-params", {
            "max_leverage": max_leverage,
            "max_position_size_usd": max_position_size_usd,
            "max_daily_loss_usd": max_daily_loss_usd,
            "max_positions": max_positions,
        })
        return result.get("success", False)
    
    # ==================== Trading ====================
    
    def open_position(
        self,
        market: str,
        side: Side,
        size_usd: float,
        leverage: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> TradeResult:
        """Open a position."""
        # Create order data
        order_data = {
            "market": market,
            "side": side.value,
            "order_type": order_type.value,
            "size_usd": size_usd,
            "leverage": leverage,
            "price": price,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
        }
        
        # Sign the order
        message = json.dumps(order_data, sort_keys=True).encode()
        order_data["signature"] = self._sign_message(message)
        
        result = self._request("POST", "/v1/order", order_data)
        
        return TradeResult(
            success=result.get("success", False),
            order_id=result.get("order_id"),
            tx_signature=result.get("tx_signature"),
            message=result.get("message", "Unknown error"),
            position=None,
        )
    
    def close_position(self, market: str, size_percent: float = 100) -> TradeResult:
        """Close a position."""
        result = self._request("POST", "/v1/position/close", {
            "market": market,
            "size_percent": size_percent,
        })
        
        return TradeResult(
            success=result.get("success", False),
            order_id=result.get("order_id"),
            tx_signature=result.get("tx_signature"),
            message=result.get("message", "Unknown error"),
            position=None,
        )
    
    def close_all_positions(self) -> TradeResult:
        """Close all positions."""
        positions = self.get_positions()
        for pos in positions:
            self.close_position(pos.market, 100)
        
        return TradeResult(
            success=True,
            order_id=None,
            tx_signature=None,
            message=f"Closed {len(positions)} positions",
            position=None,
        )
    
    def modify_position(
        self,
        market: str,
        new_leverage: Optional[int] = None,
        add_margin: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> TradeResult:
        """Modify a position."""
        result = self._request("PUT", "/v1/position/modify", {
            "market": market,
            "new_leverage": new_leverage,
            "add_margin": add_margin,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
        })
        
        return TradeResult(
            success=result.get("success", False),
            order_id=None,
            tx_signature=None,
            message=result.get("message", "Unknown error"),
            position=None,
        )
    
    # ==================== Queries ====================
    
    def get_account(self) -> AccountInfo:
        """Get account information."""
        result = self._request("GET", "/v1/account", params={"pubkey": self.pubkey})
        
        return AccountInfo(
            agent_id=result.get("agent_id", ""),
            pubkey=self.pubkey,
            collateral=result.get("collateral", 0),
            available_margin=result.get("available_margin", 0),
            total_position_value=result.get("total_position_value", 0),
            total_unrealized_pnl=result.get("unrealized_pnl", 0),
            total_realized_pnl=result.get("realized_pnl", 0),
            positions=[],
            open_orders=[],
        )
    
    def get_positions(self) -> List[Position]:
        """Get all positions."""
        result = self._request("GET", "/v1/positions", params={"pubkey": self.pubkey})
        
        if isinstance(result, list):
            # Parse positions
            positions = []
            for p in result:
                positions.append(Position(
                    market=p["market"],
                    side=Side(p["side"]),
                    size=p.get("size", 0),
                    size_usd=p.get("size_usd", 0),
                    entry_price=p.get("entry_price", 0),
                    mark_price=p.get("mark_price", 0),
                    liquidation_price=p.get("liquidation_price", 0),
                    margin=p.get("margin", 0),
                    leverage=p.get("leverage", 1),
                    unrealized_pnl=p.get("unrealized_pnl", 0),
                    unrealized_pnl_percent=p.get("unrealized_pnl_pct", 0),
                    opened_at=None,
                ))
            return positions
        
        return []
    
    def get_position(self, market: str) -> Optional[Position]:
        """Get a specific position."""
        result = self._request("GET", f"/v1/position/{market}")
        
        if result.get("success") is False or result.get("status_code") == 404:
            return None
        
        return Position(
            market=result.get("market", market),
            side=Side(result.get("side", "long")),
            size=result.get("size", 0),
            size_usd=result.get("size_usd", 0),
            entry_price=result.get("entry_price", 0),
            mark_price=result.get("mark_price", 0),
            liquidation_price=result.get("liquidation_price", 0),
            margin=result.get("margin", 0),
            leverage=result.get("leverage", 1),
            unrealized_pnl=result.get("unrealized_pnl", 0),
            unrealized_pnl_percent=result.get("unrealized_pnl_pct", 0),
            opened_at=None,
        )
    
    def get_orders(self) -> List[Order]:
        """Get open orders."""
        result = self._request("GET", "/v1/orders", params={"pubkey": self.pubkey})
        
        if isinstance(result, list):
            return result  # TODO: Parse into Order objects
        
        return []
    
    def get_markets(self) -> List[Market]:
        """Get all markets."""
        result = self._request("GET", "/v1/markets")
        
        if isinstance(result, list):
            markets = []
            for m in result:
                markets.append(Market(
                    symbol=m["symbol"],
                    index=m["index"],
                    base_asset=m["base_asset"],
                    price=m["price"],
                    index_price=m.get("index_price", m["price"]),
                    funding_rate=m.get("funding_rate", 0),
                    open_interest=m.get("open_interest", 0),
                    volume_24h=m.get("volume_24h", 0),
                ))
            return markets
        
        return []
    
    def get_price(self, market: str) -> float:
        """Get market price."""
        result = self._request("GET", f"/v1/price/{market}")
        return result.get("price", 0)
    
    # ==================== Account Management ====================
    
    def deposit(self, amount: float) -> TradeResult:
        """Deposit collateral."""
        result = self._request("POST", "/v1/account/deposit", {
            "amount": amount,
            "tx_signature": "mock_deposit_tx",
        })
        
        return TradeResult(
            success=result.get("success", False),
            order_id=None,
            tx_signature=None,
            message=result.get("message", "Unknown error"),
            position=None,
        )
    
    def withdraw(self, amount: float) -> TradeResult:
        """Withdraw collateral."""
        result = self._request("POST", "/v1/account/withdraw", {
            "amount": amount,
            "destination": self.pubkey,
        })
        
        return TradeResult(
            success=result.get("success", False),
            order_id=None,
            tx_signature=result.get("tx_signature"),
            message=result.get("message", "Unknown error"),
            position=None,
        )
