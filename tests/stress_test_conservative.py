#!/usr/bin/env python3
"""
AI Perp DEX 压力测试脚本 - 保守版
更低的并发，更准确的性能指标
"""

import asyncio
import aiohttp
import json
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random

# 配置 - 保守参数
API_BASE = "http://localhost:8082"
WS_URL = "ws://localhost:8082/ws"
NUM_AGENTS = 20
INTENTS_PER_AGENT = 10
ASSETS = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]

# 连接配置 - 更保守
MAX_CONCURRENT = 5  # 最大并发请求数
REQUEST_TIMEOUT = 60  # 更长超时
DELAY_BETWEEN_BATCHES = 0.5  # 批次间延迟


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


@dataclass 
class TestStats:
    total: int = 0
    success: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    rate_limited: int = 0
    
    def add(self, result: TestResult):
        self.total += 1
        if result.success:
            self.success += 1
            self.latencies.append(result.latency_ms)
        else:
            self.failed += 1
            key = f"{result.status_code}:{result.error[:40]}"
            self.errors[key] = self.errors.get(key, 0) + 1
            if result.status_code == 429:
                self.rate_limited += 1
    
    def summary(self) -> dict:
        if not self.latencies:
            return {"total": self.total, "success": self.success, "failed": self.failed, "rate": "0%"}
        
        s = sorted(self.latencies)
        n = len(s)
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "rate": f"{self.success/self.total*100:.1f}%",
            "latency_avg": round(statistics.mean(s), 1),
            "latency_min": round(s[0], 1),
            "latency_p50": round(s[n//2], 1),
            "latency_p95": round(s[int(n*0.95)] if n > 20 else s[-1], 1),
            "latency_max": round(s[-1], 1),
            "rate_limited": self.rate_limited,
        }


class ConservativeStressTest:
    def __init__(self):
        self.agents: List[AgentContext] = []
        self.stats = {
            "register": TestStats(),
            "intent": TestStats(),
            "read": TestStats(),
            "ws": TestStats(),
        }
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.ws_messages = 0
    
    async def _request(self, session: aiohttp.ClientSession, method: str, url: str, 
                       json_data: dict = None, headers: dict = None) -> TestResult:
        """统一的请求方法，带信号量控制"""
        async with self.semaphore:
            start = time.perf_counter()
            try:
                if method == "GET":
                    async with session.get(url, headers=headers) as resp:
                        latency = (time.perf_counter() - start) * 1000
                        if resp.status == 200:
                            return TestResult(url, True, latency, resp.status)
                        body = await resp.text()
                        return TestResult(url, False, latency, resp.status, body[:100])
                else:
                    async with session.post(url, json=json_data, headers=headers) as resp:
                        latency = (time.perf_counter() - start) * 1000
                        if resp.status == 200:
                            data = await resp.json()
                            return TestResult(url, True, latency, resp.status, json.dumps(data)[:200])
                        body = await resp.text()
                        return TestResult(url, False, latency, resp.status, body[:100])
            except Exception as e:
                latency = (time.perf_counter() - start) * 1000
                return TestResult(url, False, latency, 0, str(e)[:100])
    
    async def register_agent(self, session: aiohttp.ClientSession, idx: int) -> Optional[AgentContext]:
        """注册 Agent"""
        start = time.perf_counter()
        try:
            async with self.semaphore:
                async with session.post(f"{API_BASE}/agents/register", json={
                    "wallet_address": f"0x{idx:040x}",
                    "display_name": f"StressBot_{idx:03d}",
                }) as resp:
                    latency = (time.perf_counter() - start) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        self.stats["register"].add(TestResult("register", True, latency, 200))
                        return AgentContext(data["agent"]["agent_id"], data["api_key"])
                    else:
                        body = await resp.text()
                        self.stats["register"].add(TestResult("register", False, latency, resp.status, body[:100]))
                        return None
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            self.stats["register"].add(TestResult("register", False, latency, 0, str(e)[:100]))
            return None
    
    async def send_intent(self, session: aiohttp.ClientSession, agent: AgentContext) -> TestResult:
        """发送 Intent"""
        result = await self._request(session, "POST", f"{API_BASE}/intents", {
            "agent_id": agent.agent_id,
            "intent_type": random.choice(["long", "short"]),
            "asset": random.choice(ASSETS),
            "size_usdc": random.randint(10, 500),
            "leverage": random.randint(1, 10),
            "reason": "Stress test",
        }, {"X-API-Key": agent.api_key})
        self.stats["intent"].add(result)
        return result
    
    async def read_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> TestResult:
        """读取端点"""
        result = await self._request(session, "GET", f"{API_BASE}{endpoint}")
        self.stats["read"].add(result)
        return result
    
    async def ws_test(self, duration: int = 10):
        """WebSocket 测试"""
        start = time.perf_counter()
        messages = 0
        try:
            timeout = aiohttp.ClientTimeout(total=duration + 5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.ws_connect(WS_URL) as ws:
                    await ws.send_json({"type": "ping"})
                    while (time.perf_counter() - start) < duration:
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2)
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                messages += 1
                                self.ws_messages += 1
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                        except asyncio.TimeoutError:
                            await ws.send_json({"type": "ping"})
                    
                    latency = (time.perf_counter() - start) * 1000
                    self.stats["ws"].add(TestResult("ws", True, latency, 200))
                    return True
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            self.stats["ws"].add(TestResult("ws", False, latency, 0, str(e)[:100]))
            return False
    
    async def run(self):
        print(f"""
╔══════════════════════════════════════════════════════════╗
║     AI PERP DEX - CONSERVATIVE STRESS TEST               ║
║     {NUM_AGENTS} agents × {INTENTS_PER_AGENT} intents, max {MAX_CONCURRENT} concurrent        ║
╚══════════════════════════════════════════════════════════╝
""")
        
        test_start = time.perf_counter()
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Phase 1: Register agents (sequential batches)
            print(f"Phase 1: Registering {NUM_AGENTS} agents...")
            for i in range(NUM_AGENTS):
                agent = await self.register_agent(session, i)
                if agent:
                    self.agents.append(agent)
                if (i + 1) % 5 == 0:
                    print(f"  {i+1}/{NUM_AGENTS} registered")
                    await asyncio.sleep(DELAY_BETWEEN_BATCHES)
            
            print(f"✓ {len(self.agents)}/{NUM_AGENTS} agents registered")
            print(f"  {json.dumps(self.stats['register'].summary())}")
            
            # Phase 2: Send intents (controlled concurrency)
            print(f"\nPhase 2: Sending {len(self.agents) * INTENTS_PER_AGENT} intents...")
            intent_count = 0
            for agent in self.agents:
                for _ in range(INTENTS_PER_AGENT):
                    await self.send_intent(session, agent)
                    intent_count += 1
                    if intent_count % 20 == 0:
                        print(f"  {intent_count}/{len(self.agents) * INTENTS_PER_AGENT} sent")
                        await asyncio.sleep(0.1)  # 小延迟
            
            print(f"✓ Intents complete")
            print(f"  {json.dumps(self.stats['intent'].summary())}")
            
            # Phase 3: Read endpoints
            print(f"\nPhase 3: Testing read endpoints...")
            endpoints = ["/stats", "/prices", "/agents", "/intents?limit=10", "/leaderboard"]
            for ep in endpoints:
                for _ in range(10):
                    await self.read_endpoint(session, ep)
            
            print(f"✓ Read test complete")
            print(f"  {json.dumps(self.stats['read'].summary())}")
        
        # Phase 4: WebSocket (outside session)
        print(f"\nPhase 4: Testing WebSocket...")
        ws_tasks = [self.ws_test(10) for _ in range(3)]
        ws_results = await asyncio.gather(*ws_tasks)
        print(f"✓ WebSocket: {sum(ws_results)}/3 connections successful, {self.ws_messages} messages")
        
        # Phase 5: Burst test
        print(f"\nPhase 5: Rate limit burst test...")
        if self.agents:
            agent = self.agents[0]
            burst_stats = TestStats()
            async with aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(limit=20)) as session:
                tasks = []
                for i in range(15):
                    async def burst_intent():
                        result = await self._request(session, "POST", f"{API_BASE}/intents", {
                            "agent_id": agent.agent_id,
                            "intent_type": "long",
                            "asset": "ETH-PERP",
                            "size_usdc": 100,
                            "leverage": 1,
                        }, {"X-API-Key": agent.api_key})
                        burst_stats.add(result)
                    tasks.append(burst_intent())
                await asyncio.gather(*tasks)
            
            print(f"✓ Burst: {burst_stats.success}/15 success, {burst_stats.rate_limited} rate limited")
        
        # Final Report
        test_duration = time.perf_counter() - test_start
        total_requests = sum(s.total for s in self.stats.values())
        
        print(f"""
{'='*60}
              FINAL REPORT
{'='*60}
Duration: {test_duration:.1f}s
Total Requests: {total_requests}
Throughput: {total_requests/test_duration:.1f} req/s

📝 REGISTRATION
   {json.dumps(self.stats['register'].summary(), indent=4)}

📊 INTENTS
   {json.dumps(self.stats['intent'].summary(), indent=4)}

📖 READ ENDPOINTS
   {json.dumps(self.stats['read'].summary(), indent=4)}

🔌 WEBSOCKET
   Connections: {self.stats['ws'].total}
   Success: {self.stats['ws'].success}
   Messages: {self.ws_messages}
{'='*60}
""")


async def main():
    # Health check
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            async with s.get(f"{API_BASE}/health") as r:
                if r.status != 200:
                    print(f"Server unhealthy: {r.status}")
                    return
    except Exception as e:
        print(f"Cannot connect: {e}")
        return
    
    print("✓ Server healthy\n")
    await ConservativeStressTest().run()


if __name__ == "__main__":
    asyncio.run(main())
