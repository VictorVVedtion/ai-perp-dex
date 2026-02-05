#!/usr/bin/env python3
"""
AI Perp DEX - 50 Agent 极端场景压力测试 (带鉴权)
"""

import asyncio
import aiohttp
import json
import time
import random
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

BASE_URL = "http://localhost:8082"

@dataclass
class TestResult:
    operation: str
    agent_id: str
    success: bool
    response_time_ms: float
    error: str = ""
    details: Dict = field(default_factory=dict)

@dataclass
class TestSummary:
    total_operations: int = 0
    successful: int = 0
    failed: int = 0
    avg_response_time_ms: float = 0
    max_response_time_ms: float = 0
    min_response_time_ms: float = float('inf')
    errors: List[Dict] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    bugs: List[str] = field(default_factory=list)

class Agent:
    def __init__(self, agent_id: str, role: str, api_key: str, session: aiohttp.ClientSession):
        self.agent_id = agent_id
        self.role = role
        self.api_key = api_key
        self.session = session
        self.balance = 10000.0
        self.intents: List[str] = []
        self.signals: List[str] = []
        
    def headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        
    async def request(self, method: str, endpoint: str, data: dict = None) -> tuple:
        url = f"{BASE_URL}{endpoint}"
        start = time.time()
        
        try:
            if method == "GET":
                async with self.session.get(url, headers=self.headers()) as resp:
                    response_time = (time.time() - start) * 1000
                    result = await resp.json()
                    return resp.status, result, response_time
            elif method == "POST":
                async with self.session.post(url, json=data, headers=self.headers()) as resp:
                    response_time = (time.time() - start) * 1000
                    result = await resp.json()
                    return resp.status, result, response_time
            elif method == "DELETE":
                async with self.session.delete(url, headers=self.headers()) as resp:
                    response_time = (time.time() - start) * 1000
                    result = await resp.json()
                    return resp.status, result, response_time
        except Exception as e:
            response_time = (time.time() - start) * 1000
            return 500, {"error": str(e)}, response_time

