#!/usr/bin/env python3
"""
AI Perp DEX 压力测试脚本 v2
- 改进连接管理，避免连接耗尽
- 分批处理避免过载
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

# 连接配置 - 关键改进
CONNECTOR_LIMIT = 50  # 总连接数限制
CONNECTOR_PER_HOST = 30  # 每个 host 的连接数
REQUEST_TIMEOUT = 30  # 请求超时(秒)


@dataclass
class TestResult:
    endpoint: str
    success: bool
    latency_ms: float
    status_code: int = 0
    error: str = ""


@dataclass
class AgentContext:
    agent_id: str
    api_key: str
    wallet_address: str


@dataclass 
class TestStats:
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
                "success_rate": "0%",
            }
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{(self.successful_requests / self.total_requests * 100):.1f}%",
            "latency_avg_ms": round(statistics.mean(self.latencies), 2),
            "latency_min_ms": round(min(self.latencies), 2),
            "latency_p50_ms": round(sorted_latencies[n // 2], 2),
            "latency_p95_ms": round(sorted_latencies[int(n * 0.95)] if n > 20 else sorted_latencies[-1], 2),
            "latency_p99_ms": round(sorted_latencies[int(n * 0.99)] if n > 100 else sorted_latencies[-1], 2),
            "latency_max_ms": round(max(self.latencies), 2),
            "rate_limited": self.rate_limited,
            "server_errors": self.server_errors,
            "error_breakdown": dict(list(self.errors.items())[:5]),  # Top 5 errors
        }


class StressTestV2:
    """压力测试执行器 V2 - 改进版"""
    
    def __init__(self):
        self.agents: List[AgentContext] = []
        self.stats = {
            "registration": TestStats(),
            "intents": TestStats(),
            "websocket": TestStats(),
            "reads": TestStats(),
        }
        self.ws_messages_received = 0
        self.test_start_time: float = 0
        self.test_end_time: float = 0
    
    def _create_session(self) -> aiohttp.ClientSession:
        """创建配置好的 session"""
        connector = aiohttp.TCPConnector(
            limit=CONNECTOR_LIMIT,
            limit_per_host=CONNECTOR_PER_HOST,
        )
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        return aiohttp.ClientSession(connector=connector, timeout=timeout)
    
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
            result = TestResult("register", False, latency, 0, str(e)[:100])
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
            return TestResult("intent", False, latency, 0, str(e)[:100])
    
    async def read_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> TestResult:
        """读取端点测试"""
        start = time.perf_counter()
        try:
            async with session.get(f"{API_BASE}{endpoint}") as resp:
                latency = (time.perf_counter() - start) * 1000
                if resp.status == 200:
                    return TestResult(endpoint, True, latency, resp.status)
                else:
                    body = await resp.text()
                    return TestResult(endpoint, False, latency, resp.status, body[:100])
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return TestResult(endpoint, False, latency, 0, str(e)[:100])
    
    async def websocket_test(self, index: int, duration_seconds: int = 10):
        """WebSocket 连接测试"""
        start = time.perf_counter()
        messages = 0
        
        try:
            timeout = aiohttp.ClientTimeout(total=duration_seconds + 5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.ws_connect(WS_URL) as ws:
                    # 发送 ping
                    await ws.send_json({"type": "ping"})
                    
                    while (time.perf_counter() - start) < duration_seconds:
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                messages += 1
                                self.ws_messages_received += 1
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                        except asyncio.TimeoutError:
                            await ws.send_json({"type": "ping"})
                    
                    latency = (time.perf_counter() - start) * 1000
                    result = TestResult("ws", True, latency, 200)
                    self.stats["websocket"].add_result(result)
                    return {"success": True, "messages": messages}
                    
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            result = TestResult("ws", False, latency, 0, str(e)[:100])
            self.stats["websocket"].add_result(result)
            return {"success": False, "error": str(e), "messages": messages}
    
    async def run_registration_phase(self):
        """Phase 1: 分批注册 Agent"""
        print(f"\n{'='*60}")
        print(f"Phase 1: Registering {NUM_AGENTS} agents (batch of 5)...")
        print(f"{'='*60}")
        
        async with self._create_session() as session:
            # 分批注册，每批 5 个
            for batch_start in range(0, NUM_AGENTS, 5):
                batch_end = min(batch_start + 5, NUM_AGENTS)
                tasks = [self.register_agent(session, i) for i in range(batch_start, batch_end)]
                results = await asyncio.gather(*tasks)
                self.agents.extend([a for a in results if a is not None])
                print(f"  Batch {batch_start//5 + 1}: {sum(1 for a in results if a)} agents registered")
                await asyncio.sleep(0.1)  # 批次间短暂延迟
        
        print(f"✓ Registered {len(self.agents)}/{NUM_AGENTS} agents")
        print(f"  Stats: {json.dumps(self.stats['registration'].get_summary(), indent=2)}")
    
    async def run_intent_phase(self):
        """Phase 2: 每个 Agent 发送 Intent"""
        if not self.agents:
            print("✗ No agents registered, skipping intent phase")
            return
        
        total_intents = len(self.agents) * INTENTS_PER_AGENT
        print(f"\n{'='*60}")
        print(f"Phase 2: {len(self.agents)} agents × {INTENTS_PER_AGENT} intents = {total_intents} total")
        print(f"{'='*60}")
        
        async with self._create_session() as session:
            # 每个 agent 发送 intents，但限制并发
            semaphore = asyncio.Semaphore(10)  # 最多 10 个并发请求
            
            async def send_with_limit(agent, i):
                async with semaphore:
                    result = await self.send_intent(session, agent, i)
                    self.stats["intents"].add_result(result)
                    return result
            
            tasks = []
            for agent in self.agents:
                for i in range(INTENTS_PER_AGENT):
                    tasks.append(send_with_limit(agent, i))
            
            # 分批执行
            batch_size = 50
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                await asyncio.gather(*batch)
                progress = min(i + batch_size, len(tasks))
                print(f"  Progress: {progress}/{len(tasks)} intents sent")
        
        print(f"✓ Intent submission complete")
        print(f"  Stats: {json.dumps(self.stats['intents'].get_summary(), indent=2)}")
    
    async def run_read_load_test(self):
        """Phase 3: 并发读取测试"""
        print(f"\n{'='*60}")
        print(f"Phase 3: Concurrent read load test...")
        print(f"{'='*60}")
        
        endpoints = [
            "/stats",
            "/prices",
            "/agents",
            "/intents",
            "/leaderboard",
            "/matches",
        ]
        
        async with self._create_session() as session:
            tasks = []
            # 每个端点测试 20 次
            for _ in range(20):
                for endpoint in endpoints:
                    tasks.append(self.read_endpoint(session, endpoint))
            
            results = await asyncio.gather(*tasks)
            for r in results:
                self.stats["reads"].add_result(r)
        
        print(f"✓ Read load test complete")
        print(f"  Stats: {json.dumps(self.stats['reads'].get_summary(), indent=2)}")
    
    async def run_websocket_phase(self, num_connections: int = 5, duration: int = 10):
        """Phase 4: WebSocket 稳定性测试"""
        print(f"\n{'='*60}")
        print(f"Phase 4: Testing {num_connections} WebSocket connections for {duration}s...")
        print(f"{'='*60}")
        
        tasks = [self.websocket_test(i, duration) for i in range(num_connections)]
        results = await asyncio.gather(*tasks)
        
        successful = sum(1 for r in results if r.get("success"))
        total_messages = sum(r.get("messages", 0) for r in results)
        
        print(f"✓ WebSocket test complete")
        print(f"  Successful connections: {successful}/{num_connections}")
        print(f"  Total messages received: {total_messages}")
        print(f"  Stats: {json.dumps(self.stats['websocket'].get_summary(), indent=2)}")
    
    async def run_burst_test(self):
        """Phase 5: 突发测试"""
        print(f"\n{'='*60}")
        print(f"Phase 5: Rate limit burst test...")
        print(f"{'='*60}")
        
        if not self.agents:
            print("✗ No agents for burst test")
            return
        
        agent = self.agents[0]
        burst_stats = TestStats()
        
        async with self._create_session() as session:
            # 快速发送 15 个请求（超过 10/s 限制）
            tasks = [self.send_intent(session, agent, i) for i in range(15)]
            results = await asyncio.gather(*tasks)
            
            for r in results:
                burst_stats.add_result(r)
        
        print(f"✓ Burst test complete")
        print(f"  Requests: 15 (limit: 10/s per agent)")
        print(f"  Successful: {burst_stats.successful_requests}")
        print(f"  Rate limited (429): {burst_stats.rate_limited}")
        print(f"  Server errors (5xx): {burst_stats.server_errors}")
    
    def print_final_report(self):
        """打印最终报告"""
        duration = self.test_end_time - self.test_start_time
        
        print(f"\n{'='*60}")
        print(f"           STRESS TEST FINAL REPORT")
        print(f"{'='*60}")
        print(f"Test Duration: {duration:.2f}s")
        print(f"Agents Created: {len(self.agents)}")
        print(f"")
        
        # Registration
        reg = self.stats["registration"].get_summary()
        print(f"📝 REGISTRATION ({reg.get('total_requests', 0)} requests)")
        print(f"   Success Rate: {reg.get('success_rate', 'N/A')}")
        print(f"   Latency - Avg: {reg.get('latency_avg_ms', 'N/A')}ms, P95: {reg.get('latency_p95_ms', 'N/A')}ms")
        print()
        
        # Intents
        intent = self.stats["intents"].get_summary()
        print(f"📊 INTENTS ({intent.get('total_requests', 0)} requests)")
        print(f"   Success Rate: {intent.get('success_rate', 'N/A')}")
        print(f"   Latency - Avg: {intent.get('latency_avg_ms', 'N/A')}ms, P95: {intent.get('latency_p95_ms', 'N/A')}ms, Max: {intent.get('latency_max_ms', 'N/A')}ms")
        print(f"   Rate Limited: {intent.get('rate_limited', 0)}")
        print()
        
        # Reads
        reads = self.stats["reads"].get_summary()
        print(f"📖 READ ENDPOINTS ({reads.get('total_requests', 0)} requests)")
        print(f"   Success Rate: {reads.get('success_rate', 'N/A')}")
        print(f"   Latency - Avg: {reads.get('latency_avg_ms', 'N/A')}ms, P95: {reads.get('latency_p95_ms', 'N/A')}ms")
        print()
        
        # WebSocket
        ws = self.stats["websocket"].get_summary()
        print(f"🔌 WEBSOCKET ({ws.get('total_requests', 0)} connections)")
        print(f"   Success Rate: {ws.get('success_rate', 'N/A')}")
        print(f"   Messages Received: {self.ws_messages_received}")
        print()
        
        # Throughput
        total_requests = sum(s.total_requests for s in self.stats.values())
        if duration > 0:
            throughput = total_requests / duration
            print(f"⚡ OVERALL THROUGHPUT: {throughput:.1f} requests/second")
            print(f"   Total Requests: {total_requests}")
        
        # Error summary
        all_errors = {}
        for stat in self.stats.values():
            for error, count in stat.errors.items():
                all_errors[error] = all_errors.get(error, 0) + count
        
        if all_errors:
            print(f"\n❌ TOP ERRORS:")
            for error, count in sorted(all_errors.items(), key=lambda x: -x[1])[:5]:
                print(f"   {count}x: {error}")
        
        print(f"\n{'='*60}")
    
    async def run(self):
        """运行完整测试"""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║     AI PERP DEX - STRESS TEST v2                         ║
║     API: {API_BASE}                              ║
║     Config: {NUM_AGENTS} agents × {INTENTS_PER_AGENT} intents              ║
╚══════════════════════════════════════════════════════════╝
""")
        
        self.test_start_time = time.perf_counter()
        
        await self.run_registration_phase()
        await self.run_intent_phase()
        await self.run_read_load_test()
        await self.run_websocket_phase(num_connections=5, duration=10)
        await self.run_burst_test()
        
        self.test_end_time = time.perf_counter()
        self.print_final_report()
        
        return self.stats


async def main():
    # Check server health
    print("Checking server health...")
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{API_BASE}/health") as resp:
                if resp.status != 200:
                    print(f"❌ Server returned {resp.status}")
                    return
                print("✓ Server is healthy\n")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Start the server first:")
        print("   cd trading-hub && python -m uvicorn api.server:app --port 8082")
        return
    
    test = StressTestV2()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
