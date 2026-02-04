"""Pytest configuration and fixtures for ai_perp_dex tests"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from ai_perp_dex import Client


@pytest_asyncio.fixture
async def client():
    """Create a test client instance"""
    c = Client(
        base_url="http://localhost:8080",
        agent_id="test-agent-001",
        api_key="test-api-key",
    )
    yield c
    await c.close()


@pytest.fixture
def sample_market_data():
    """Sample market data from API"""
    return [
        {
            "market": "BTC-USD",
            "current_price": 50000.0,
            "volume_24h": 1000000.0,
            "open_interest": 500000.0,
            "funding_rate_24h": 0.0001,
        },
        {
            "market": "ETH-USD",
            "current_price": 3000.0,
            "volume_24h": 500000.0,
            "open_interest": 250000.0,
            "funding_rate_24h": 0.0002,
        },
    ]


@pytest.fixture
def sample_request_data():
    """Sample trade request data"""
    return {
        "id": "req-001",
        "agent_id": "test-agent-001",
        "market": "BTC-USD",
        "side": "long",
        "size_usdc": 1000.0,
        "leverage": 10,
        "max_slippage_bps": 100,
        "status": "pending",
        "created_at": "2024-01-15T10:00:00Z",
        "quotes_count": 0,
    }


@pytest.fixture
def sample_quote_data():
    """Sample quote data"""
    return {
        "id": "quote-001",
        "request_id": "req-001",
        "agent_id": "mm-agent-001",
        "funding_rate": 0.001,
        "collateral_usdc": 500.0,
        "created_at": "2024-01-15T10:01:00Z",
    }


@pytest.fixture
def sample_position_data():
    """Sample position data from API"""
    return {
        "id": "pos-001",
        "trader_agent": "test-agent-001",
        "mm_agent": "mm-agent-001",
        "market": "BTC-USD",
        "side": "long",
        "size_usdc": 1000.0,
        "entry_price": 50000.0,
        "leverage": 10,
        "created_at": "2024-01-15T10:02:00Z",
    }
