"""Tests for ai_perp_dex.client module"""

import pytest
import pytest_asyncio
from httpx import Response

from ai_perp_dex import Client, Market, TradeRequest, Quote, Position


class TestClientInit:
    """Tests for Client initialization"""
    
    def test_client_default_values(self):
        client = Client()
        assert client.base_url == "http://localhost:8080"
        assert client.ws_url == "ws://localhost:8080/ws"
        assert client.agent_id is None
        assert client.api_key is None
        assert client.timeout == 30.0
    
    def test_client_custom_values(self):
        client = Client(
            base_url="http://api.example.com",
            ws_url="ws://ws.example.com/stream",
            agent_id="my-agent",
            api_key="secret-key",
            timeout=60.0,
        )
        assert client.base_url == "http://api.example.com"
        assert client.ws_url == "ws://ws.example.com/stream"
        assert client.agent_id == "my-agent"
        assert client.api_key == "secret-key"
        assert client.timeout == 60.0
    
    def test_client_strips_trailing_slash(self):
        client = Client(base_url="http://api.example.com/")
        assert client.base_url == "http://api.example.com"
    
    def test_client_ws_url_derived_from_base(self):
        client = Client(base_url="http://api.example.com:9000")
        assert client.ws_url == "ws://api.example.com:9000/ws"
    
    def test_client_https_to_wss(self):
        client = Client(base_url="https://api.example.com")
        assert client.ws_url == "wss://api.example.com/ws"


class TestClientHealth:
    """Tests for Client.health()"""
    
    @pytest.mark.asyncio
    async def test_health_success(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/health",
            json={"status": "ok", "version": "1.0.0"},
        )
        
        result = await client.health()
        
        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"


