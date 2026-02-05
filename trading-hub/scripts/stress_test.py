"""
AI Perp DEX 压力测试 - 100 个 Agent 并发交易
"""

import asyncio
import aiohttp
import random
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List

BASE_URL = "http://localhost:8082"

# Agent 名字生成
PREFIXES = ["Alpha", "Beta", "Gamma", "Delta", "Omega", "Sigma", "Theta", "Zeta", "Nova", "Quantum"]
SUFFIXES = ["Trader", "Bot", "Agent", "AI", "Algo", "Quant", "Hedge", "Arb", "Whale", "Degen"]

@dataclass
class TestResult:
    agent_id: str
    action: str
    success: bool
    latency_ms: float
    error: str = None

class StressTest:
    def __init__(self, num_agents: int = 100):
        self.num_agents = num_agents
        self.agents = []
        self.results: List[TestResult] = []
        self.session = None
    
    async def setup(self):
        """初始化"""
        self.session = aiohttp.ClientSession()
        
        # Seed 数据
        await self.session.post(f"{BASE_URL}/demo/seed")
        print(f"🚀 准备 {self.num_agents} 个 Agent...")
    
    async def cleanup(self):
        """清理"""
        if self.session:
            await self.session.close()
    
    async def register_agent(self, index: int) -> str:
        """注册单个 Agent"""
        name = f"{random.choice(PREFIXES)}{random.choice(SUFFIXES)}_{index:03d}"
        wallet = f"0x{random.randint(0, 0xFFFFFFFF):08x}{index:04x}"
        
        start = time.time()
        try:
            async with self.session.post(
                f"{BASE_URL}/agents/register",
                json={"wallet_address": wallet, "display_name": name}
            ) as resp:
                data = await resp.json()
                latency = (time.time() - start) * 1000
                
                if data.get("success"):
                    agent_id = data["agent"]["agent_id"]
                    self.agents.append(agent_id)
                    self.results.append(TestResult(agent_id, "register", True, latency))
                    return agent_id
                else:
                    self.results.append(TestResult(name, "register", False, latency, str(data)))
                    return None
        except Exception as e:
            self.results.append(TestResult(name, "register", False, 0, str(e)))
            return None
    
    async def random_trade(self, agent_id: str):
        """随机交易"""
        asset = random.choice(["BTC-PERP", "ETH-PERP", "SOL-PERP"])
        side = random.choice(["long", "short"])
        size = random.randint(10, 200)
        leverage = random.randint(1, 20)
        
        start = time.time()
        try:
            async with self.session.post(
                f"{BASE_URL}/intents",
                json={
                    "agent_id": agent_id,
                    "intent_type": side,
                    "asset": asset,
                    "size_usdc": size,
                    "leverage": leverage,
                }
            ) as resp:
                data = await resp.json()
                latency = (time.time() - start) * 1000
                
                success = data.get("success", False)
                self.results.append(TestResult(agent_id, f"trade_{side}", success, latency))
                return success
        except Exception as e:
            self.results.append(TestResult(agent_id, "trade", False, 0, str(e)))
            return False
    
    async def random_signal(self, agent_id: str):
        """随机创建信号"""
        asset = random.choice(["BTC-PERP", "ETH-PERP", "SOL-PERP"])
        signal_type = random.choice(["price_above", "price_below"])
        target = random.randint(1000, 100000)
        stake = random.randint(10, 100)
        
        start = time.time()
        try:
            async with self.session.post(
                f"{BASE_URL}/signals",
                json={
                    "agent_id": agent_id,
                    "asset": asset,
                    "signal_type": signal_type,
                    "target_value": target,
                    "stake_amount": stake,
                }
            ) as resp:
                data = await resp.json()
                latency = (time.time() - start) * 1000
                
                success = data.get("success", False)
                self.results.append(TestResult(agent_id, "signal", success, latency))
                return success
        except Exception as e:
            self.results.append(TestResult(agent_id, "signal", False, 0, str(e)))
            return False
    
    async def random_transfer(self, from_agent: str, to_agent: str):
        """随机转账"""
        amount = random.randint(1, 50)
        
        start = time.time()
        try:
            async with self.session.post(
                f"{BASE_URL}/transfer",
                json={
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "amount": amount,
                }
            ) as resp:
                data = await resp.json()
                latency = (time.time() - start) * 1000
                
                success = "settlement" in data
                self.results.append(TestResult(from_agent, "transfer", success, latency))
                return success
        except Exception as e:
            self.results.append(TestResult(from_agent, "transfer", False, 0, str(e)))
            return False
    
    async def agent_lifecycle(self, index: int):
        """单个 Agent 的完整生命周期"""
        # 注册
        agent_id = await self.register_agent(index)
        if not agent_id:
            return
        
        # 入金
        await self.session.post(
            f"{BASE_URL}/deposit",
            json={"agent_id": agent_id, "amount": random.randint(100, 1000)}
        )
        
        # 随机操作 3-5 次
        for _ in range(random.randint(3, 5)):
            action = random.choice(["trade", "trade", "signal", "transfer"])
            
            if action == "trade":
                await self.random_trade(agent_id)
            elif action == "signal":
                await self.random_signal(agent_id)
            elif action == "transfer" and len(self.agents) > 1:
                other = random.choice([a for a in self.agents if a != agent_id])
                await self.random_transfer(agent_id, other)
            
            # 随机延迟
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    async def run(self):
        """运行测试"""
        await self.setup()
        
        print(f"⏱️  开始测试 {datetime.now().strftime('%H:%M:%S')}")
        start_time = time.time()
        
        # 批量创建 Agent 和执行操作
        batch_size = 20
        for i in range(0, self.num_agents, batch_size):
            batch = range(i, min(i + batch_size, self.num_agents))
            tasks = [self.agent_lifecycle(j) for j in batch]
            await asyncio.gather(*tasks)
            print(f"   完成 {min(i + batch_size, self.num_agents)}/{self.num_agents} agents...")
        
        total_time = time.time() - start_time
        
        await self.cleanup()
        
        # 统计
        self.print_report(total_time)
    
    def print_report(self, total_time: float):
        """打印报告"""
        print("\n" + "=" * 60)
        print("📊 压力测试报告")
        print("=" * 60)
        
        success = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        print(f"\n⏱️  总耗时: {total_time:.1f}s")
        print(f"👥 Agent 数量: {len(self.agents)}")
        print(f"📝 总操作数: {len(self.results)}")
        print(f"✅ 成功: {len(success)} ({len(success)/len(self.results)*100:.1f}%)")
        print(f"❌ 失败: {len(failed)} ({len(failed)/len(self.results)*100:.1f}%)")
        
        # 延迟统计
        if success:
            latencies = [r.latency_ms for r in success]
            print(f"\n⚡ 延迟统计:")
            print(f"   平均: {sum(latencies)/len(latencies):.1f}ms")
            print(f"   最小: {min(latencies):.1f}ms")
            print(f"   最大: {max(latencies):.1f}ms")
            print(f"   P95: {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms")
        
        # 按类型统计
        print(f"\n📈 按操作类型:")
        action_types = set(r.action for r in self.results)
        for action in sorted(action_types):
            action_results = [r for r in self.results if r.action == action]
            action_success = [r for r in action_results if r.success]
            print(f"   {action}: {len(action_success)}/{len(action_results)} ({len(action_success)/len(action_results)*100:.0f}%)")
        
        # 失败详情
        if failed:
            print(f"\n❌ 失败详情 (前5个):")
            for r in failed[:5]:
                print(f"   {r.agent_id} - {r.action}: {r.error[:50] if r.error else 'unknown'}")
        
        print("\n" + "=" * 60)
        
        # TPS
        tps = len(self.results) / total_time
        print(f"🚀 TPS: {tps:.1f} 操作/秒")
        print("=" * 60)


async def main():
    test = StressTest(num_agents=100)
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
