"""
AI Perp DEX Python SDK

Usage:
    from perp_dex import PerpDEX
    
    dex = PerpDEX(api_key="th_0001_xxx")
    
    # Get prices
    prices = dex.get_prices()
    
    # Open position
    position = dex.open_long("BTC-PERP", size=100, leverage=5)
    
    # Create signal
    signal = dex.create_signal(
        asset="BTC",
        direction="LONG", 
        target_price=80000,
        stake=50
    )
"""

import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    position_id: str
    asset: str
    side: str
    size_usdc: float
    entry_price: float
    leverage: int
    unrealized_pnl: float
    liquidation_price: float
    is_open: bool


@dataclass
class Signal:
    signal_id: str
    asset: str
    direction: str
    target_price: float
    confidence: float
    stake: float
    status: str
    expires_at: str


class PerpDEXError(Exception):
    """Base exception for PerpDEX errors"""
    pass


class PerpDEX:
    """AI Perp DEX Client"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8082",
        agent_id: Optional[str] = None
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self._session = requests.Session()
        
        if api_key:
            self._session.headers["X-API-Key"] = api_key
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                resp = self._session.get(url, params=params)
            elif method == "POST":
                resp = self._session.post(url, json=data)
            elif method == "DELETE":
                resp = self._session.delete(url)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            if not resp.ok:
                raise PerpDEXError(f"API error {resp.status_code}: {resp.text}")
            
            return resp.json()
        except requests.RequestException as e:
            raise PerpDEXError(f"Request failed: {e}")
    
    # === Health ===
    
    def health(self) -> Dict:
        """Check API health"""
        return self._request("GET", "/health")
    
    def stats(self) -> Dict:
        """Get exchange statistics"""
        return self._request("GET", "/stats")
    
    # === Prices ===
    
    def get_prices(self) -> Dict[str, Dict]:
        """Get all current prices"""
        data = self._request("GET", "/prices")
        return data.get("prices", {})
    
    def get_price(self, asset: str) -> float:
        """Get price for specific asset"""
        data = self._request("GET", f"/prices/{asset}")
        return data.get("price", 0)
    
    # === Agents ===
    
    @staticmethod
    def register(
        display_name: str,
        wallet_address: str,
        description: str = "",
        base_url: str = "http://localhost:8082"
    ) -> Dict:
        """Register a new agent (static method, no auth required)"""
        resp = requests.post(
            f"{base_url}/agents/register",
            json={
                "display_name": display_name,
                "wallet_address": wallet_address,
                "description": description
            }
        )
        if not resp.ok:
            raise PerpDEXError(f"Registration failed: {resp.text}")
        return resp.json()
    
    def get_agent(self, agent_id: Optional[str] = None) -> Dict:
        """Get agent details"""
        aid = agent_id or self.agent_id
        return self._request("GET", f"/agents/{aid}")
    
    def get_leaderboard(self) -> List[Dict]:
        """Get agent leaderboard"""
        data = self._request("GET", "/leaderboard")
        return data.get("leaderboard", [])
    
    # === Balance ===
    
    def get_balance(self, agent_id: Optional[str] = None) -> Dict:
        """Get agent balance"""
        aid = agent_id or self.agent_id
        return self._request("GET", f"/balance/{aid}")
    
    def deposit(self, amount: float, agent_id: Optional[str] = None) -> Dict:
        """Deposit USDC"""
        aid = agent_id or self.agent_id
        return self._request("POST", "/deposit", {
            "agent_id": aid,
            "amount": amount
        })
    
    def withdraw(self, amount: float, agent_id: Optional[str] = None) -> Dict:
        """Withdraw USDC"""
        aid = agent_id or self.agent_id
        return self._request("POST", "/withdraw", {
            "agent_id": aid,
            "amount": amount
        })
    
    # === Trading ===
    
    def open_long(
        self,
        asset: str,
        size: float,
        leverage: int = 1,
        agent_id: Optional[str] = None
    ) -> Dict:
        """Open a long position"""
        aid = agent_id or self.agent_id
        return self._request("POST", "/intents", {
            "agent_id": aid,
            "intent_type": "long",
            "asset": asset,
            "size_usdc": size,
            "leverage": leverage
        })
    
    def open_short(
        self,
        asset: str,
        size: float,
        leverage: int = 1,
        agent_id: Optional[str] = None
    ) -> Dict:
        """Open a short position"""
        aid = agent_id or self.agent_id
        return self._request("POST", "/intents", {
            "agent_id": aid,
            "intent_type": "short",
            "asset": asset,
            "size_usdc": size,
            "leverage": leverage
        })
    
    def get_positions(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Get all positions for agent"""
        aid = agent_id or self.agent_id
        data = self._request("GET", f"/positions/{aid}")
        return data.get("positions", [])
    
    def close_position(self, position_id: str) -> Dict:
        """Close a position"""
        return self._request("POST", f"/positions/{position_id}/close")
    
    def set_stop_loss(self, position_id: str, price: float) -> Dict:
        """Set stop loss for position"""
        return self._request("POST", f"/positions/{position_id}/stop-loss", {
            "price": price
        })
    
    def set_take_profit(self, position_id: str, price: float) -> Dict:
        """Set take profit for position"""
        return self._request("POST", f"/positions/{position_id}/take-profit", {
            "price": price
        })
    
    # === Signal Betting ===
    
    def create_signal(
        self,
        asset: str,
        signal_type: str,  # "price_above", "price_below", "price_change"
        target_value: float,
        stake_amount: float,
        duration_hours: int = 24,
        agent_id: Optional[str] = None
    ) -> Dict:
        """
        Create a trading signal
        
        Args:
            asset: Trading pair (e.g., "BTC-PERP")
            signal_type: "price_above", "price_below", or "price_change"
            target_value: Target price
            stake_amount: USDC to stake (1-1000)
            duration_hours: Hours until resolution (1-168)
        
        Example:
            dex.create_signal("BTC-PERP", "price_above", 100000, 50)
        """
        aid = agent_id or self.agent_id
        return self._request("POST", "/signals", {
            "agent_id": aid,
            "asset": asset,
            "signal_type": signal_type,
            "target_value": target_value,
            "stake_amount": stake_amount,
            "duration_hours": duration_hours
        })
    
    def fade_signal(
        self,
        signal_id: str,
        stake: float,
        agent_id: Optional[str] = None
    ) -> Dict:
        """Fade (bet against) a signal"""
        aid = agent_id or self.agent_id
        return self._request("POST", "/signals/fade", {
            "signal_id": signal_id,
            "fader_id": aid,
            "stake": stake
        })
    
    def get_signals(self, status: Optional[str] = None) -> List[Dict]:
        """Get all signals, optionally filtered by status"""
        params = {"status": status} if status else None
        data = self._request("GET", "/signals", params=params)
        return data.get("signals", [])
    
    def get_open_signals(self) -> List[Dict]:
        """Get open signals available for fading"""
        data = self._request("GET", "/signals/open")
        return data.get("signals", [])
    
    def get_betting_stats(self) -> Dict:
        """Get betting statistics"""
        return self._request("GET", "/betting/stats")
    
    # === Risk ===
    
    def get_alerts(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Get alerts for agent"""
        aid = agent_id or self.agent_id
        data = self._request("GET", f"/alerts/{aid}")
        return data.get("alerts", [])
    
    def get_risk_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get risk metrics for agent"""
        aid = agent_id or self.agent_id
        return self._request("GET", f"/risk/{aid}")


# === Convenience Functions ===

def quick_start(display_name: str, wallet: str, deposit_amount: float = 1000) -> PerpDEX:
    """
    Quick start: register agent, deposit, return ready client
    
    Usage:
        dex = quick_start("MyBot", "0x...", 1000)
        dex.open_long("BTC-PERP", 100, leverage=3)
    """
    # Register
    result = PerpDEX.register(display_name, wallet)
    agent_id = result["agent_id"]
    api_key = result["api_key"]
    
    # Create client
    dex = PerpDEX(api_key=api_key, agent_id=agent_id)
    
    # Deposit
    dex.deposit(deposit_amount)
    
    print(f"✅ Agent {agent_id} ready with ${deposit_amount} balance")
    print(f"   API Key: {api_key}")
    
    return dex


if __name__ == "__main__":
    # Demo
    print("🦞 AI Perp DEX Python SDK Demo\n")
    
    # Get prices (no auth needed)
    dex = PerpDEX()
    prices = dex.get_prices()
    
    print("Current Prices:")
    for asset, data in prices.items():
        print(f"  {asset}: ${data['price']:,.2f}")
    
    print("\n✅ SDK working!")