class TestClientRegister:
    """Tests for Client.register()"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/agents/register",
            json={
                "success": True,
                "data": {
                    "agent_id": "test-agent-001",
                    "api_key": "new-api-key-123",
                },
            },
        )
        
        result = await client.register(name="Test Agent", is_mm=False)
        
        assert result["success"] is True
        assert client.api_key == "new-api-key-123"
    
    @pytest.mark.asyncio
    async def test_register_without_agent_id(self):
        client = Client(base_url="http://localhost:8080")
        
        with pytest.raises(ValueError, match="agent_id required"):
            await client.register()
        
        await client.close()


class TestClientGetMarkets:
    """Tests for Client.get_markets()"""
    
    @pytest.mark.asyncio
    async def test_get_markets_success(self, httpx_mock, client, sample_market_data):
        httpx_mock.add_response(
            url="http://localhost:8080/markets",
            json={"data": sample_market_data},
        )
        
        markets = await client.get_markets()
        
        assert len(markets) == 2
        assert isinstance(markets[0], Market)
        assert markets[0].symbol == "BTC-USD"
        assert markets[0].price == 50000.0
        assert markets[1].symbol == "ETH-USD"
    
    @pytest.mark.asyncio
    async def test_get_markets_parses_market_field(self, httpx_mock, client):
        """Test that 'market' field is mapped to 'symbol'"""
        httpx_mock.add_response(
            url="http://localhost:8080/markets",
            json={"data": [{"market": "SOL-USD", "current_price": 100.0}]},
        )
        
        markets = await client.get_markets()
        
        assert markets[0].symbol == "SOL-USD"
        assert markets[0].base_asset == "SOL"


class TestClientGetRequests:
    """Tests for Client.get_requests()"""
    
    @pytest.mark.asyncio
    async def test_get_requests_success(self, httpx_mock, client, sample_request_data):
        httpx_mock.add_response(
            url="http://localhost:8080/requests",
            json={"data": [sample_request_data]},
        )
        
        requests = await client.get_requests()
        
        assert len(requests) == 1
        assert isinstance(requests[0], TradeRequest)
        assert requests[0].id == "req-001"
        assert requests[0].market == "BTC-USD"
    
    @pytest.mark.asyncio
    async def test_get_requests_with_status_filter(self, httpx_mock, client, sample_request_data):
        httpx_mock.add_response(
            url="http://localhost:8080/requests?status=pending",
            json={"data": [sample_request_data]},
        )
        
        requests = await client.get_requests(status="pending")
        
        assert len(requests) == 1


class TestClientGetQuotes:
    """Tests for Client.get_quotes()"""
    
    @pytest.mark.asyncio
    async def test_get_quotes_success(self, httpx_mock, client, sample_quote_data):
        httpx_mock.add_response(
            url="http://localhost:8080/quotes/req-001",
            json={"data": [sample_quote_data]},
        )
        
        quotes = await client.get_quotes("req-001")
        
        assert len(quotes) == 1
        assert isinstance(quotes[0], Quote)
        assert quotes[0].id == "quote-001"
        assert quotes[0].funding_rate == 0.001


class TestClientGetPositions:
    """Tests for Client.get_positions()"""
    
    @pytest.mark.asyncio
    async def test_get_positions_success(self, httpx_mock, client, sample_position_data):
        httpx_mock.add_response(
            url="http://localhost:8080/positions/test-agent-001",
            json={"data": [sample_position_data]},
        )
        
        positions = await client.get_positions()
        
        assert len(positions) == 1
        assert isinstance(positions[0], Position)
        assert positions[0].id == "pos-001"
        assert positions[0].trader_id == "test-agent-001"
        assert positions[0].entry_price == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_positions_with_agent_id(self, httpx_mock, client, sample_position_data):
        httpx_mock.add_response(
            url="http://localhost:8080/positions/other-agent",
            json={"data": [sample_position_data]},
        )
        
        positions = await client.get_positions(agent_id="other-agent")
        
        assert len(positions) == 1
    
    @pytest.mark.asyncio
    async def test_get_positions_without_agent_id(self):
        client = Client(base_url="http://localhost:8080")
        
        with pytest.raises(ValueError, match="agent_id required"):
            await client.get_positions()
        
        await client.close()


class TestClientClosePosition:
    """Tests for Client.close_position()"""
    
    @pytest.mark.asyncio
    async def test_close_position_full(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/close",
            json={"success": True, "data": {"closed_size": 1000.0, "pnl": 50.0}},
        )
        
        result = await client.close_position("pos-001")
        
        assert result["success"] is True
        assert result["data"]["pnl"] == 50.0
    
    @pytest.mark.asyncio
    async def test_close_position_partial(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/close",
            json={"success": True, "data": {"closed_size": 500.0}},
        )
        
        result = await client.close_position("pos-001", size_percent=50)
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_close_position_without_agent_id(self):
        client = Client(base_url="http://localhost:8080")
        
        with pytest.raises(ValueError, match="agent_id required"):
            await client.close_position("pos-001")
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_close_position_failure(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/close",
            status_code=400,
            text="Position not found",
        )
        
        with pytest.raises(Exception, match="Close failed"):
            await client.close_position("invalid-pos")


class TestClientCreateRequest:
    """Tests for Client.create_request()"""
    
    @pytest.mark.asyncio
    async def test_create_request_success(self, httpx_mock, client, sample_request_data):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/request",
            json={"data": sample_request_data},
        )
        
        request = await client.create_request(
            market="BTC-USD",
            side="long",
            size_usdc=1000.0,
            leverage=10,
        )
        
        assert isinstance(request, TradeRequest)
        assert request.market == "BTC-USD"
    
    @pytest.mark.asyncio
    async def test_create_request_without_agent_id(self):
        client = Client(base_url="http://localhost:8080")
        
        with pytest.raises(ValueError, match="agent_id required"):
            await client.create_request(
                market="BTC-USD",
                side="long",
                size_usdc=1000.0,
            )
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_create_request_failure(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/request",
            status_code=400,
            text="Invalid market",
        )
        
        with pytest.raises(Exception, match="Request failed"):
            await client.create_request(
                market="INVALID",
                side="long",
                size_usdc=1000.0,
            )


class TestClientCreateQuote:
    """Tests for Client.create_quote()"""
    
    @pytest.mark.asyncio
    async def test_create_quote_success(self, httpx_mock, client, sample_quote_data):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/quote",
            json={"data": sample_quote_data},
        )
        
        quote = await client.create_quote(
            request_id="req-001",
            funding_rate=0.001,
            collateral_usdc=500.0,
        )
        
        assert isinstance(quote, Quote)
        assert quote.funding_rate == 0.001
    
    @pytest.mark.asyncio
    async def test_create_quote_without_agent_id(self):
        client = Client(base_url="http://localhost:8080")
        
        with pytest.raises(ValueError, match="agent_id required"):
            await client.create_quote(
                request_id="req-001",
                funding_rate=0.001,
            )
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_create_quote_failure(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/quote",
            status_code=400,
            text="Request expired",
        )
        
        with pytest.raises(Exception, match="Quote failed"):
            await client.create_quote(
                request_id="expired-req",
                funding_rate=0.001,
            )


class TestClientAcceptQuote:
    """Tests for Client.accept_quote()"""
    
    @pytest.mark.asyncio
    async def test_accept_quote_success(self, httpx_mock, client, sample_position_data):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/accept",
            json={"data": sample_position_data},
        )
        
        position = await client.accept_quote("quote-001", request_id="req-001")
        
        assert isinstance(position, Position)
        assert position.id == "pos-001"
        assert position.market == "BTC-USD"
    
    @pytest.mark.asyncio
    async def test_accept_quote_failure(self, httpx_mock, client):
        httpx_mock.add_response(
            url="http://localhost:8080/trade/accept",
            status_code=400,
            text="Quote expired",
        )
        
        with pytest.raises(Exception, match="Accept failed"):
            await client.accept_quote("expired-quote")


class TestClientWebSocket:
    """Tests for Client WebSocket functionality"""
    
    def test_on_message_decorator(self, client):
        @client.on_message
        def handler(msg):
            pass
        
        assert handler in client._ws_handlers
    
    def test_multiple_handlers(self, client):
        @client.on_message
        def handler1(msg):
            pass
        
        @client.on_message
        def handler2(msg):
            pass
        
        assert len(client._ws_handlers) == 2


class TestClientClose:
    """Tests for Client.close()"""
    
    @pytest.mark.asyncio
    async def test_close_http_client(self):
        client = Client()
        await client.close()
        # Should not raise even when called multiple times
        await client.close()
