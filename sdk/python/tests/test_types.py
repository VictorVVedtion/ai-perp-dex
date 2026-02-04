"""Tests for ai_perp_dex.types module"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from ai_perp_dex.types import (
    Side,
    Market,
    TradeRequest,
    Quote,
    Position,
    AgentInfo,
    WebSocketMessage,
)


class TestSideEnum:
    """Tests for Side enum"""
    
    def test_side_values(self):
        assert Side.LONG.value == "long"
        assert Side.SHORT.value == "short"
    
    def test_side_from_string(self):
        assert Side("long") == Side.LONG
        assert Side("short") == Side.SHORT
    
    def test_side_invalid(self):
        with pytest.raises(ValueError):
            Side("invalid")


class TestMarket:
    """Tests for Market model"""
    
    def test_market_creation(self):
        market = Market(
            symbol="BTC-USD",
            base_asset="BTC",
            price=50000.0,
        )
        assert market.symbol == "BTC-USD"
        assert market.base_asset == "BTC"
        assert market.quote_asset == "USD"  # default
        assert market.price == 50000.0
        assert market.volume_24h == 0  # default
        assert market.open_interest == 0  # default
        assert market.funding_rate == 0  # default
        assert market.max_leverage == 50  # default
    
    def test_market_full_data(self):
        market = Market(
            symbol="ETH-USD",
            base_asset="ETH",
            quote_asset="USDT",
            price=3000.0,
            volume_24h=1000000.0,
            open_interest=500000.0,
            funding_rate=0.0001,
            max_leverage=100,
        )
        assert market.quote_asset == "USDT"
        assert market.volume_24h == 1000000.0
        assert market.max_leverage == 100
    
    def test_market_missing_required_field(self):
        with pytest.raises(ValidationError):
            Market(base_asset="BTC", price=50000.0)  # missing symbol


class TestTradeRequest:
    """Tests for TradeRequest model"""
    
    def test_trade_request_creation(self):
        req = TradeRequest(
            agent_id="agent-001",
            market="BTC-USD",
            side=Side.LONG,
            size_usdc=1000.0,
        )
        assert req.agent_id == "agent-001"
        assert req.market == "BTC-USD"
        assert req.side == Side.LONG
        assert req.size_usdc == 1000.0
        assert req.leverage == 1  # default
        assert req.max_slippage_bps == 100  # default
        assert req.status == "pending"  # default
        assert req.id is not None  # auto-generated UUID
    
    def test_trade_request_with_leverage(self):
        req = TradeRequest(
            agent_id="agent-001",
            market="ETH-USD",
            side=Side.SHORT,
            size_usdc=5000.0,
            leverage=20,
            max_slippage_bps=50,
        )
        assert req.side == Side.SHORT
        assert req.leverage == 20
        assert req.max_slippage_bps == 50
    
    def test_trade_request_side_string(self):
        req = TradeRequest(
            agent_id="agent-001",
            market="BTC-USD",
            side="long",
            size_usdc=1000.0,
        )
        assert req.side == Side.LONG
    
    def test_trade_request_uuid_uniqueness(self):
        req1 = TradeRequest(agent_id="a", market="BTC-USD", side="long", size_usdc=100)
        req2 = TradeRequest(agent_id="a", market="BTC-USD", side="long", size_usdc=100)
        assert req1.id != req2.id


class TestQuote:
    """Tests for Quote model"""
    
    def test_quote_creation(self):
        quote = Quote(
            request_id="req-001",
            agent_id="mm-001",
            funding_rate=0.001,
            collateral_usdc=500.0,
        )
        assert quote.request_id == "req-001"
        assert quote.agent_id == "mm-001"
        assert quote.funding_rate == 0.001
        assert quote.collateral_usdc == 500.0
        assert quote.id is not None
    
    def test_quote_mm_id_alias(self):
        quote = Quote(
            request_id="req-001",
            agent_id="mm-001",
            funding_rate=0.001,
            collateral_usdc=500.0,
        )
        assert quote.mm_id == quote.agent_id == "mm-001"
    
    def test_quote_with_valid_until(self):
        dt = datetime(2024, 1, 15, 12, 0, 0)
        quote = Quote(
            request_id="req-001",
            agent_id="mm-001",
            funding_rate=0.001,
            collateral_usdc=500.0,
            valid_until=dt,
        )
        assert quote.valid_until == dt


class TestPosition:
    """Tests for Position model"""
    
    def test_position_creation(self):
        pos = Position(
            id="pos-001",
            trader_id="trader-001",
            mm_id="mm-001",
            market="BTC-USD",
            side=Side.LONG,
            size_usdc=1000.0,
            entry_price=50000.0,
            created_at=datetime(2024, 1, 15, 10, 0, 0),
        )
        assert pos.id == "pos-001"
        assert pos.trader_id == "trader-001"
        assert pos.mm_id == "mm-001"
        assert pos.market == "BTC-USD"
        assert pos.side == Side.LONG
        assert pos.size_usdc == 1000.0
        assert pos.entry_price == 50000.0
        assert pos.leverage == 1  # default
        assert pos.unrealized_pnl == 0  # default
    
    def test_position_is_profitable_positive_pnl(self):
        pos = Position(
            id="pos-001",
            trader_id="trader-001",
            mm_id="mm-001",
            market="BTC-USD",
            side=Side.LONG,
            size_usdc=1000.0,
            entry_price=50000.0,
            unrealized_pnl=100.0,
            created_at=datetime.utcnow(),
        )
        assert pos.is_profitable is True
    
    def test_position_is_profitable_negative_pnl(self):
        pos = Position(
            id="pos-001",
            trader_id="trader-001",
            mm_id="mm-001",
            market="BTC-USD",
            side=Side.SHORT,
            size_usdc=1000.0,
            entry_price=50000.0,
            unrealized_pnl=-50.0,
            created_at=datetime.utcnow(),
        )
        assert pos.is_profitable is False
    
    def test_position_is_profitable_zero_pnl(self):
        pos = Position(
            id="pos-001",
            trader_id="trader-001",
            mm_id="mm-001",
            market="BTC-USD",
            side=Side.LONG,
            size_usdc=1000.0,
            entry_price=50000.0,
            unrealized_pnl=0,
            created_at=datetime.utcnow(),
        )
        assert pos.is_profitable is False


class TestAgentInfo:
    """Tests for AgentInfo model"""
    
    def test_agent_info_creation(self):
        info = AgentInfo(
            id="agent-001",
            agent_type="trader",
        )
        assert info.id == "agent-001"
        assert info.agent_type == "trader"
        assert info.is_online is False  # default
        assert info.total_volume == 0  # default
        assert info.total_pnl == 0  # default
        assert info.trade_count == 0  # default
    
    def test_agent_info_mm_type(self):
        info = AgentInfo(
            id="mm-001",
            agent_type="mm",
            is_online=True,
            total_volume=1000000.0,
            total_pnl=5000.0,
            trade_count=150,
        )
        assert info.agent_type == "mm"
        assert info.is_online is True
        assert info.total_volume == 1000000.0


class TestWebSocketMessage:
    """Tests for WebSocketMessage model"""
    
    def test_ws_message_creation(self):
        msg = WebSocketMessage(
            type="request",
            data={"id": "req-001", "market": "BTC-USD"},
        )
        assert msg.type == "request"
        assert msg.data["id"] == "req-001"
        assert msg.timestamp is not None
    
    def test_ws_message_types(self):
        for msg_type in ["request", "quote", "fill", "close", "heartbeat"]:
            msg = WebSocketMessage(type=msg_type, data={})
            assert msg.type == msg_type
    
    def test_ws_message_with_custom_timestamp(self):
        dt = datetime(2024, 1, 15, 10, 0, 0)
        msg = WebSocketMessage(
            type="fill",
            data={"position_id": "pos-001"},
            timestamp=dt,
        )
        assert msg.timestamp == dt
