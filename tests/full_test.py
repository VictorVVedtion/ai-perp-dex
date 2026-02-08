#!/usr/bin/env python3
"""
AI Perp DEX - 专业全面测试套件
覆盖所有 API 端点和业务逻辑
"""

import asyncio
import aiohttp
import json
import time
import random
import string
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

BASE_URL = "http://localhost:8082"

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0

@dataclass
class TestAgent:
    agent_id: str
    api_key: str
    wallet: str

class PerpDEXTester:
    def __init__(self):
        self.results: List[TestResult] = []
        self.agents: List[TestAgent] = []
        self.positions: List[str] = []
        self.signals: List[str] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def _random_wallet(self) -> str:
        return "0x" + "".join(random.choices(string.hexdigits, k=40))
    
    async def _request(self, method: str, path: str, 
                       json_data: dict = None, 
                       api_key: str = None,
                       expected_status: int = None) -> Tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        
        url = f"{BASE_URL}{path}"
        async with self.session.request(method, url, json=json_data, headers=headers) as resp:
            try:
                data = await resp.json()
            except:
                data = {"raw": await resp.text()}
            return resp.status, data
    
    def _record(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.results.append(TestResult(name, passed, message, duration_ms))
        status = "✅" if passed else "❌"
        print(f"  {status} {name}" + (f": {message}" if message and not passed else ""))

    @staticmethod
    def _available_balance(data: dict) -> float:
        """兼容不同余额响应结构."""
        if not isinstance(data, dict):
            return 0.0
        if isinstance(data.get("available"), (int, float)):
            return float(data["available"])
        if isinstance(data.get("balance"), (int, float)):
            return float(data["balance"])
        nested = data.get("balance")
        if isinstance(nested, dict) and isinstance(nested.get("available"), (int, float)):
            return float(nested["available"])
        return 0.0
    
    # ========== 基础 API 测试 ==========
    
    async def test_health(self):
        """健康检查"""
        status, data = await self._request("GET", "/health")
        self._record("健康检查", status == 200 and data.get("status") == "ok")
    
    async def test_prices(self):
        """价格服务"""
        status, data = await self._request("GET", "/prices")
        has_btc = "BTC" in data.get("prices", {})
        has_eth = "ETH" in data.get("prices", {})
        self._record("价格服务", status == 200 and has_btc and has_eth)
    
    async def test_docs(self):
        """API 文档"""
        status, _ = await self._request("GET", "/docs")
        self._record("API 文档", status == 200)
    
    # ========== Agent 注册测试 ==========
    
    async def test_register_agent(self):
        """正常注册"""
        wallet = self._random_wallet()
        status, data = await self._request("POST", "/agents/register", {
            "wallet_address": wallet,
            "display_name": f"Test Agent {len(self.agents)+1}",
            "bio": "Automated test agent"
        })
        
        if status == 200 and data.get("success"):
            agent = TestAgent(
                agent_id=data["agent"]["agent_id"],
                api_key=data["api_key"],
                wallet=wallet
            )
            self.agents.append(agent)
            self._record("Agent 注册", True)
        else:
            self._record("Agent 注册", False, str(data)[:100])
    
    async def test_register_duplicate(self):
        """重复注册拒绝"""
        if not self.agents:
            self._record("重复注册拒绝", False, "No agent to test")
            return
        
        status, data = await self._request("POST", "/agents/register", {
            "wallet_address": self.agents[0].wallet,
            "display_name": "Duplicate"
        })
        self._record("重复注册拒绝", status == 409)
    
    async def test_register_invalid_wallet(self):
        """无效钱包格式"""
        status, data = await self._request("POST", "/agents/register", {
            "wallet_address": "",
            "display_name": "Invalid"
        })
        self._record("空钱包拒绝", status in [400, 422])
    
    async def test_get_agent(self):
        """查询 Agent"""
        if not self.agents:
            self._record("查询 Agent", False, "No agent")
            return
        
        status, data = await self._request("GET", f"/agents/{self.agents[0].agent_id}")
        self._record("查询 Agent", status == 200 and "agent_id" in data)
    
    async def test_get_nonexistent_agent(self):
        """查询不存在的 Agent"""
        status, data = await self._request("GET", "/agents/fake_agent_999")
        self._record("不存在 Agent 返回 404", status == 404)
    
    async def test_list_agents(self):
        """Agent 列表"""
        status, data = await self._request("GET", "/agents")
        self._record("Agent 列表", status == 200 and "agents" in data)
    
    # ========== 认证测试 ==========
    
    async def test_auth_no_key(self):
        """无 API Key 访问受保护端点"""
        status, data = await self._request("POST", "/deposit", {
            "agent_id": "test", "amount": 100
        })
        self._record("无 Key 拒绝", status == 401)
    
    async def test_auth_invalid_key(self):
        """无效 API Key"""
        status, data = await self._request("POST", "/deposit", {
            "agent_id": "test", "amount": 100
        }, api_key="fake_key_12345")
        self._record("无效 Key 拒绝", status in [401, 403])
    
    async def test_auth_cross_agent(self):
        """跨 Agent 操作"""
        if len(self.agents) < 2:
            # 创建第二个 agent
            await self.test_register_agent()
        
        if len(self.agents) >= 2:
            status, data = await self._request("POST", "/deposit", {
                "agent_id": self.agents[1].agent_id,
                "amount": 100
            }, api_key=self.agents[0].api_key)
            self._record("跨 Agent 操作拒绝", status == 403)
        else:
            self._record("跨 Agent 操作拒绝", False, "Could not create second agent")
    
    async def test_auth_me(self):
        """验证当前身份"""
        if not self.agents:
            self._record("身份验证", False, "No agent")
            return
        
        status, data = await self._request("GET", "/auth/me", 
                                           api_key=self.agents[0].api_key)
        self._record("身份验证", status == 200 and "agent" in data)
    
    # ========== Faucet 测试 ==========
    
    async def test_faucet(self):
        """领取 Faucet"""
        if not self.agents:
            self._record("Faucet 领取", False, "No agent")
            return
        
        status, data = await self._request("POST", "/faucet",
                                           api_key=self.agents[0].api_key)
        self._record("Faucet 领取", status == 200 and data.get("new_balance", 0) >= 10000)
    
    async def test_faucet_cooldown(self):
        """Faucet 冷却"""
        if not self.agents:
            self._record("Faucet 冷却", False, "No agent")
            return
        
        status, data = await self._request("POST", "/faucet",
                                           api_key=self.agents[0].api_key)
        self._record("Faucet 冷却限制", status == 429 or "cooldown" in str(data).lower())
    
    # ========== 存款/提款测试 ==========
    
    async def test_deposit(self):
        """存款"""
        if not self.agents:
            self._record("存款", False, "No agent")
            return
        
        status, data = await self._request("POST", "/deposit", {
            "agent_id": self.agents[0].agent_id,
            "amount": 5000
        }, api_key=self.agents[0].api_key)
        self._record("存款", status == 200 and data.get("success"))
    
    async def test_withdraw(self):
        """提款"""
        if not self.agents:
            self._record("提款", False, "No agent")
            return
        
        status, data = await self._request("POST", "/withdraw", {
            "agent_id": self.agents[0].agent_id,
            "amount": 1000
        }, api_key=self.agents[0].api_key)
        self._record("提款", status == 200 and data.get("success"))
    
    async def test_withdraw_insufficient(self):
        """超额提款"""
        if not self.agents:
            self._record("超额提款拒绝", False, "No agent")
            return
        
        status, data = await self._request("POST", "/withdraw", {
            "agent_id": self.agents[0].agent_id,
            "amount": 999999999
        }, api_key=self.agents[0].api_key)
        self._record("超额提款拒绝", status in [400, 422] or "insufficient" in str(data).lower())
    
    async def test_balance(self):
        """余额查询"""
        if not self.agents:
            self._record("余额查询", False, "No agent")
            return
        
        status, data = await self._request(
            "GET",
            f"/balance/{self.agents[0].agent_id}",
            api_key=self.agents[0].api_key,
        )
        has_balance_fields = any(k in data for k in ("available", "total", "balance"))
        self._record("余额查询", status == 200 and has_balance_fields)
    
    async def test_negative_deposit(self):
        """负数存款"""
        if not self.agents:
            self._record("负数存款拒绝", False, "No agent")
            return
        
        status, data = await self._request("POST", "/deposit", {
            "agent_id": self.agents[0].agent_id,
            "amount": -100
        }, api_key=self.agents[0].api_key)
        self._record("负数存款拒绝", status == 422)
    
    # ========== 交易测试 ==========
    
    async def test_open_long(self):
        """开多仓"""
        if not self.agents:
            self._record("开多仓", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "long",
            "asset": "BTC-PERP",
            "size_usdc": 1000,
            "leverage": 5
        }, api_key=self.agents[0].api_key)
        
        if status == 200 and data.get("success"):
            pos_id = data.get("position", {}).get("position_id")
            if pos_id:
                self.positions.append(pos_id)
            self._record("开多仓", True)
        else:
            self._record("开多仓", False, str(data)[:100])
    
    async def test_open_short(self):
        """开空仓"""
        if not self.agents:
            self._record("开空仓", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "short",
            "asset": "ETH-PERP",
            "size_usdc": 500,
            "leverage": 3
        }, api_key=self.agents[0].api_key)
        
        if status == 200 and data.get("success"):
            pos_id = data.get("position", {}).get("position_id")
            if pos_id:
                self.positions.append(pos_id)
            self._record("开空仓", True)
        else:
            self._record("开空仓", False, str(data)[:100])
    
    async def test_open_high_leverage(self):
        """高杠杆 (20x)"""
        if not self.agents:
            self._record("高杠杆开仓", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "long",
            "asset": "SOL-PERP",
            "size_usdc": 100,
            "leverage": 20
        }, api_key=self.agents[0].api_key)
        self._record("高杠杆开仓 (20x)", status == 200 and data.get("success"))
    
    async def test_invalid_asset(self):
        """无效资产"""
        if not self.agents:
            self._record("无效资产拒绝", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "long",
            "asset": "FAKE-PERP",
            "size_usdc": 100,
            "leverage": 2
        }, api_key=self.agents[0].api_key)
        self._record("无效资产拒绝", status in [400, 422])
    
    async def test_excessive_leverage(self):
        """超额杠杆 (>100x)"""
        if not self.agents:
            self._record("超额杠杆拒绝", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "long",
            "asset": "BTC-PERP",
            "size_usdc": 100,
            "leverage": 150
        }, api_key=self.agents[0].api_key)
        self._record("超额杠杆拒绝 (>100x)", status == 422)
    
    async def test_zero_size(self):
        """零金额"""
        if not self.agents:
            self._record("零金额拒绝", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "long",
            "asset": "BTC-PERP",
            "size_usdc": 0,
            "leverage": 2
        }, api_key=self.agents[0].api_key)
        self._record("零金额拒绝", status == 422)
    
    async def test_insufficient_balance(self):
        """余额不足"""
        if not self.agents:
            self._record("余额不足拒绝", False, "No agent")
            return
        
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[0].agent_id,
            "intent_type": "long",
            "asset": "BTC-PERP",
            "size_usdc": 999999999,
            "leverage": 2
        }, api_key=self.agents[0].api_key)
        self._record("余额不足拒绝", status in [400, 422] or "insufficient" in str(data).lower())
    
    # ========== 持仓测试 ==========
    
    async def test_list_positions(self):
        """持仓列表"""
        if not self.agents:
            self._record("持仓列表", False, "No agent")
            return
        
        status, data = await self._request(
            "GET",
            f"/positions/{self.agents[0].agent_id}",
            api_key=self.agents[0].api_key,
        )
        self._record("持仓列表", status == 200 and "positions" in data)
    
    async def test_close_position(self):
        """平仓"""
        if not self.positions:
            self._record("平仓", False, "No position to close")
            return
        
        pos_id = self.positions[0]
        status, data = await self._request("POST", f"/positions/{pos_id}/close",
                                           api_key=self.agents[0].api_key)
        if status == 200:
            self.positions.remove(pos_id)
        self._record("平仓", status == 200 and data.get("success"))
    
    async def test_close_nonexistent(self):
        """平不存在的仓位"""
        if not self.agents:
            self._record("平不存在仓位", False, "No agent")
            return
        
        status, data = await self._request("POST", "/positions/fake_pos_999/close",
                                           api_key=self.agents[0].api_key)
        self._record("平不存在仓位返回 404", status == 404)
    
    async def test_close_others_position(self):
        """平别人的仓位"""
        if len(self.agents) < 2:
            self._record("平别人仓位拒绝", False, "Need 2 agents")
            return
        
        # 给第二个 agent 开仓
        await self._request("POST", "/faucet", api_key=self.agents[1].api_key)
        status, data = await self._request("POST", "/intents", {
            "agent_id": self.agents[1].agent_id,
            "intent_type": "long",
            "asset": "BTC-PERP",
            "size_usdc": 100,
            "leverage": 2
        }, api_key=self.agents[1].api_key)
        
        if data.get("success"):
            other_pos = data["position"]["position_id"]
            # 尝试用 agent 0 平仓
            status, data = await self._request("POST", f"/positions/{other_pos}/close",
                                               api_key=self.agents[0].api_key)
            self._record("平别人仓位拒绝", status == 403 or "don't own" in str(data).lower())
        else:
            self._record("平别人仓位拒绝", False, "Could not create position")
    
    # ========== Signal Betting 测试 ==========
    
    async def test_create_signal(self):
        """创建 Signal"""
        if not self.agents:
            self._record("创建 Signal", False, "No agent")
            return
        
        # 获取当前 BTC 价格
        _, prices = await self._request("GET", "/prices")
        btc_price = prices.get("prices", {}).get("BTC", {}).get("price", 60000)
        
        status, data = await self._request("POST", "/signals", {
            "agent_id": self.agents[0].agent_id,
            "asset": "BTC-PERP",
            "signal_type": "price_above",
            "target_value": btc_price - 5000,
            "stake_amount": 100,
            "duration_hours": 24
        }, api_key=self.agents[0].api_key)
        
        if status == 200 and data.get("success"):
            sig_id = data.get("signal", {}).get("signal_id")
            if sig_id:
                self.signals.append(sig_id)
            self._record("创建 Signal", True)
        else:
            self._record("创建 Signal", False, str(data)[:100])
    
    async def test_signal_stake_deducted(self):
        """Signal 押金扣除"""
        if not self.agents:
            self._record("Signal 押金扣除", False, "No agent")
            return
        
        # 获取余额
        _, bal_before = await self._request(
            "GET",
            f"/balance/{self.agents[0].agent_id}",
            api_key=self.agents[0].api_key,
        )
        before = self._available_balance(bal_before)
        
        # 创建 Signal
        _, prices = await self._request("GET", "/prices")
        btc_price = prices.get("prices", {}).get("BTC", {}).get("price", 60000)
        
        await self._request("POST", "/signals", {
            "agent_id": self.agents[0].agent_id,
            "asset": "BTC-PERP",
            "signal_type": "price_below",
            "target_value": btc_price + 5000,
            "stake_amount": 50,
            "duration_hours": 1
        }, api_key=self.agents[0].api_key)
        
        # 检查余额
        _, bal_after = await self._request(
            "GET",
            f"/balance/{self.agents[0].agent_id}",
            api_key=self.agents[0].api_key,
        )
        after = self._available_balance(bal_after)
        
        self._record("Signal 押金扣除", before - after >= 50)
    
    async def test_fade_self_signal(self):
        """自己 Fade 自己的 Signal"""
        if not self.agents or not self.signals:
            self._record("自 Fade 拒绝", False, "No signal")
            return
        
        status, data = await self._request("POST", "/signals/fade", {
            "fader_id": self.agents[0].agent_id,
            "signal_id": self.signals[0],
            "stake_amount": 100
        }, api_key=self.agents[0].api_key)
        self._record("自 Fade 拒绝", status in [400, 422] or "own" in str(data).lower())
    
    async def test_fade_signal(self):
        """Fade Signal"""
        if len(self.agents) < 2 or not self.signals:
            self._record("Fade Signal", False, "Need 2 agents and signal")
            return
        
        status, data = await self._request("POST", "/signals/fade", {
            "fader_id": self.agents[1].agent_id,
            "signal_id": self.signals[0],
            "stake_amount": 100
        }, api_key=self.agents[1].api_key)
        self._record("Fade Signal", status == 200 and data.get("success"))
    
    async def test_fade_matched_signal(self):
        """重复 Fade 已匹配的 Signal"""
        if len(self.agents) < 2 or not self.signals:
            self._record("重复 Fade 拒绝", False, "Need 2 agents and signal")
            return
        
        status, data = await self._request("POST", "/signals/fade", {
            "fader_id": self.agents[1].agent_id,
            "signal_id": self.signals[0],
            "stake_amount": 100
        }, api_key=self.agents[1].api_key)
        self._record("重复 Fade 拒绝", status in [400, 422] or "matched" in str(data).lower() or "already" in str(data).lower())
    
    async def test_list_signals(self):
        """Signal 列表"""
        status, data = await self._request("GET", "/signals?status=all")
        self._record("Signal 列表", status == 200 and "signals" in data)
    
    # ========== 统计和排行榜测试 ==========
    
    async def test_leaderboard(self):
        """交易排行榜"""
        status, data = await self._request("GET", "/leaderboard?limit=10")
        self._record("交易排行榜", status == 200 and "leaderboard" in data)
    
    async def test_pnl_leaderboard(self):
        """PnL 排行榜"""
        status, data = await self._request("GET", "/pnl-leaderboard?limit=10")
        self._record("PnL 排行榜", status == 200 and "leaderboard" in data)
    
    async def test_intent_stats(self):
        """Intent 统计"""
        status, data = await self._request("GET", "/intents/stats")
        self._record("Intent 统计", status == 200 and "total_intents" in data)
    
    async def test_betting_stats(self):
        """Betting 统计"""
        status, data = await self._request("GET", "/betting/stats")
        self._record("Betting 统计", status == 200)
    
    async def test_platform_stats(self):
        """平台统计"""
        status, data = await self._request("GET", "/stats")
        self._record("平台统计", status == 200)
    
    # ========== 并发测试 ==========
    
    async def test_concurrent_requests(self):
        """并发请求"""
        tasks = [self._request("GET", "/health") for _ in range(50)]
        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        success = sum(1 for r in results if not isinstance(r, Exception) and r[0] == 200)
        self._record(f"并发测试 (50请求/{elapsed:.2f}s)", success >= 45, f"{success}/50 成功")
    
    # ========== WebSocket 测试 ==========
    
    async def test_websocket_connect(self):
        """WebSocket 连接"""
        try:
            async with self.session.ws_connect(f"ws://localhost:8082/ws") as ws:
                # 等待欢迎消息
                msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
                self._record("WebSocket 连接", msg.get("type") == "connected")
        except Exception as e:
            self._record("WebSocket 连接", False, str(e)[:50])
    
    # ========== 运行所有测试 ==========
    
    async def run_all(self):
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║         🦞 AI Perp DEX 专业测试套件                          ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()
        
        # 基础 API
        print("━━━ 1. 基础 API ━━━")
        await self.test_health()
        await self.test_prices()
        await self.test_docs()
        
        # Agent 注册
        print("\n━━━ 2. Agent 注册 ━━━")
        await self.test_register_agent()
        await self.test_register_agent()  # 第二个
        await self.test_register_duplicate()
        await self.test_register_invalid_wallet()
        await self.test_get_agent()
        await self.test_get_nonexistent_agent()
        await self.test_list_agents()
        
        # 认证
        print("\n━━━ 3. 认证安全 ━━━")
        await self.test_auth_no_key()
        await self.test_auth_invalid_key()
        await self.test_auth_cross_agent()
        await self.test_auth_me()
        
        # Faucet
        print("\n━━━ 4. Faucet ━━━")
        await self.test_faucet()
        await self.test_faucet_cooldown()
        
        # 存款/提款
        print("\n━━━ 5. 存款/提款 ━━━")
        await self.test_deposit()
        await self.test_withdraw()
        await self.test_withdraw_insufficient()
        await self.test_balance()
        await self.test_negative_deposit()
        
        # 交易
        print("\n━━━ 6. 交易开仓 ━━━")
        await self.test_open_long()
        await self.test_open_short()
        await self.test_open_high_leverage()
        await self.test_invalid_asset()
        await self.test_excessive_leverage()
        await self.test_zero_size()
        await self.test_insufficient_balance()
        
        # 持仓
        print("\n━━━ 7. 持仓管理 ━━━")
        await self.test_list_positions()
        await self.test_close_position()
        await self.test_close_nonexistent()
        await self.test_close_others_position()
        
        # Signal Betting
        print("\n━━━ 8. Signal Betting ━━━")
        await self.test_create_signal()
        await self.test_signal_stake_deducted()
        await self.test_fade_self_signal()
        await self.test_fade_signal()
        await self.test_fade_matched_signal()
        await self.test_list_signals()
        
        # 统计
        print("\n━━━ 9. 统计和排行榜 ━━━")
        await self.test_leaderboard()
        await self.test_pnl_leaderboard()
        await self.test_intent_stats()
        await self.test_betting_stats()
        await self.test_platform_stats()
        
        # 并发
        print("\n━━━ 10. 性能测试 ━━━")
        await self.test_concurrent_requests()
        
        # WebSocket
        print("\n━━━ 11. WebSocket ━━━")
        await self.test_websocket_connect()
        
        # 汇总
        self.print_summary()
    
    def print_summary(self):
        print()
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                     📊 测试报告                              ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        print(f"\n  总测试数: {total}")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  通过率: {passed/total*100:.1f}%")
        
        if passed/total >= 0.95:
            grade = "A+"
        elif passed/total >= 0.90:
            grade = "A"
        elif passed/total >= 0.85:
            grade = "B+"
        elif passed/total >= 0.80:
            grade = "B"
        else:
            grade = "C"
        
        print(f"  评级: {grade}")
        
        if failed > 0:
            print("\n  ❌ 失败的测试:")
            for r in self.results:
                if not r.passed:
                    print(f"     • {r.name}" + (f": {r.message}" if r.message else ""))
        
        print()


async def main():
    async with PerpDEXTester() as tester:
        await tester.run_all()


if __name__ == "__main__":
    asyncio.run(main())
