#!/usr/bin/env python3
"""
AI Perp DEX - 50 Agent 极端场景压力测试 (Final Version)
增加超时处理和崩溃检测
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
REQUEST_TIMEOUT = 10  # 秒

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
    timeouts: int = 0
    server_errors: int = 0
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
        
    def headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        
    async def request(self, method: str, endpoint: str, data: dict = None, timeout: int = REQUEST_TIMEOUT) -> tuple:
        url = f"{BASE_URL}{endpoint}"
        start = time.time()
        
        try:
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            if method == "GET":
                async with self.session.get(url, headers=self.headers(), timeout=client_timeout) as resp:
                    response_time = (time.time() - start) * 1000
                    result = await resp.json()
                    return resp.status, result, response_time
            elif method == "POST":
                async with self.session.post(url, json=data, headers=self.headers(), timeout=client_timeout) as resp:
                    response_time = (time.time() - start) * 1000
                    result = await resp.json()
                    return resp.status, result, response_time
            elif method == "DELETE":
                async with self.session.delete(url, headers=self.headers(), timeout=client_timeout) as resp:
                    response_time = (time.time() - start) * 1000
                    result = await resp.json()
                    return resp.status, result, response_time
        except asyncio.TimeoutError:
            return 408, {"error": "TIMEOUT"}, (time.time() - start) * 1000
        except aiohttp.ClientError as e:
            return 503, {"error": f"CONNECTION_ERROR: {e}"}, (time.time() - start) * 1000
        except Exception as e:
            return 500, {"error": str(e)}, (time.time() - start) * 1000

class StressTest:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.results: List[TestResult] = []
        self.summary = TestSummary()
        self.all_signals: List[str] = []
        self.server_crashed = False
        
    def record(self, result: TestResult):
        self.results.append(result)
        self.summary.total_operations += 1
        
        if result.success:
            self.summary.successful += 1
        else:
            self.summary.failed += 1
            if "TIMEOUT" in result.error:
                self.summary.timeouts += 1
            elif "CONNECTION" in result.error or "503" in result.error:
                self.summary.server_errors += 1
                
            self.summary.errors.append({
                "operation": result.operation,
                "agent_id": result.agent_id,
                "error": result.error[:200],
                "time": datetime.now().isoformat()
            })
        
        self.summary.max_response_time_ms = max(self.summary.max_response_time_ms, result.response_time_ms)
        if result.response_time_ms > 0:
            self.summary.min_response_time_ms = min(self.summary.min_response_time_ms, result.response_time_ms)

    async def check_server_health(self, session: aiohttp.ClientSession) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.get(f"{BASE_URL}/health", timeout=timeout) as resp:
                return resp.status == 200
        except:
            return False

    async def register_agents(self, session: aiohttp.ClientSession):
        print("\n🚀 Phase 1: Registering 50 Agents...")
        
        roles = {"trader": 20, "signal": 15, "funding": 15}
        agent_idx = 0
        
        for role, count in roles.items():
            for i in range(count):
                agent_idx += 1
                wallet = f"0x{uuid.uuid4().hex[:40]}"
                name = f"{role.upper()}_{agent_idx:03d}"
                
                start = time.time()
                try:
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with session.post(f"{BASE_URL}/agents/register", json={
                        "wallet_address": wallet,
                        "display_name": name,
                        "twitter_handle": f"@{name.lower()}"
                    }, timeout=timeout) as resp:
                        response_time = (time.time() - start) * 1000
                        result = await resp.json()
                        
                        if resp.status == 200 and "agent" in result:
                            agent_id = result["agent"]["agent_id"]
                            api_key = result.get("api_key", "")
                            self.agents[agent_id] = Agent(agent_id, role, api_key, session)
                            
                            self.record(TestResult(
                                operation="register",
                                agent_id=agent_id,
                                success=True,
                                response_time_ms=response_time,
                                details={"name": name, "role": role}
                            ))
                except Exception as e:
                    self.record(TestResult(
                        operation="register",
                        agent_id=name,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error=str(e)
                    ))
        
        print(f"✅ Registered {len(self.agents)}/50 agents")

    async def run_trading_tests(self):
        print("\n📊 Phase 2: Trading Tests (20 Agents)...")
        
        traders = [a for a in self.agents.values() if a.role == "trader"][:20]
        
        # 最小金额
        print("  → Min amount ($1)")
        for agent in traders[:4]:
            await self._test_trade(agent, size=1, leverage=1, test_name="min_amount")
        
        # 最大金额
        print("  → Max amount ($10000)")
        for agent in traders[4:8]:
            await self._test_trade(agent, size=10000, leverage=1, test_name="max_amount")
        
        # 最高杠杆
        print("  → Max leverage (100x)")
        for agent in traders[8:12]:
            await self._test_trade(agent, size=100, leverage=100, test_name="max_leverage")
        
        # 快速开平仓
        print("  → Rapid open/close")
        for agent in traders[12:16]:
            await self._test_rapid_open_close(agent)
        
        # 同时做多做空
        print("  → Simultaneous long/short")
        for agent in traders[16:20]:
            await self._test_simultaneous_long_short(agent)
        
        # 边界测试
        print("  → Edge cases")
        await self._test_trade(traders[0], size=0.001, leverage=1, test_name="tiny")
        await self._test_trade(traders[1], size=100, leverage=150, test_name="over_leverage")
        await self._test_trade(traders[2], size=-100, leverage=5, test_name="negative")

    async def _test_trade(self, agent: Agent, size: float, leverage: int, test_name: str):
        intent_type = random.choice(["long", "short"])
        asset = random.choice(["BTC-PERP", "ETH-PERP", "SOL-PERP"])
        
        status, result, response_time = await agent.request("POST", "/intents", {
            "agent_id": agent.agent_id,
            "intent_type": intent_type,
            "asset": asset,
            "size_usdc": size,
            "leverage": leverage,
            "reason": f"Test: {test_name}"
        })
        
        success = status == 200 and result.get("success", False)
        
        self.record(TestResult(
            operation=f"trade_{test_name}",
            agent_id=agent.agent_id,
            success=success,
            response_time_ms=response_time,
            error="" if success else str(result.get("detail", result))[:100],
            details={"size": size, "leverage": leverage, "type": intent_type}
        ))
        
        # Bug检测
        if test_name == "over_leverage" and success:
            self.summary.bugs.append(f"BUG: Leverage {leverage}x > 100x allowed")
        if test_name == "negative" and success:
            self.summary.bugs.append(f"BUG: Negative size ${size} allowed")

    async def _test_rapid_open_close(self, agent: Agent):
        for i in range(5):
            status, result, response_time = await agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": "long",
                "asset": "ETH-PERP",
                "size_usdc": 100,
                "leverage": 10,
                "reason": f"Rapid {i+1}/5"
            })
            
            self.record(TestResult(
                operation="rapid_open",
                agent_id=agent.agent_id,
                success=status == 200,
                response_time_ms=response_time,
                error="" if status == 200 else str(result.get("detail", ""))[:50]
            ))
            
            if status == 200 and "intent" in result:
                intent_id = result["intent"].get("intent_id")
                if intent_id:
                    status2, result2, close_time = await agent.request("DELETE", f"/intents/{intent_id}")
                    self.record(TestResult(
                        operation="rapid_close",
                        agent_id=agent.agent_id,
                        success=status2 == 200,
                        response_time_ms=close_time
                    ))
            
            await asyncio.sleep(0.05)

    async def _test_simultaneous_long_short(self, agent: Agent):
        long_task = agent.request("POST", "/intents", {
            "agent_id": agent.agent_id,
            "intent_type": "long",
            "asset": "ETH-PERP",
            "size_usdc": 100,
            "leverage": 5
        })
        
        short_task = agent.request("POST", "/intents", {
            "agent_id": agent.agent_id,
            "intent_type": "short",
            "asset": "ETH-PERP",
            "size_usdc": 100,
            "leverage": 5
        })
        
        results = await asyncio.gather(long_task, short_task, return_exceptions=True)
        
        successes = sum(1 for r in results if isinstance(r, tuple) and r[0] == 200)
        
        if successes == 2:
            self.summary.bugs.append(f"BUG: Agent {agent.agent_id} can hold both LONG and SHORT on same asset")
        
        self.record(TestResult(
            operation="simultaneous_long_short",
            agent_id=agent.agent_id,
            success=True,
            response_time_ms=0,
            details={"both_success": successes == 2}
        ))

    async def run_signal_tests(self):
        print("\n📡 Phase 3: Signal Tests (15 Agents)...")
        
        signalers = [a for a in self.agents.values() if a.role == "signal"][:15]
        
        # 创建信号
        print("  → Creating signals")
        for agent in signalers[:5]:
            await self._test_create_signal(agent)
        
        # Fade信号
        print("  → Fading signals")
        for agent in signalers[5:10]:
            await self._test_fade_signal(agent)
        
        # 信号轰炸
        print("  → Signal bombing")
        for agent in signalers[10:15]:
            await self._test_signal_bomb(agent)

    async def _test_create_signal(self, agent: Agent):
        status, result, response_time = await agent.request("POST", "/signals", {
            "agent_id": agent.agent_id,
            "asset": "ETH-PERP",
            "signal_type": random.choice(["price_above", "price_below"]),
            "target_value": random.uniform(2000, 3000),
            "stake_amount": random.uniform(10, 100),
            "duration_hours": random.choice([1, 4, 24])
        })
        
        success = status == 200
        if success and "signal" in result:
            signal_id = result["signal"].get("signal_id")
            if signal_id:
                self.all_signals.append(signal_id)
        
        self.record(TestResult(
            operation="create_signal",
            agent_id=agent.agent_id,
            success=success,
            response_time_ms=response_time
        ))

    async def _test_fade_signal(self, agent: Agent):
        if not self.all_signals:
            status, result, _ = await agent.request("GET", "/signals")
            if status == 200:
                for s in result.get("signals", []):
                    if s.get("status") == "open":
                        self.all_signals.append(s["signal_id"])
        
        if not self.all_signals:
            return
        
        signal_id = random.choice(self.all_signals)
        status, result, response_time = await agent.request("POST", "/signals/fade", {
            "signal_id": signal_id,
            "fader_id": agent.agent_id
        })
        
        self.record(TestResult(
            operation="fade_signal",
            agent_id=agent.agent_id,
            success=status == 200,
            response_time_ms=response_time
        ))

    async def _test_signal_bomb(self, agent: Agent):
        success_count = 0
        for _ in range(10):
            status, result, _ = await agent.request("POST", "/signals", {
                "agent_id": agent.agent_id,
                "asset": random.choice(["BTC-PERP", "ETH-PERP"]),
                "signal_type": "price_above",
                "target_value": random.uniform(1000, 5000),
                "stake_amount": 1,
                "duration_hours": 1
            })
            if status == 200:
                success_count += 1
        
        self.record(TestResult(
            operation="signal_bomb",
            agent_id=agent.agent_id,
            success=success_count >= 7,
            response_time_ms=0,
            details={"sent": 10, "success": success_count}
        ))

    async def run_funding_tests(self):
        print("\n💰 Phase 4: Funding Tests (15 Agents)...")
        
        funders = [a for a in self.agents.values() if a.role == "funding"][:15]
        
        print("  → Checking PnL")
        for agent in funders[:5]:
            status, result, response_time = await agent.request("GET", f"/pnl/{agent.agent_id}")
            self.record(TestResult(
                operation="check_pnl",
                agent_id=agent.agent_id,
                success=status == 200,
                response_time_ms=response_time
            ))
        
        print("  → Near-liquidation trades")
        for agent in funders[5:10]:
            status, result, response_time = await agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": "long",
                "asset": "ETH-PERP",
                "size_usdc": 9000,
                "leverage": 50
            })
            
            success = status == 200
            self.record(TestResult(
                operation="near_liquidation",
                agent_id=agent.agent_id,
                success=success,
                response_time_ms=response_time
            ))
            
            if success:
                self.summary.anomalies.append(f"$450k notional exposure allowed for {agent.agent_id}")
        
        print("  → High-frequency trading")
        for agent in funders[10:15]:
            for i in range(5):
                status, result, response_time = await agent.request("POST", "/intents", {
                    "agent_id": agent.agent_id,
                    "intent_type": random.choice(["long", "short"]),
                    "asset": "ETH-PERP",
                    "size_usdc": 10,
                    "leverage": 2
                })
                self.record(TestResult(
                    operation="hft",
                    agent_id=agent.agent_id,
                    success=status == 200,
                    response_time_ms=response_time
                ))

    async def run_concurrent_load(self, session: aiohttp.ClientSession):
        print("\n⚡ Phase 5: Concurrent Load Test...")
        
        # 检查服务器状态
        if not await self.check_server_health(session):
            self.summary.bugs.append("CRITICAL: Server crashed before concurrent load test")
            self.server_crashed = True
            return
        
        tasks = []
        for agent in list(self.agents.values())[:30]:  # 限制30个并发
            tasks.append(self._concurrent_activity(agent))
        
        start = time.time()
        await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start
        
        print(f"  → Completed in {total_time:.2f}s")
        
        # 检查服务器是否存活
        if not await self.check_server_health(session):
            self.summary.bugs.append("CRITICAL: Server crashed during concurrent load test")
            self.server_crashed = True

    async def _concurrent_activity(self, agent: Agent):
        for _ in range(2):
            op = random.choice(["trade", "signal", "pnl"])
            
            if op == "trade":
                await self._test_trade(agent, size=random.uniform(10, 200), leverage=random.randint(1, 10), test_name="concurrent")
            elif op == "signal":
                await self._test_create_signal(agent)
            else:
                status, result, response_time = await agent.request("GET", f"/pnl/{agent.agent_id}")
                self.record(TestResult(
                    operation="concurrent_pnl",
                    agent_id=agent.agent_id,
                    success=status == 200,
                    response_time_ms=response_time
                ))
            
            await asyncio.sleep(random.uniform(0.05, 0.2))

    async def run_stress_spike(self, session: aiohttp.ClientSession):
        print("\n🔥 Phase 6: Stress Spike Test (50 simultaneous)...")
        
        if self.server_crashed:
            print("  ⚠️ Skipped - server already crashed")
            return
        
        if not await self.check_server_health(session):
            self.summary.bugs.append("CRITICAL: Server not responding before stress spike")
            return
        
        # 50个同时发单 - 使用更短的超时
        tasks = []
        for agent in self.agents.values():
            tasks.append(agent.request("POST", "/intents", {
                "agent_id": agent.agent_id,
                "intent_type": random.choice(["long", "short"]),
                "asset": "ETH-PERP",
                "size_usdc": 100,
                "leverage": 10
            }, timeout=15))
        
        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.time() - start) * 1000
        
        success_count = sum(1 for r in results if isinstance(r, tuple) and r[0] == 200)
        timeout_count = sum(1 for r in results if isinstance(r, tuple) and r[0] == 408)
        error_count = sum(1 for r in results if isinstance(r, tuple) and r[0] >= 500)
        
        self.record(TestResult(
            operation="stress_spike",
            agent_id="ALL",
            success=success_count >= 40,
            response_time_ms=total_time / 50,
            details={"sent": 50, "success": success_count, "timeout": timeout_count, "errors": error_count}
        ))
        
        print(f"  → {success_count}/50 success, {timeout_count} timeouts, {error_count} errors")
        
        if success_count < 40:
            self.summary.anomalies.append(f"Stress spike: only {success_count}/50 orders succeeded")
        
        # 检查服务器是否还活着
        await asyncio.sleep(1)
        if not await self.check_server_health(session):
            self.summary.bugs.append("CRITICAL: Server crashed during stress spike")
            self.server_crashed = True

    def calculate_summary(self):
        if self.results:
            times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
            self.summary.avg_response_time_ms = sum(times) / len(times) if times else 0
        
        if self.summary.min_response_time_ms == float('inf'):
            self.summary.min_response_time_ms = 0

    def get_stability_score(self) -> int:
        score = 10
        
        # 服务器崩溃是致命的
        if self.server_crashed:
            return 1
        
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
        
        # Bug 数量
        critical_bugs = sum(1 for b in self.summary.bugs if "CRITICAL" in b)
        score -= min(critical_bugs * 3, 6)
        score -= min(len(self.summary.bugs) - critical_bugs, 2)
        
        return max(1, min(10, score))

    def get_performance_bottlenecks(self) -> List[str]:
        bottlenecks = []
        
        op_times = defaultdict(list)
        for r in self.results:
            if r.response_time_ms > 0:
                op_times[r.operation].append(r.response_time_ms)
        
        for op, times in op_times.items():
            if not times:
                continue
            avg = sum(times) / len(times)
            max_time = max(times)
            
            if avg > 500:
                bottlenecks.append(f"⚠️ {op}: avg {avg:.0f}ms (SLOW)")
            elif avg > 100:
                bottlenecks.append(f"⚡ {op}: avg {avg:.0f}ms")
        
        if self.summary.timeouts > 0:
            bottlenecks.append(f"🕐 {self.summary.timeouts} request timeouts")
        
        if self.summary.server_errors > 0:
            bottlenecks.append(f"💥 {self.summary.server_errors} server errors")
        
        return bottlenecks

    def save_results(self, path: str) -> dict:
        self.calculate_summary()
        
        # 操作统计
        op_stats = defaultdict(lambda: {"total": 0, "success": 0, "times": []})
        for r in self.results:
            op_stats[r.operation]["total"] += 1
            if r.success:
                op_stats[r.operation]["success"] += 1
            if r.response_time_ms > 0:
                op_stats[r.operation]["times"].append(r.response_time_ms)
        
        for op, stats in op_stats.items():
            stats["avg_ms"] = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
            stats["success_rate"] = f"{stats['success'] / stats['total'] * 100:.1f}%" if stats["total"] > 0 else "N/A"
            del stats["times"]
        
        output = {
            "test_time": datetime.now().isoformat(),
            "server_crashed": self.server_crashed,
            "summary": {
                "total_agents": len(self.agents),
                "total_operations": self.summary.total_operations,
                "successful": self.summary.successful,
                "failed": self.summary.failed,
                "timeouts": self.summary.timeouts,
                "server_errors": self.summary.server_errors,
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
        }
        
        with open(path, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return output

async def main():
    print("=" * 60)
    print("🧪 AI Perp DEX - 50 Agent 极端场景压力测试 (Final)")
    print("=" * 60)
    
    test = StressTest()
    
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 检查服务器
        if not await test.check_server_health(session):
            print("❌ Cannot connect to server at", BASE_URL)
            return
        
        print("✅ Server is healthy")
        
        # 执行测试
        await test.register_agents(session)
        
        if len(test.agents) < 10:
            print("❌ Not enough agents registered")
            return
        
        await test.run_trading_tests()
        
        # 中途检查
        if not await test.check_server_health(session):
            print("⚠️ Server crashed after trading tests!")
            test.server_crashed = True
            test.summary.bugs.append("CRITICAL: Server crashed after trading tests")
        else:
            await test.run_signal_tests()
            
            if not await test.check_server_health(session):
                print("⚠️ Server crashed after signal tests!")
                test.server_crashed = True
                test.summary.bugs.append("CRITICAL: Server crashed after signal tests")
            else:
                await test.run_funding_tests()
                await test.run_concurrent_load(session)
                await test.run_stress_spike(session)
    
    # 保存结果
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
    print(f"  • 超时: {results['summary']['timeouts']}")
    print(f"  • 服务器错误: {results['summary']['server_errors']}")
    print(f"  • 平均响应: {results['summary']['avg_response_time_ms']:.1f}ms")
    print(f"  • 最慢响应: {results['summary']['max_response_time_ms']:.0f}ms")
    
    if test.server_crashed:
        print(f"\n🔴 服务器崩溃: YES")
    
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
    
    print(f"\n📁 详细结果: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
