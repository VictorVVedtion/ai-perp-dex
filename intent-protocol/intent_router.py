#!/usr/bin/env python3
"""
Financial Intent Router
路由意图到正确的执行场所
"""

import asyncio
import aiohttp
from dataclasses import dataclass
from typing import Optional, Dict, Any
from intent_parser import IntentParser, ParsedIntent, IntentType, SettlementRoute

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    route_used: str
    tx_signature: Optional[str] = None
    details: Dict[str, Any] = None
    error: Optional[str] = None

class IntentRouter:
    """意图路由器"""
    
    def __init__(
        self,
        settlement_url: str = "http://localhost:8081",
        trade_router_url: str = "http://localhost:3000",
    ):
        self.parser = IntentParser()
        self.settlement_url = settlement_url
        self.trade_router_url = trade_router_url
        
    async def process_intent(
        self, 
        intent: str | dict, 
        agent_id: str,
        counterparty: Optional[str] = None,
    ) -> ExecutionResult:
        """处理意图：解析 → 路由 → 执行"""
        
        # 1. 解析意图
        parsed = self.parser.parse(intent, agent_id)
        parsed.counterparty = counterparty
        
        print(f"📝 解析意图: {parsed.type.value} → {parsed.route.value}")
        
        # 2. 路由执行
        if parsed.route == SettlementRoute.AI_PERP_DEX:
            return await self._route_to_perp_dex(parsed)
        elif parsed.route == SettlementRoute.P2P_ESCROW:
            return await self._route_to_escrow(parsed)
        elif parsed.route == SettlementRoute.ORACLE_SETTLE:
            return await self._route_to_oracle(parsed)
        elif parsed.route == SettlementRoute.REVENUE_SHARE:
            return await self._route_to_revenue_share(parsed)
        elif parsed.route == SettlementRoute.ATOMIC_SWAP:
            return await self._route_to_atomic_swap(parsed)
        elif parsed.route == SettlementRoute.EXTERNAL_DEX:
            return await self._route_to_external(parsed)
        else:
            return ExecutionResult(
                success=False,
                route_used="none",
                error=f"Unknown route: {parsed.route}",
            )
    
    async def _route_to_perp_dex(self, intent: ParsedIntent) -> ExecutionResult:
        """路由到 AI Perp DEX"""
        
        params = intent.params
        action = params.get("action", "long")
        asset = params.get("asset", "BTC-PERP")
        size = params.get("size_usdc", 100)
        leverage = params.get("leverage", 1)
        
        # 计算链上参数
        # 假设 BTC 价格 $72,000
        btc_price = 72000
        position_size = int(size * leverage / btc_price * 1_000_000)  # 合约精度
        entry_price = int(btc_price * 1_000_000)  # 6 decimals
        
        if action == "short":
            position_size = -position_size
        
        market_index = {"BTC-PERP": 0, "ETH-PERP": 1, "SOL-PERP": 2}.get(asset, 0)
        
        # 调用 Settlement Service
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.settlement_url}/settle/open",
                    json={
                        "owner": intent.agent_id,
                        "market_index": market_index,
                        "size": position_size,
                        "entry_price": entry_price,
                    }
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("success"):
                        return ExecutionResult(
                            success=True,
                            route_used="ai_perp_dex",
                            tx_signature=result.get("signature"),
                            details={
                                "action": action,
                                "asset": asset,
                                "size": size,
                                "leverage": leverage,
                                "entry_price": btc_price,
                            }
                        )
                    else:
                        return ExecutionResult(
                            success=False,
                            route_used="ai_perp_dex",
                            error=result.get("error", "Unknown error"),
                        )
        except Exception as e:
            return ExecutionResult(
                success=False,
                route_used="ai_perp_dex",
                error=str(e),
            )
    
    async def _route_to_escrow(self, intent: ParsedIntent) -> ExecutionResult:
        """路由到 P2P Escrow (服务类)"""
        
        # TODO: 实现 Escrow 合约调用
        # 目前返回模拟结果
        
        return ExecutionResult(
            success=True,
            route_used="p2p_escrow",
            details={
                "type": "service",
                "description": intent.params.get("description", ""),
                "status": "escrow_created",
                "note": "P2P Escrow 待实现",
            }
        )
    
    async def _route_to_oracle(self, intent: ParsedIntent) -> ExecutionResult:
        """路由到 Oracle Settlement (信号类)"""
        
        # TODO: 实现 Oracle 预言机结算
        
        return ExecutionResult(
            success=True,
            route_used="oracle_settle",
            details={
                "type": "signal",
                "prediction": intent.params.get("prediction", ""),
                "status": "signal_registered",
                "note": "Oracle Settlement 待实现",
            }
        )
    
    async def _route_to_revenue_share(self, intent: ParsedIntent) -> ExecutionResult:
        """路由到收益分成合约 (协作类)"""
        
        # TODO: 实现收益分成合约
        
        return ExecutionResult(
            success=True,
            route_used="revenue_share",
            details={
                "type": "collab",
                "proposal": intent.params.get("proposal", ""),
                "status": "contract_created",
                "note": "Revenue Share 待实现",
            }
        )
    
    async def _route_to_atomic_swap(self, intent: ParsedIntent) -> ExecutionResult:
        """路由到原子交换 (P2P 兑换)"""
        
        # TODO: 实现原子交换
        
        return ExecutionResult(
            success=True,
            route_used="atomic_swap",
            details={
                "type": "swap",
                "swap": intent.params.get("swap", ""),
                "status": "swap_pending",
                "note": "Atomic Swap 待实现",
            }
        )
    
    async def _route_to_external(self, intent: ParsedIntent) -> ExecutionResult:
        """路由到外部 DEX (大额)"""
        
        # TODO: 实现外部 DEX 集成 (dYdX, Hyperliquid)
        
        return ExecutionResult(
            success=True,
            route_used="external_dex",
            details={
                "type": "trade",
                "note": "External DEX 待实现，大额交易",
            }
        )


async def main():
    """测试 Intent Router"""
    
    print("🚀 Intent Router 测试")
    print("=" * 60)
    
    router = IntentRouter()
    
    # 测试用例
    test_cases = [
        ("long BTC 10x 100 USDC", "7kuz1ACEgmwL82Zs7NqCt9jxYxfZq1avM3ZEC67ijsQz"),
        ("帮你设计 tokenomics，收费 100 MOLT", "agent_cindy"),
        ("预测 ETH 24h 涨 5%", "agent_signal"),
        ("你出 Alpha 我出执行，分成 60/40", "agent_collab"),
    ]
    
    for intent, agent_id in test_cases:
        print(f"\n输入: {intent}")
        print(f"Agent: {agent_id}")
        
        result = await router.process_intent(intent, agent_id)
        
        print(f"成功: {result.success}")
        print(f"路由: {result.route_used}")
        if result.tx_signature:
            print(f"签名: {result.tx_signature[:30]}...")
        if result.details:
            print(f"详情: {result.details}")
        if result.error:
            print(f"错误: {result.error}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