class StressTest:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.results: List[TestResult] = []
        self.summary = TestSummary()
        self.all_signals: List[str] = []  # 所有创建的信号ID
        
    def record(self, result: TestResult):
        self.results.append(result)
        self.summary.total_operations += 1
        
        if result.success:
            self.summary.successful += 1
        else:
            self.summary.failed += 1
            self.summary.errors.append({
                "operation": result.operation,
                "agent_id": result.agent_id,
                "error": result.error[:200],  # 截断长错误
                "time": datetime.now().isoformat()
            })
        
        self.summary.max_response_time_ms = max(self.summary.max_response_time_ms, result.response_time_ms)
        if result.response_time_ms > 0:
            self.summary.min_response_time_ms = min(self.summary.min_response_time_ms, result.response_time_ms)
        
    async def register_agents(self, session: aiohttp.ClientSession):
        print("\n🚀 Phase 1: Registering 50 Agents...")
        
        roles = {"trader": 20, "signal": 15, "funding": 15}
        agent_idx = 0
        tasks = []
        
        for role, count in roles.items():
            for i in range(count):
                agent_idx += 1
                wallet = f"0x{uuid.uuid4().hex[:40]}"
                name = f"{role.upper()}_{agent_idx:03d}"
                tasks.append(self._register_one_agent(session, wallet, name, role, agent_idx))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r and isinstance(r, str))
        print(f"✅ Registered {success_count}/50 agents")
        
    async def _register_one_agent(self, session: aiohttp.ClientSession, wallet: str, name: str, role: str, idx: int) -> Optional[str]:
        start = time.time()
        
        try:
            async with session.post(f"{BASE_URL}/agents/register", json={
                "wallet_address": wallet,
                "display_name": name,
                "twitter_handle": f"@{name.lower()}"
            }) as resp:
                response_time = (time.time() - start) * 1000
                result = await resp.json()
                
                if resp.status == 200 and "agent" in result:
                    agent_id = result["agent"]["agent_id"]
                    api_key = result.get("api_key", "")  # 获取API key
                    
                    self.agents[agent_id] = Agent(agent_id, role, api_key, session)
                    
                    self.record(TestResult(
                        operation="register",
                        agent_id=agent_id,
                        success=True,
                        response_time_ms=response_time,
                        details={"name": name, "role": role, "has_api_key": bool(api_key)}
                    ))
                    return agent_id
                else:
                    self.record(TestResult(
                        operation="register",
                        agent_id=name,
                        success=False,
                        response_time_ms=response_time,
                        error=str(result)
                    ))
                    return None
        except Exception as e:
            self.record(TestResult(
                operation="register",
                agent_id=name,
                success=False,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            ))
            return None

    async def run_trading_tests(self, session: aiohttp.ClientSession):
        print("\n📊 Phase 2: Trading Tests (20 Agents)...")
        
        traders = [a for a in self.agents.values() if a.role == "trader"]
        if len(traders) < 20:
            print(f"⚠️ Only {len(traders)} traders available")
        
        # Test 1: 最小金额 ($1)
        print("  → Testing minimum amount ($1)")
        tasks1 = [self._test_trade(agent, size=1, leverage=1, test_name="min_amount") for agent in traders[:4]]
        await asyncio.gather(*tasks1)
        
        # Test 2: 最大金额 ($10000)
        print("  → Testing maximum amount ($10000)")
        tasks2 = [self._test_trade(agent, size=10000, leverage=1, test_name="max_amount") for agent in traders[4:8]]
        await asyncio.gather(*tasks2)
        
        # Test 3: 最高杠杆 (100x)
        print("  → Testing maximum leverage (100x)")
        tasks3 = [self._test_trade(agent, size=100, leverage=100, test_name="max_leverage") for agent in traders[8:12]]
        await asyncio.gather(*tasks3)
        
        # Test 4: 快速开平仓
        print("  → Testing rapid open/close")
        tasks4 = [self._test_rapid_open_close(agent) for agent in traders[12:16]]
        await asyncio.gather(*tasks4)
        
        # Test 5: 同时做多做空
        print("  → Testing simultaneous long/short")
        tasks5 = [self._test_simultaneous_long_short(agent) for agent in traders[16:20]]
        await asyncio.gather(*tasks5)
        
        # Test 6: 边界值测试
        print("  → Testing edge cases")
        edge_tests = [
            self._test_trade(traders[0], size=0.001, leverage=1, test_name="tiny_amount"),  # 极小金额
            self._test_trade(traders[1], size=100, leverage=101, test_name="over_leverage"),  # 超过100x
            self._test_trade(traders[2], size=-100, leverage=5, test_name="negative_size"),  # 负金额
            self._test_trade(traders[3], size=100, leverage=0, test_name="zero_leverage"),  # 0杠杆
        ]
        await asyncio.gather(*edge_tests)
        
    async def _test_trade(self, agent: Agent, size: float, leverage: int, test_name: str):
        start = time.time()
        intent_type = random.choice(["long", "short"])
        asset = random.choice(["BTC-PERP", "ETH-PERP", "SOL-PERP"])
        
        try:
            status, result, response_time = await agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": intent_type,
                "asset": asset,
                "size_usdc": size,
                "leverage": leverage,
                "reason": f"Stress test: {test_name}"
            })
            
            success = status == 200 and result.get("success", False)
            
            # 记录intent ID
            if success and "intent" in result:
                intent_id = result["intent"].get("intent_id")
                if intent_id:
                    agent.intents.append(intent_id)
            
            self.record(TestResult(
                operation=f"trade_{test_name}",
                agent_id=agent.agent_id,
                success=success,
                response_time_ms=response_time,
                error="" if success else str(result.get("detail", result))[:200],
                details={
                    "size": size,
                    "leverage": leverage,
                    "type": intent_type,
                    "asset": asset,
                    "internal_rate": result.get("routing", {}).get("internal_rate", "N/A") if success else "N/A"
                }
            ))
            
            # 边界条件检查
            if test_name == "over_leverage" and success:
                self.summary.bugs.append(f"BUG: Leverage > 100x allowed ({leverage}x)")
            if test_name == "negative_size" and success:
                self.summary.bugs.append(f"BUG: Negative size allowed (${size})")
            if test_name == "zero_leverage" and success:
                self.summary.bugs.append(f"BUG: Zero leverage allowed")
            if test_name == "tiny_amount" and success and size < 1:
                self.summary.anomalies.append(f"允许极小金额交易: ${size}")
                
        except Exception as e:
            self.record(TestResult(
                operation=f"trade_{test_name}",
                agent_id=agent.agent_id,
                success=False,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            ))

    async def _test_rapid_open_close(self, agent: Agent):
        """快速开平仓 - 5轮"""
        for i in range(5):
            # 开仓
            status, result, open_time = await agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": "long",
                "asset": "ETH-PERP",
                "size_usdc": 100,
                "leverage": 10,
                "reason": f"Rapid test {i+1}/5"
            })
            
            self.record(TestResult(
                operation="rapid_open",
                agent_id=agent.agent_id,
                success=status == 200,
                response_time_ms=open_time,
                error="" if status == 200 else str(result.get("detail", ""))[:100]
            ))
            
            # 立即平仓 (cancel intent)
            intent_id = result.get("intent", {}).get("intent_id") if status == 200 else None
            if intent_id:
                status2, result2, close_time = await agent.request("DELETE", f"/intents/{intent_id}")
                
                self.record(TestResult(
                    operation="rapid_close",
                    agent_id=agent.agent_id,
                    success=status2 == 200,
                    response_time_ms=close_time
                ))
            
            await asyncio.sleep(0.01)

    async def _test_simultaneous_long_short(self, agent: Agent):
        """同时做多做空同一资产"""
        start = time.time()
        
        # 并发提交 long 和 short
        long_task = agent.request("POST", "/intents", {
            "agent_id": agent.agent_id,
            "intent_type": "long",
            "asset": "ETH-PERP",
            "size_usdc": 100,
            "leverage": 5,
            "reason": "Simultaneous test - LONG"
        })
        
        short_task = agent.request("POST", "/intents", {
            "agent_id": agent.agent_id,
            "intent_type": "short",
            "asset": "ETH-PERP",
            "size_usdc": 100,
            "leverage": 5,
            "reason": "Simultaneous test - SHORT"
        })
        
        results = await asyncio.gather(long_task, short_task, return_exceptions=True)
        response_time = (time.time() - start) * 1000
        
        long_success = short_success = False
        for r in results:
            if isinstance(r, tuple) and r[0] == 200:
                intent = r[1].get("intent", {})
                if intent.get("intent_type") == "long":
                    long_success = True
                else:
                    short_success = True
        
        # 两个都成功可能是bug
        if long_success and short_success:
            self.summary.bugs.append(
                f"BUG: Agent {agent.agent_id} 同时持有 LONG 和 SHORT 同一资产 (对冲风险)"
            )
        
        self.record(TestResult(
            operation="simultaneous_long_short",
            agent_id=agent.agent_id,
            success=True,
            response_time_ms=response_time,
            details={"long": long_success, "short": short_success}
        ))

    async def run_signal_tests(self, session: aiohttp.ClientSession):
        print("\n📡 Phase 3: Signal Tests (15 Agents)...")
        
        signalers = [a for a in self.agents.values() if a.role == "signal"]
        
        # Test 1: 创建信号
        print("  → Creating signals")
        tasks1 = [self._test_create_signal(agent) for agent in signalers[:5]]
        await asyncio.gather(*tasks1)
        
        # Test 2: Fade 信号 (需要先有信号)
        print("  → Fading signals")
        await asyncio.sleep(0.1)  # 等待信号创建
        tasks2 = [self._test_fade_signal(agent) for agent in signalers[5:10]]
        await asyncio.gather(*tasks2)
        
        # Test 3: 信号轰炸
        print("  → Signal bombing (20 signals each)")
        tasks3 = [self._test_signal_bomb(agent) for agent in signalers[10:15]]
        await asyncio.gather(*tasks3)
        
        # Test 4: 边界测试
        print("  → Signal edge cases")
        if signalers:
            edge_tests = [
                self._test_signal_edge_case(signalers[0], stake=0, name="zero_stake"),
                self._test_signal_edge_case(signalers[0], stake=-10, name="negative_stake"),
                self._test_signal_edge_case(signalers[0], duration=0, name="zero_duration"),
                self._test_signal_edge_case(signalers[0], target=0, name="zero_target"),
            ]
            await asyncio.gather(*edge_tests)

    async def _test_create_signal(self, agent: Agent):
        start = time.time()
        
        try:
            status, result, response_time = await agent.request("POST", "/signals", {
                "agent_id": agent.agent_id,
                "asset": "ETH-PERP",
                "signal_type": random.choice(["price_above", "price_below"]),
                "target_value": random.uniform(2000, 3000),
                "stake_amount": random.uniform(10, 100),
                "duration_hours": random.choice([1, 4, 12, 24])
            })
            
            success = status == 200
            if success and "signal" in result:
                signal_id = result["signal"].get("signal_id")
                if signal_id:
                    agent.signals.append(signal_id)
                    self.all_signals.append(signal_id)
            
            self.record(TestResult(
                operation="create_signal",
                agent_id=agent.agent_id,
                success=success,
                response_time_ms=response_time,
                error="" if success else str(result.get("detail", result))[:100],
                details={"signal_id": result.get("signal", {}).get("signal_id") if success else None}
            ))
        except Exception as e:
            self.record(TestResult(
                operation="create_signal",
                agent_id=agent.agent_id,
                success=False,
                response_time_ms=(time.time() - start) * 1000,
                error=str(e)
            ))

    async def _test_fade_signal(self, agent: Agent):
        """Fade一个已存在的信号"""
        if not self.all_signals:
            # 先获取可用信号
            status, result, _ = await agent.request("GET", "/signals")
            if status == 200:
                signals = result.get("signals", [])
                for s in signals:
                    if s.get("status") == "open" and s.get("signal_id"):
                        self.all_signals.append(s["signal_id"])
        
        if not self.all_signals:
            self.record(TestResult(
                operation="fade_signal",
                agent_id=agent.agent_id,
                success=False,
                response_time_ms=0,
                error="No signals available to fade"
            ))
            return
        
        signal_id = random.choice(self.all_signals)
        start = time.time()
        
        status, result, response_time = await agent.request("POST", "/signals/fade", {
            "signal_id": signal_id,
            "fader_id": agent.agent_id
        })
        
        self.record(TestResult(
            operation="fade_signal",
            agent_id=agent.agent_id,
            success=status == 200,
            response_time_ms=response_time,
            error="" if status == 200 else str(result.get("detail", result))[:100],
            details={"signal_id": signal_id}
        ))

    async def _test_signal_bomb(self, agent: Agent):
        """信号轰炸 - 快速创建20个信号"""
        success_count = 0
        total_time = 0
        
        for i in range(20):
            start = time.time()
            status, result, response_time = await agent.request("POST", "/signals", {
                "agent_id": agent.agent_id,
                "asset": random.choice(["BTC-PERP", "ETH-PERP", "SOL-PERP"]),
                "signal_type": "price_above",
                "target_value": random.uniform(1000, 5000),
                "stake_amount": 1,
                "duration_hours": 1
            })
            
            if status == 200:
                success_count += 1
                if "signal" in result:
                    signal_id = result["signal"].get("signal_id")
                    if signal_id:
                        self.all_signals.append(signal_id)
            
            total_time += response_time
        
        self.record(TestResult(
            operation="signal_bomb",
            agent_id=agent.agent_id,
            success=success_count >= 15,
            response_time_ms=total_time / 20,
            details={"sent": 20, "success": success_count}
        ))
        
        if success_count < 15:
            self.summary.anomalies.append(
                f"Signal bomb: only {success_count}/20 signals created for {agent.agent_id}"
            )

    async def _test_signal_edge_case(self, agent: Agent, stake=50, duration=24, target=2500, name="edge"):
        start = time.time()
        
        status, result, response_time = await agent.request("POST", "/signals", {
            "agent_id": agent.agent_id,
            "asset": "ETH-PERP",
            "signal_type": "price_above",
            "target_value": target,
            "stake_amount": stake,
            "duration_hours": duration
        })
        
        success = status == 200
        
        # 边界检查
        if success:
            if stake <= 0:
                self.summary.bugs.append(f"BUG: 允许 stake={stake} 的信号")
            if duration <= 0:
                self.summary.bugs.append(f"BUG: 允许 duration={duration}h 的信号")
            if target <= 0:
                self.summary.bugs.append(f"BUG: 允许 target={target} 的信号")
        
        self.record(TestResult(
            operation=f"signal_{name}",
            agent_id=agent.agent_id,
            success=True,  # 测试本身成功
            response_time_ms=response_time,
            details={"allowed": success, "stake": stake, "duration": duration}
        ))

    async def run_funding_tests(self, session: aiohttp.ClientSession):
        print("\n💰 Phase 4: Funding Tests (15 Agents)...")
        
        funders = [a for a in self.agents.values() if a.role == "funding"]
        
        # Test 1: 检查PnL
        print("  → Checking PnL")
        tasks1 = [self._test_check_pnl(agent) for agent in funders[:5]]
        await asyncio.gather(*tasks1)
        
        # Test 2: 接近清算的交易
        print("  → Near-liquidation trades")
        tasks2 = [self._test_near_liquidation(agent) for agent in funders[5:10]]
        await asyncio.gather(*tasks2)
        
        # Test 3: 高频交易
        print("  → High-frequency trading")
        tasks3 = [self._test_high_frequency(agent) for agent in funders[10:15]]
        await asyncio.gather(*tasks3)

    async def _test_check_pnl(self, agent: Agent):
        start = time.time()
        
        status, result, response_time = await agent.request("GET", f"/pnl/{agent.agent_id}")
        
        self.record(TestResult(
            operation="check_pnl",
            agent_id=agent.agent_id,
            success=status == 200,
            response_time_ms=response_time,
            error="" if status == 200 else str(result.get("detail", ""))[:100]
        ))

    async def _test_near_liquidation(self, agent: Agent):
        """高杠杆大仓位 - 测试清算保护"""
        start = time.time()
        
        status, result, response_time = await agent.request("POST", "/intents", {
            "agent_id": agent.agent_id,
            "intent_type": "long",
            "asset": "ETH-PERP",
            "size_usdc": 9000,  # 接近全部资金
            "leverage": 50,     # 高杠杆
            "reason": "Near liquidation test"
        })
        
        success = status == 200 and result.get("success", False)
        
        self.record(TestResult(
            operation="near_liquidation",
            agent_id=agent.agent_id,
            success=success,
            response_time_ms=response_time,
            error="" if success else str(result.get("detail", ""))[:100],
            details={
                "size": 9000,
                "leverage": 50,
                "notional": 9000 * 50
            }
        ))
        
        if success:
            self.summary.anomalies.append(
                f"Agent {agent.agent_id}: $450k notional exposure allowed (margin check?)"
            )

    async def _test_high_frequency(self, agent: Agent):
        """高频交易 - 100ms内发10单"""
        success_count = 0
        times = []
        
        for i in range(10):
            start = time.time()
            status, result, response_time = await agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": random.choice(["long", "short"]),
                "asset": "ETH-PERP",
                "size_usdc": 10,
                "leverage": 2,
                "reason": f"HFT test {i+1}"
            })
            
            times.append(response_time)
            if status == 200:
                success_count += 1
        
        avg_time = sum(times) / len(times) if times else 0
        
        self.record(TestResult(
            operation="high_frequency",
            agent_id=agent.agent_id,
            success=success_count >= 8,
            response_time_ms=avg_time,
            details={"sent": 10, "success": success_count, "avg_ms": avg_time}
        ))
        
        if avg_time > 100:
            self.summary.anomalies.append(f"HFT slow: avg {avg_time:.0f}ms for {agent.agent_id}")

    async def run_concurrent_load(self, session: aiohttp.ClientSession):
        print("\n⚡ Phase 5: Concurrent Load Test (All 50 Agents)...")
        
        tasks = [self._concurrent_agent_activity(agent) for agent in self.agents.values()]
        
        start = time.time()
        await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start
        
        print(f"  → Completed in {total_time:.2f}s ({len(self.agents) * 3} operations)")

    async def _concurrent_agent_activity(self, agent: Agent):
        for _ in range(3):
            op = random.choice(["trade", "signal", "check_pnl", "stats"])
            
            if op == "trade":
                await self._test_trade(agent, 
                                       size=random.uniform(10, 500),
                                       leverage=random.randint(1, 20),
                                       test_name="concurrent")
            elif op == "signal":
                await self._test_create_signal(agent)
            elif op == "check_pnl":
                await self._test_check_pnl(agent)
            else:
                status, result, response_time = await agent.request("GET", "/stats")
                self.record(TestResult(
                    operation="check_stats",
                    agent_id=agent.agent_id,
                    success=status == 200,
                    response_time_ms=response_time
                ))
            
            await asyncio.sleep(random.uniform(0.01, 0.05))

    async def run_stress_spike(self, session: aiohttp.ClientSession):
        """压力峰值测试 - 所有50个Agent同时发单"""
        print("\n🔥 Phase 6: Stress Spike (50 simultaneous orders)...")
        
        tasks = []
        for agent in self.agents.values():
            tasks.append(agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": random.choice(["long", "short"]),
                "asset": "ETH-PERP",
                "size_usdc": 100,
                "leverage": 10,
                "reason": "Stress spike test"
            }))
        
        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.time() - start) * 1000
        
        success_count = sum(1 for r in results if isinstance(r, tuple) and r[0] == 200)
        avg_time = sum(r[2] for r in results if isinstance(r, tuple)) / len(results) if results else 0
        
        self.record(TestResult(
            operation="stress_spike",
            agent_id="ALL",
            success=success_count >= 40,
            response_time_ms=avg_time,
            details={"sent": 50, "success": success_count, "total_ms": total_time}
        ))
        
        print(f"  → {success_count}/50 orders succeeded, avg {avg_time:.0f}ms")
        
        if success_count < 40:
            self.summary.bugs.append(f"BUG: Stress spike failed {50 - success_count}/50 orders")

    def calculate_summary(self):
        if self.results:
            times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
            self.summary.avg_response_time_ms = sum(times) / len(times) if times else 0
        
        if self.summary.min_response_time_ms == float('inf'):
            self.summary.min_response_time_ms = 0

    def get_stability_score(self) -> int:
        score = 10
        
        if self.summary.total_operations > 0:
            error_rate = self.summary.failed / self.summary.total_operations
            if error_rate > 0.5:
                score -= 5
            elif error_rate > 0.3:
                score -= 3
            elif error_rate > 0.1:
                score -= 2
            elif error_rate > 0.05:
                score -= 1
        
        if self.summary.avg_response_time_ms > 1000:
            score -= 2
        elif self.summary.avg_response_time_ms > 500:
            score -= 1
        
        score -= min(len(self.summary.bugs), 3)
        score -= min(len(self.summary.anomalies) // 3, 2)
        
        return max(1, min(10, score))

    def get_performance_bottlenecks(self) -> List[str]:
        bottlenecks = []
        
        op_times = defaultdict(list)
        for r in self.results:
            if r.response_time_ms > 0:
                op_times[r.operation].append(r.response_time_ms)
        
        for op, times in op_times.items():
            avg = sum(times) / len(times) if times else 0
            max_time = max(times) if times else 0
            
            if avg > 500:
                bottlenecks.append(f"⚠️ {op}: avg {avg:.0f}ms (SLOW)")
            elif avg > 200:
                bottlenecks.append(f"⚡ {op}: avg {avg:.0f}ms (moderate)")
            
            if max_time > 2000:
                bottlenecks.append(f"🐌 {op}: max {max_time:.0f}ms (spike)")
        
        return bottlenecks

    def save_results(self, path: str):
        self.calculate_summary()
        
        # 按操作类型分组统计
        op_stats = defaultdict(lambda: {"total": 0, "success": 0, "avg_ms": 0, "times": []})
        for r in self.results:
            op_stats[r.operation]["total"] += 1
            if r.success:
                op_stats[r.operation]["success"] += 1
            op_stats[r.operation]["times"].append(r.response_time_ms)
        
        for op, stats in op_stats.items():
            stats["avg_ms"] = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
            stats["success_rate"] = f"{stats['success'] / stats['total'] * 100:.1f}%" if stats["total"] > 0 else "N/A"
            del stats["times"]
        
        output = {
            "test_time": datetime.now().isoformat(),
            "summary": {
                "total_agents": len(self.agents),
                "total_operations": self.summary.total_operations,
                "successful": self.summary.successful,
                "failed": self.summary.failed,
                "success_rate": f"{self.summary.successful / self.summary.total_operations * 100:.1f}%" if self.summary.total_operations > 0 else "N/A",
                "avg_response_time_ms": round(self.summary.avg_response_time_ms, 2),
                "max_response_time_ms": round(self.summary.max_response_time_ms, 2),
                "min_response_time_ms": round(self.summary.min_response_time_ms, 2),
            },
            "stability_score": self.get_stability_score(),
            "bugs": self.summary.bugs,
            "anomalies": self.summary.anomalies,
            "performance_bottlenecks": self.get_performance_bottlenecks(),
            "operation_stats": dict(op_stats),
            "errors": self.summary.errors[:30],
            "detailed_results": [
                {
                    "operation": r.operation,
                    "agent_id": r.agent_id,
                    "success": r.success,
                    "response_time_ms": round(r.response_time_ms, 2),
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results[:300]
            ]
        }
        
        with open(path, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return output

async def main():
    print("=" * 60)
    print("🧪 AI Perp DEX - 50 Agent 极端场景压力测试")
    print("=" * 60)
    
    test = StressTest()
    
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status != 200:
                    print("❌ Server not healthy!")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return
        
        print("✅ Server is healthy")
        
        await test.register_agents(session)
        
        if len(test.agents) < 10:
            print("❌ Not enough agents registered, aborting")
            return
        
        await test.run_trading_tests(session)
        await test.run_signal_tests(session)
        await test.run_funding_tests(session)
        await test.run_concurrent_load(session)
        await test.run_stress_spike(session)
    
    output_path = "/tmp/stress_test_results.json"
    results = test.save_results(output_path)
    
    # 打印报告
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)
    
    print(f"\n📈 总体统计:")
    print(f"  • 注册 Agent: {len(test.agents)}")
    print(f"  • 总操作数: {results['summary']['total_operations']}")
    print(f"  • 成功率: {results['summary']['success_rate']}")
    print(f"  • 平均响应: {results['summary']['avg_response_time_ms']:.1f}ms")
    print(f"  • 最慢响应: {results['summary']['max_response_time_ms']:.0f}ms")
    
    print(f"\n🏆 系统稳定性评分: {results['stability_score']}/10")
    
    if results['bugs']:
        print(f"\n🐛 发现的 Bug ({len(results['bugs'])}):")
        for bug in results['bugs']:
            print(f"  • {bug}")
    else:
        print("\n✅ 未发现明显 Bug")
    
    if results['anomalies']:
        print(f"\n⚠️ 异常行为 ({len(results['anomalies'])}):")
        for anomaly in results['anomalies'][:10]:
            print(f"  • {anomaly}")
    
    if results['performance_bottlenecks']:
        print(f"\n🔧 性能瓶颈:")
        for bottleneck in results['performance_bottlenecks']:
            print(f"  {bottleneck}")
    
    print(f"\n📁 详细结果已保存到: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
