"""Legacy async Client compatibility layer.

This module preserves the historical `Client` interface used by
`sdk/python/tests/test_client.py` and older Trade Router integrations.
New integrations should use `TradingHub` from `.client`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import httpx

from .types import Market, Position, Quote, TradeRequest


class Client:
    """Backward-compatible async client for legacy Trade Router endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        ws_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.ws_url = ws_url or self.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        self.agent_id = agent_id
        self.api_key = api_key
        self.timeout = timeout

        self._ws_handlers: List[Callable[[Any], Any]] = []
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    def _auth_headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key} if self.api_key else {}

    @staticmethod
    def _extract_payload(data: Any) -> Any:
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        resp = await self._http.request(
            method,
            path,
            json=json_data,
            params=params,
            headers=self._auth_headers(),
        )
        if resp.status_code >= 400:
            raise Exception(resp.text or f"HTTP {resp.status_code}")
        if not resp.text:
            return {}
        return resp.json()

    def _require_agent(self, agent_id: Optional[str] = None) -> str:
        aid = agent_id or self.agent_id
        if not aid:
            raise ValueError("agent_id required")
        return aid

    @staticmethod
    def _to_market(item: dict) -> Market:
        symbol = item.get("symbol") or item.get("market")
        base_asset = item.get("base_asset") or (symbol.split("-")[0] if symbol else "")
        return Market(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=item.get("quote_asset", "USD"),
            price=item.get("price", item.get("current_price", 0.0)),
            volume_24h=item.get("volume_24h", 0.0),
            open_interest=item.get("open_interest", 0.0),
            funding_rate=item.get("funding_rate", item.get("funding_rate_24h", 0.0)),
            max_leverage=item.get("max_leverage", 50),
        )

    @staticmethod
    def _to_request(item: dict) -> TradeRequest:
        return TradeRequest(
            id=item.get("id"),
            agent_id=item.get("agent_id"),
            market=item.get("market"),
            side=item.get("side"),
            size_usdc=item.get("size_usdc", 0.0),
            leverage=item.get("leverage", 1),
            max_slippage_bps=item.get("max_slippage_bps", 100),
            status=item.get("status", "pending"),
            created_at=item.get("created_at"),
            expires_at=item.get("expires_at"),
            quotes_count=item.get("quotes_count", 0),
        )

    @staticmethod
    def _to_quote(item: dict) -> Quote:
        return Quote(
            id=item.get("id"),
            request_id=item.get("request_id"),
            agent_id=item.get("agent_id"),
            funding_rate=item.get("funding_rate", 0.0),
            collateral_usdc=item.get("collateral_usdc", 0.0),
            valid_until=item.get("valid_until"),
            created_at=item.get("created_at"),
        )

    @staticmethod
    def _to_position(item: dict) -> Position:
        return Position(
            id=item.get("id", item.get("position_id")),
            trader_id=item.get("trader_id", item.get("trader_agent")),
            mm_id=item.get("mm_id", item.get("mm_agent")),
            market=item.get("market", item.get("asset")),
            side=item.get("side"),
            size_usdc=item.get("size_usdc", 0.0),
            entry_price=item.get("entry_price", 0.0),
            mark_price=item.get("mark_price", item.get("current_price")),
            leverage=item.get("leverage", 1),
            unrealized_pnl=item.get("unrealized_pnl", 0.0),
            created_at=item.get("created_at"),
        )

    async def health(self) -> Dict[str, Any]:
        return await self._request("GET", "/health")

    async def register(self, name: str = "Agent", is_mm: bool = False) -> Dict[str, Any]:
        aid = self._require_agent()
        result = await self._request(
            "POST",
            "/agents/register",
            json_data={
                "agent_id": aid,
                "display_name": name,
                "is_mm": is_mm,
            },
        )
        payload = self._extract_payload(result)
        if isinstance(payload, dict) and payload.get("api_key"):
            self.api_key = payload["api_key"]
        return result

    async def get_markets(self) -> List[Market]:
        result = await self._request("GET", "/markets")
        payload = self._extract_payload(result)
        if not isinstance(payload, list):
            return []
        return [self._to_market(item) for item in payload]

    async def get_requests(self, status: Optional[str] = None) -> List[TradeRequest]:
        params = {"status": status} if status else None
        result = await self._request("GET", "/requests", params=params)
        payload = self._extract_payload(result)
        if not isinstance(payload, list):
            return []
        return [self._to_request(item) for item in payload]

    async def get_quotes(self, request_id: str) -> List[Quote]:
        result = await self._request("GET", f"/quotes/{request_id}")
        payload = self._extract_payload(result)
        if not isinstance(payload, list):
            return []
        return [self._to_quote(item) for item in payload]

    async def get_positions(self, agent_id: Optional[str] = None) -> List[Position]:
        aid = self._require_agent(agent_id)
        result = await self._request("GET", f"/positions/{aid}")
        payload = self._extract_payload(result)
        if isinstance(payload, dict) and "positions" in payload:
            payload = payload["positions"]
        if not isinstance(payload, list):
            return []
        return [self._to_position(item) for item in payload]

    async def close_position(
        self,
        position_id: str,
        *,
        size_percent: int = 100,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        aid = self._require_agent(agent_id)
        try:
            return await self._request(
                "POST",
                "/trade/close",
                json_data={"position_id": position_id, "agent_id": aid, "size_percent": size_percent},
            )
        except Exception as exc:  # noqa: BLE001
            raise Exception(f"Close failed: {exc}") from exc

    async def create_request(
        self,
        *,
        market: str,
        side: str,
        size_usdc: float,
        leverage: int = 1,
        max_slippage_bps: int = 100,
        agent_id: Optional[str] = None,
    ) -> TradeRequest:
        aid = self._require_agent(agent_id)
        try:
            result = await self._request(
                "POST",
                "/trade/request",
                json_data={
                    "agent_id": aid,
                    "market": market,
                    "side": side,
                    "size_usdc": size_usdc,
                    "leverage": leverage,
                    "max_slippage_bps": max_slippage_bps,
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise Exception(f"Request failed: {exc}") from exc
        payload = self._extract_payload(result)
        return self._to_request(payload)

    async def create_quote(
        self,
        *,
        request_id: str,
        funding_rate: float,
        collateral_usdc: float = 0.0,
        valid_for: int = 10,
        agent_id: Optional[str] = None,
    ) -> Quote:
        aid = self._require_agent(agent_id)
        try:
            result = await self._request(
                "POST",
                "/trade/quote",
                json_data={
                    "request_id": request_id,
                    "agent_id": aid,
                    "funding_rate": funding_rate,
                    "collateral_usdc": collateral_usdc,
                    "valid_for": valid_for,
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise Exception(f"Quote failed: {exc}") from exc
        payload = self._extract_payload(result)
        return self._to_quote(payload)

    async def accept_quote(
        self,
        quote_id: str,
        *,
        request_id: Optional[str] = None,
        signature: str = "",
        agent_id: Optional[str] = None,
    ) -> Position:
        aid = self._require_agent(agent_id)
        body = {"quote_id": quote_id, "agent_id": aid, "signature": signature}
        if request_id:
            body["request_id"] = request_id
        try:
            result = await self._request("POST", "/trade/accept", json_data=body)
        except Exception as exc:  # noqa: BLE001
            raise Exception(f"Accept failed: {exc}") from exc
        payload = self._extract_payload(result)
        return self._to_position(payload)

    def on_message(self, handler: Callable[[Any], Any]) -> Callable[[Any], Any]:
        self._ws_handlers.append(handler)
        return handler

    async def close(self):
        await self._http.aclose()
