#!/usr/bin/env python3
"""
AI Perp DEX 压力测试脚本
- 并发创建 20 个 Agent
- 每个 Agent 快速发送 10 个交易 Intent
- 测试 WebSocket 连接稳定性
- 记录响应时间和错误率
"""

import asyncio
import aiohttp
import json
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import random

# 配置
API_BASE = "http://localhost:8082"
WS_URL = "ws://localhost:8082/ws"
NUM_AGENTS = 20
INTENTS_PER_AGENT = 10
ASSETS = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]


@dataclass
class TestResult:
    """单次请求结果"""
    endpoint: str
    success: bool
    latency_ms: float
    status_code: int = 0
    error: str = ""


@dataclass
class AgentContext:
    """Agent 上下文"""
    agent_id: str
    api_key: str
    wallet_address: str


@dataclass
class TestStats:
    """测试统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    rate_limited: int = 0
    server_errors: int = 0
    
    def add_result(self, result: TestResult):
        self.total_requests += 1
        if result.success:
            self.successful_requests += 1
            self.latencies.append(result.latency_ms)
        else:
            self.failed_requests += 1
            error_key = f"{result.status_code}:{result.error[:50]}"
            self.errors[error_key] = self.errors.get(error_key, 0) + 1
            if result.status_code == 429:
                self.rate_limited += 1
            elif result.status_code >= 500:
                self.server_errors += 1
    
    def get_summary(self) -> dict:
        if not self.latencies:
            return {
                "total": self.total_requests,
                "success": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": 0,
            }
        
        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{(self.successful_requests / self.total_requests * 100):.1f}%",
            "latency_avg_ms": round(statistics.mean(self.latencies), 2),
            "latency_p50_ms": round(statistics.median(self.latencies), 2),
            "latency_p95_ms": round(sorted(self.latencies)[int(len(self.latencies) * 0.95)] if len(self.latencies) > 20 else max(self.latencies), 2),
            "latency_p99_ms": round(sorted(self.latencies)[int(len(self.latencies) * 0.99)] if len(self.latencies) > 100 else max(self.latencies), 2),
            "latency_max_ms": round(max(self.latencies), 2),
            "rate_limited": self.rate_limited,
            "server_errors": self.server_errors,
            "error_breakdown": self.errors,
        }


class StressTest:
    """压力测试执行器"""
    
    def __init__(self):
        self.agents: List[AgentContext] = []
        self.stats = {
            "registration": TestStats(),
            "intents": TestStats(),
            "websocket": TestStats(),
        }
        self.ws_messages_received = 0
        self.ws_connections_active = 0
        self.test_start_time: float = 0
        self.test_end_time: float = 0
    
    async def register_agent(self, session: aiohttp.ClientSession, index: int) -> Optional[AgentContext]:
        """注册单个 Agent"""
        wallet = f"0x{index:040x}"
        payload = {
            "wallet_address": wallet,
            "display_name": f"StressBot_{index:03d}",
        }
        
        start = time.perf_counter()
        try:
            async with session.post(f"{API_BASE}/agents/register", json=payload) as resp:
                latency = (time.perf_counter() - start) * 1000
                
                if resp.status == 200:
                    data = await resp.json()
                    result = TestResult("register", True, latency, resp.status)
                    self.stats["registration"].add_result(result)
                    return AgentContext(
                        agent_id=data["agent"]["agent_id"],
                        api_key=data["api_key"],
                        wallet_address=wallet,
                    )
                else:
                    body = await resp.text()
                    result = TestResult("register", False, latency, resp.status, body[:100])
                    self.stats["registration"].add_result(result)
                    return None
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            result = TestResult("register", False, latency, 0, str(e))
            self.stats["registration"].add_result(result)
            return None
    
    async def send_intent(self, session: aiohttp.ClientSession, agent: AgentContext, intent_num: int) -> TestResult:
        """发送单个交易 Intent"""
        intent_type = random.choice(["long", "short"])
        asset = random.choice(ASSETS)
        size = random.randint(10, 500)
        leverage = random.randint(1, 20)
        
        payload = {
            "agent_id": agent.agent_id,
            "intent_type": intent_type,
            "asset": asset,
            "size_usdc": size,
            "leverage": leverage,
            "reason": f"Stress test intent #{intent_num}",
        }
        
        headers = {"X-API-Key": agent.api_key}
        
        start = time.perf_counter()
        try:
            async with session.post(f"{API_BASE}/intents", json=payload, headers=headers) as resp:
                latency = (time.perf_counter() - start) * 1000
                
                if resp.status == 200:
                    return TestResult("intent", True, latency, resp.status)
                else:
                    body = await resp.text()
                    return TestResult("intent", False, latency, resp.status, body[:100])
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return TestResult("intent", False, latency, 0, str(e))
    
    async def agent_worker(self, session: aiohttp.ClientSession, agent: AgentContext) -> List[TestResult]:
        """单个 Agent 的工作循环 - 快速发送 Intent"""
        results = []
        for i in range(INTENTS_PER_AGENT):
            result = await self.send_intent(session, agent, i)
            results.append(result)
            self.stats["intents"].add_result(result)
            # 小延迟避免过于激进 (可调整)
            await asyncio.sleep(0.01)  # 10ms
        return results
    
    async def websocket_listener(self, ws_index: int, duration_seconds: int = 30):
        """WebSocket 监听器"""
        start = time.perf_counter()
        messages = 0
        errors = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(WS_URL, timeout=10) as ws:
                    self.ws_connections_active += 1
                    
                    # 发送 ping
                    await ws.send_json({"type": "ping"})
                    
                    while (time.perf_counter() - start) < duration_seconds:
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                messages += 1
                                self.ws_messages_received += 1
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                        except asyncio.TimeoutError:
                            # 发送心跳
                            await ws.send_json({"type": "ping"})
                    
                    latency = (time.perf_counter() - start) * 1000
                    result = TestResult("ws_connect", True, latency, 200)
                    self.stats["websocket"].add_result(result)
                    
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            result = TestResult("ws_connect", False, latency, 0, str(e))
            self.stats["websocket"].add_result(result)
            errors += 1
        finally:
            self.ws_connections_active = max(0, self.ws_connections_active - 1)
        
        return {"messages": messages, "errors": errors}
    
    async def run_registration_phase(self):
        """Phase 1: 并发注册所有 Agent"""
        print(f"\n{'='*60}")
        print(f"Phase 1: Registering {NUM_AGENTS} agents concurrently...")
        print(f"{'='*60}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.register_agent(session, i) for i in range(NUM_AGENTS)]
            results = await asyncio.gather(*tasks)
            self.agents = [a for a in results if a is not None]
        
        print(f"✓ Registered {len(self.agents)}/{NUM_AGENTS} agents")
        print(f"  Stats: {json.dumps(self.stats['registration'].get_summary(), indent=2)}")
    
    async def run_intent_phase(self):
        """Phase 2: 每个 Agent 并发发送 Intent"""
        if not self.agents:
            print("✗ No agents registered, skipping intent phase")
            return
        
        print(f"\n{'='*60}")
        print(f"Phase 2: Each of {len(self.agents)} agents sending {INTENTS_PER_AGENT} intents...")
        print(f"         Total intents: {len(self.agents) * INTENTS_PER_AGENT}")
        print(f"{'='*60}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.agent_worker(session, agent) for agent in self.agents]
            await asyncio.gather(*tasks)
        
        print(f"✓ Intent submission complete")
        print(f"  Stats: {json.dumps(self.stats['intents'].get_summary(), indent=2)}")
    
    async def run_websocket_phase(self, num_connections: int = 10, duration: int = 15):
        """Phase 3: WebSocket 稳定性测试"""
        print(f"\n{'='*60}")
        print(f"Phase 3: Testing {num_connections} WebSocket connections for {duration}s...")
        print(f"{'='*60}")
        
        tasks = [self.websocket_listener(i, duration) for i in range(num_connections)]
        results = await asyncio.gather(*tasks)
        
        total_messages = sum(r["messages"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        
        print(f"✓ WebSocket test complete")
        print(f"  Connections: {num_connections}")
        print(f"  Total messages received: {total_messages}")
        print(f"  Connection errors: {total_errors}")
        print(f"  Stats: {json.dumps(self.stats['websocket'].get_summary(), indent=2)}")
    
    async def run_concurrent_load_test(self):
        """Phase 4: 高并发混合负载测试"""
        print(f"\n{'='*60}")
        print(f"Phase 4: Concurrent load test (registration + intents + WS)...")
        print(f"{'='*60}")
        
        if not self.agents:
            print("✗ No agents for load test")
            return
        
        # 同时运行:
        # - 5 个新 Agent 注册
        # - 所有现有 Agent 发送 Intent
        # - 5 个 WebSocket 连接
        
        async with aiohttp.ClientSession() as session:
            registration_tasks = [self.register_agent(session, 100 + i) for i in range(5)]
            intent_tasks = [self.agent_worker(session, agent) for agent in self.agents[:5]]
            ws_tasks = [self.websocket_listener(i, 10) for i in range(5)]
            
            all_tasks = registration_tasks + intent_tasks + ws_tasks
            await asyncio.gather(*all_tasks, return_exceptions=True)
        
        print("✓ Concurrent load test complete")
    
    async def run_burst_test(self):
        """Phase 5: 突发请求测试 (测试限流)"""
        print(f"\n{'='*60}")
        print(f"Phase 5: Burst test (testing rate limits)...")
        print(f"{'='*60}")
        
        if not self.agents:
            print("✗ No agents for burst test")
            return
        
        agent = self.agents[0]
        burst_results = []
        
        async with aiohttp.ClientSession() as session:
            # 1秒内发送 20 个请求 (超过 per-agent 限制的 10/s)
            tasks = [self.send_intent(session, agent, i) for i in range(20)]
            results = await asyncio.gather(*tasks)
            
            rate_limited = sum(1 for r in results if r.status_code == 429)
            successful = sum(1 for r in results if r.success)
            
        print(f"✓ Burst test complete")
        print(f"  Requests sent: 20 (in ~instant burst)")
        print(f"  Successful: {successful}")
        print(f"  Rate limited (429): {rate_limited}")
    
    def print_final_report(self):
        """打印最终报告"""
        duration = self.test_end_time - self.test_start_time
        
        print(f"\n{'='*60}")
        print(f"           STRESS TEST FINAL REPORT")
        print(f"{'='*60}")
        print(f"Test Duration: {duration:.2f}s")
        print(f"Agents Created: {len(self.agents)}")
        print(f"")
        
        # Registration stats
        reg_stats = self.stats["registration"].get_summary()
        print(f"📝 REGISTRATION:")
        print(f"   Requests: {reg_stats.get('total_requests', 0)}")
        print(f"   Success Rate: {reg_stats.get('success_rate', 'N/A')}")
        print(f"   Avg Latency: {reg_stats.get('latency_avg_ms', 'N/A')}ms")
        print(f"   P95 Latency: {reg_stats.get('latency_p95_ms', 'N/A')}ms")
        print(f"")
        
        # Intent stats
        int_stats = self.stats["intents"].get_summary()
        print(f"📊 INTENTS:")
        print(f"   Requests: {int_stats.get('total_requests', 0)}")
        print(f"   Success Rate: {int_stats.get('success_rate', 'N/A')}")
        print(f"   Avg Latency: {int_stats.get('latency_avg_ms', 'N/A')}ms")
        print(f"   P95 Latency: {int_stats.get('latency_p95_ms', 'N/A')}ms")
        print(f"   P99 Latency: {int_stats.get('latency_p99_ms', 'N/A')}ms")
        print(f"   Max Latency: {int_stats.get('latency_max_ms', 'N/A')}ms")
        print(f"   Rate Limited: {int_stats.get('rate_limited', 0)}")
        print(f"")
        
        # WebSocket stats
        ws_stats = self.stats["websocket"].get_summary()
        print(f"🔌 WEBSOCKET:")
        print(f"   Connections: {ws_stats.get('total_requests', 0)}")
        print(f"   Success Rate: {ws_stats.get('success_rate', 'N/A')}")
        print(f"   Messages Received: {self.ws_messages_received}")
        print(f"")
        
        # Calculate throughput
        total_requests = (
            self.stats["registration"].total_requests +
            self.stats["intents"].total_requests
        )
        if duration > 0:
            throughput = total_requests / duration
            print(f"⚡ THROUGHPUT: {throughput:.1f} requests/second")
        
        # Error summary
        all_errors = {}
        for stat in self.stats.values():
            for error, count in stat.errors.items():
                all_errors[error] = all_errors.get(error, 0) + count
        
        if all_errors:
            print(f"\n❌ ERROR SUMMARY:")
            for error, count in sorted(all_errors.items(), key=lambda x: -x[1])[:10]:
                print(f"   {count}x: {error}")
        
        print(f"\n{'='*60}")
    
    async def run(self):
        """运行完整压力测试"""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║     AI PERP DEX - STRESS TEST                            ║
║     API: {API_BASE}                              ║
║     Agents: {NUM_AGENTS}, Intents/Agent: {INTENTS_PER_AGENT}                    ║
╚══════════════════════════════════════════════════════════╝
""")
        
        self.test_start_time = time.perf_counter()
        
        # Phase 1: Registration
        await self.run_registration_phase()
        
        # Phase 2: Intents
        await self.run_intent_phase()
        
        # Phase 3: WebSocket
        await self.run_websocket_phase(num_connections=10, duration=15)
        
        # Phase 4: Concurrent load
        await self.run_concurrent_load_test()
        
        # Phase 5: Burst test
        await self.run_burst_test()
        
        self.test_end_time = time.perf_counter()
        
        # Final report
        self.print_final_report()
        
        return self.stats


async def check_server_health():
    """检查服务器是否在线"""
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{API_BASE}/health") as resp:
                if resp.status == 200:
                    return True
    except Exception as e:
        print(f"Health check error: {e}")
    return False


async def main():
    # 检查服务器
    print(f"Checking server health at {API_BASE}...")
    if not await check_server_health():
        print(f"❌ Server not responding at {API_BASE}")
        print("   Please start the server first:")
        print("   cd trading-hub && python -m uvicorn api.server:app --port 8082")
        return
    
    print("✓ Server is healthy\n")
    
    # 运行测试
    test = StressTest()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
