"""
AI Perp DEX API Tests
Run: pytest tests/test_api.py -v
"""

import pytest
import requests
import time
import uuid

BASE_URL = "http://localhost:8082"


class TestHealth:
    """Health check tests"""
    
    def test_health(self):
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
    
    def test_api_info(self):
        resp = requests.get(f"{BASE_URL}/api")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data or "name" in data


class TestPrices:
    """Price feed tests"""
    
    def test_get_all_prices(self):
        resp = requests.get(f"{BASE_URL}/prices")
        assert resp.status_code == 200
        data = resp.json()
        assert "prices" in data
        assert "BTC" in data["prices"]
        assert data["prices"]["BTC"]["price"] > 0
    
    def test_get_single_price(self):
        resp = requests.get(f"{BASE_URL}/prices/BTC")
        assert resp.status_code == 200
        data = resp.json()
        assert "price" in data
        assert data["price"] > 0


class TestAgentRegistration:
    """Agent registration tests"""
    
    def test_register_agent(self):
        wallet = f"0xTest{uuid.uuid4().hex[:8]}"
        resp = requests.post(
            f"{BASE_URL}/agents/register",
            json={
                "display_name": "TestBot",
                "wallet_address": wallet,
                "description": "Test agent"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert "agent_id" in data["agent"]
        assert "api_key" in data
        assert data["api_key"].startswith("th_")
    
    def test_register_duplicate_wallet(self):
        wallet = f"0xDupe{uuid.uuid4().hex[:8]}"
        # First registration
        requests.post(
            f"{BASE_URL}/agents/register",
            json={"display_name": "First", "wallet_address": wallet}
        )
        # Duplicate should fail
        resp = requests.post(
            f"{BASE_URL}/agents/register",
            json={"display_name": "Second", "wallet_address": wallet}
        )
        # Duplicate registration should be rejected explicitly
        assert resp.status_code in [400, 409]
    
    def test_list_agents(self):
        resp = requests.get(f"{BASE_URL}/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)


class TestTrading:
    """Trading tests"""
    
    @pytest.fixture
    def agent(self):
        """Create a test agent with balance"""
        wallet = f"0xTrade{uuid.uuid4().hex[:8]}"
        reg = requests.post(
            f"{BASE_URL}/agents/register",
            json={"display_name": "TradeTest", "wallet_address": wallet}
        ).json()
        api_key = reg["api_key"]
        agent_id = reg["agent"]["agent_id"]
        
        # Deposit
        requests.post(
            f"{BASE_URL}/deposit",
            headers={"X-API-Key": api_key},
            json={"agent_id": agent_id, "amount": 1000}
        )
        
        return {"agent_id": agent_id, "api_key": api_key}
    
    def test_open_long(self, agent):
        resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "intent_type": "long",
                "asset": "BTC-PERP",
                "size_usdc": 50,
                "leverage": 3
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert "position" in data
        assert data["position"]["side"] == "long"
    
    def test_open_short(self, agent):
        resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "intent_type": "short",
                "asset": "ETH-PERP",
                "size_usdc": 30,
                "leverage": 2
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert data["position"]["side"] == "short"
    
    def test_close_position(self, agent):
        # Open position first
        open_resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "intent_type": "long",
                "asset": "SOL-PERP",
                "size_usdc": 20,
                "leverage": 2
            }
        ).json()
        position_id = open_resp["position"]["position_id"]
        
        # Close it
        resp = requests.post(
            f"{BASE_URL}/positions/{position_id}/close",
            headers={"X-API-Key": agent["api_key"]}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert "pnl" in data
    
    def test_leverage_limit(self, agent):
        """Test that leverage > 20x is rejected"""
        resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "intent_type": "long",
                "asset": "BTC-PERP",
                "size_usdc": 10,
                "leverage": 25  # Should be rejected
            }
        )
        assert resp.status_code == 422  # Validation error
    
    def test_insufficient_balance(self):
        """Test that trading without balance fails"""
        wallet = f"0xPoor{uuid.uuid4().hex[:8]}"
        reg = requests.post(
            f"{BASE_URL}/agents/register",
            json={"display_name": "PoorBot", "wallet_address": wallet}
        ).json()
        
        resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": reg["api_key"]},
            json={
                "agent_id": reg["agent"]["agent_id"],
                "intent_type": "long",
                "asset": "BTC-PERP",
                "size_usdc": 100,
                "leverage": 5
            }
        )
        assert resp.status_code == 400
        assert "Insufficient balance" in resp.json()["detail"]


class TestSignalBetting:
    """Signal betting tests"""
    
    @pytest.fixture
    def two_agents(self):
        """Create two agents for signal betting"""
        agents = []
        for i in range(2):
            wallet = f"0xSig{i}{uuid.uuid4().hex[:6]}"
            reg = requests.post(
                f"{BASE_URL}/agents/register",
                json={"display_name": f"SignalBot{i}", "wallet_address": wallet}
            ).json()
            api_key = reg["api_key"]
            agent_id = reg["agent"]["agent_id"]
            
            # Deposit
            requests.post(
                f"{BASE_URL}/deposit",
                headers={"X-API-Key": api_key},
                json={"agent_id": agent_id, "amount": 500}
            )
            agents.append({"agent_id": agent_id, "api_key": api_key})
        return agents
    
    def test_create_signal(self, two_agents):
        agent = two_agents[0]
        resp = requests.post(
            f"{BASE_URL}/signals",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "asset": "BTC-PERP",
                "signal_type": "price_above",
                "target_value": 80000,
                "confidence": 0.8,
                "timeframe_hours": 1,
                "stake_amount": 50,
                "rationale": "Test signal"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "signal" in data
        assert data["signal"]["signal_id"].startswith("sig_")
    
    def test_fade_signal(self, two_agents):
        creator = two_agents[0]
        fader = two_agents[1]
        
        # Create signal
        sig_resp = requests.post(
            f"{BASE_URL}/signals",
            headers={"X-API-Key": creator["api_key"]},
            json={
                "agent_id": creator["agent_id"],
                "asset": "ETH-PERP",
                "signal_type": "price_below",
                "target_value": 2000,
                "confidence": 0.7,
                "timeframe_hours": 2,
                "stake_amount": 30,
                "rationale": "Test"
            }
        ).json()
        signal_id = sig_resp["signal"]["signal_id"]
        
        # Fade it
        resp = requests.post(
            f"{BASE_URL}/signals/fade",
            headers={"X-API-Key": fader["api_key"]},
            json={
                "signal_id": signal_id,
                "fader_id": fader["agent_id"],
                "stake": 30
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "bet" in data
        assert data["bet"]["bet_id"].startswith("bet_")
    
    def test_cannot_fade_own_signal(self, two_agents):
        agent = two_agents[0]
        
        # Create signal
        sig_resp = requests.post(
            f"{BASE_URL}/signals",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "asset": "SOL-PERP",
                "signal_type": "price_above",
                "target_value": 100,
                "confidence": 0.6,
                "timeframe_hours": 1,
                "stake_amount": 20,
                "rationale": "Self test"
            }
        ).json()
        signal_id = sig_resp["signal"]["signal_id"]
        
        # Try to fade own signal
        resp = requests.post(
            f"{BASE_URL}/signals/fade",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "signal_id": signal_id,
                "fader_id": agent["agent_id"],
                "stake": 20
            }
        )
        assert resp.status_code == 400
        assert "own signal" in resp.json()["detail"].lower()


class TestSecurity:
    """Security tests"""
    
    def test_invalid_api_key(self):
        resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": "invalid_key_123"},
            json={
                "agent_id": "agent_0001",
                "intent_type": "long",
                "asset": "BTC-PERP",
                "size_usdc": 100,
                "leverage": 5
            }
        )
        assert resp.status_code in [401, 403]
        assert "Invalid" in resp.json()["detail"]
    
    def test_cannot_trade_for_other_agent(self):
        # Register two agents
        wallets = [f"0xSec{i}{uuid.uuid4().hex[:6]}" for i in range(2)]
        agents = []
        for w in wallets:
            reg = requests.post(
                f"{BASE_URL}/agents/register",
                json={"display_name": "SecTest", "wallet_address": w}
            ).json()
            agents.append(reg)
        
        # Agent 0 tries to trade for Agent 1
        resp = requests.post(
            f"{BASE_URL}/intents",
            headers={"X-API-Key": agents[0]["api_key"]},
            json={
                "agent_id": agents[1]["agent"]["agent_id"],  # Wrong agent
                "intent_type": "long",
                "asset": "BTC-PERP",
                "size_usdc": 10,
                "leverage": 2
            }
        )
        assert resp.status_code == 403
        assert "another agent" in resp.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestSignalBettingEdgeCases:
    """Signal Betting 边界测试"""
    
    @pytest.fixture
    def agents_with_balance(self):
        """创建两个有余额的 agents"""
        agents = []
        for i in range(2):
            wallet = f"0xSB{i}{uuid.uuid4().hex[:6]}"
            reg = requests.post(
                f"{BASE_URL}/agents/register",
                json={"display_name": f"SBTest{i}", "wallet_address": wallet}
            ).json()
            api_key = reg["api_key"]
            agent_id = reg["agent"]["agent_id"]
            
            # Deposit
            requests.post(
                f"{BASE_URL}/deposit",
                headers={"X-API-Key": api_key},
                json={"agent_id": agent_id, "amount": 200}
            )
            agents.append({"agent_id": agent_id, "api_key": api_key})
        return agents
    
    def test_signal_with_zero_stake(self, agents_with_balance):
        """测试零押注应该失败"""
        agent = agents_with_balance[0]
        resp = requests.post(
            f"{BASE_URL}/signals",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "asset": "BTC-PERP",
                "signal_type": "price_above",
                "target_value": 100000,
                "confidence": 0.8,
                "timeframe_hours": 24,
                "stake_amount": 0,  # Zero stake
                "rationale": "Should fail"
            }
        )
        assert resp.status_code == 422  # Validation error
    
    def test_signal_stake_exceeds_balance(self, agents_with_balance):
        """测试押注超过余额应该失败"""
        agent = agents_with_balance[0]
        resp = requests.post(
            f"{BASE_URL}/signals",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "agent_id": agent["agent_id"],
                "asset": "BTC-PERP",
                "signal_type": "price_above",
                "target_value": 100000,
                "confidence": 0.8,
                "timeframe_hours": 24,
                "stake_amount": 9999,  # More than balance
                "rationale": "Should fail"
            }
        )
        assert resp.status_code in [400, 422]  # Validation or balance error
    
    def test_fade_nonexistent_signal(self, agents_with_balance):
        """测试 fade 不存在的 signal"""
        agent = agents_with_balance[0]
        resp = requests.post(
            f"{BASE_URL}/signals/fade",
            headers={"X-API-Key": agent["api_key"]},
            json={
                "signal_id": "sig_nonexistent",
                "fader_id": agent["agent_id"],
                "stake": 10
            }
        )
        assert resp.status_code in [400, 404]
    
    def test_double_fade_same_signal(self, agents_with_balance):
        """测试同一个 signal 不能被 fade 两次"""
        creator = agents_with_balance[0]
        fader = agents_with_balance[1]
        
        # Create signal
        sig_resp = requests.post(
            f"{BASE_URL}/signals",
            headers={"X-API-Key": creator["api_key"]},
            json={
                "agent_id": creator["agent_id"],
                "asset": "ETH-PERP",
                "signal_type": "price_below",
                "target_value": 1500,
                "confidence": 0.6,
                "timeframe_hours": 12,
                "stake_amount": 10,
                "rationale": "Test double fade"
            }
        ).json()
        signal_id = sig_resp["signal"]["signal_id"]
        
        # First fade - should succeed
        resp1 = requests.post(
            f"{BASE_URL}/signals/fade",
            headers={"X-API-Key": fader["api_key"]},
            json={"signal_id": signal_id, "fader_id": fader["agent_id"], "stake": 10}
        )
        assert resp1.status_code == 200
        
        # Second fade - should fail (already matched)
        resp2 = requests.post(
            f"{BASE_URL}/signals/fade",
            headers={"X-API-Key": fader["api_key"]},
            json={"signal_id": signal_id, "fader_id": fader["agent_id"], "stake": 10}
        )
        assert resp2.status_code == 400
