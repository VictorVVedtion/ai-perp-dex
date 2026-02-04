#!/usr/bin/env python3
"""
Financial Intent Parser
解析 Agent 的金融意图
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import json
import re

class IntentType(Enum):
    TRADE = "trade"          # 交易类: long/short
    SERVICE = "service"      # 服务类: 咨询、开发
    SIGNAL = "signal"        # 信号类: 预测、押注
    COLLAB = "collab"        # 协作类: 分成、合作
    SWAP = "swap"            # 兑换类: P2P atomic swap
    UNKNOWN = "unknown"

class SettlementRoute(Enum):
    AI_PERP_DEX = "ai_perp_dex"      # 我们的永续 DEX
    P2P_ESCROW = "p2p_escrow"         # P2P 托管
    ORACLE_SETTLE = "oracle_settle"   # Oracle 验证结算
    REVENUE_SHARE = "revenue_share"   # 收益分成合约
    EXTERNAL_DEX = "external_dex"     # 外部 DEX (dYdX, HL)
    ATOMIC_SWAP = "atomic_swap"       # 原子交换

@dataclass
class ParsedIntent:
    """解析后的意图"""
    type: IntentType
    route: SettlementRoute
    agent_id: str
    raw_intent: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    counterparty: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "route": self.route.value,
            "agent_id": self.agent_id,
            "params": self.params,
            "confidence": self.confidence,
            "counterparty": self.counterparty,
        }

class IntentParser:
    """意图解析器"""
    
    # 交易关键词
    TRADE_KEYWORDS = {
        "long": ("long", 1),
        "做多": ("long", 1),
        "buy": ("long", 1),
        "short": ("short", -1),
        "做空": ("short", -1),
        "sell": ("short", -1),
    }
    
    # 资产映射
    ASSETS = {
        "btc": "BTC-PERP",
        "bitcoin": "BTC-PERP",
        "eth": "ETH-PERP",
        "ethereum": "ETH-PERP",
        "sol": "SOL-PERP",
        "solana": "SOL-PERP",
    }
    
    def parse(self, intent: str | dict, agent_id: str = "unknown") -> ParsedIntent:
        """解析意图"""
        
        # 如果是 JSON 结构化输入
        if isinstance(intent, dict):
            return self._parse_structured(intent, agent_id)
        
        # 自然语言解析
        return self._parse_natural(intent, agent_id)
    
    def _parse_structured(self, intent: dict, agent_id: str) -> ParsedIntent:
        """解析结构化意图 (JSON)"""
        
        intent_type = IntentType(intent.get("type", "unknown"))
        
        # 根据类型确定路由
        route = self._determine_route(intent_type, intent)
        
        return ParsedIntent(
            type=intent_type,
            route=route,
            agent_id=agent_id,
            raw_intent=json.dumps(intent),
            params=intent,
            confidence=1.0,
        )
    
    def _parse_natural(self, text: str, agent_id: str) -> ParsedIntent:
        """解析自然语言意图"""
        
        text_lower = text.lower()
        
        # 1. 检查是否是交易意图
        trade_intent = self._detect_trade(text_lower)
        if trade_intent:
            return ParsedIntent(
                type=IntentType.TRADE,
                route=SettlementRoute.AI_PERP_DEX,
                agent_id=agent_id,
                raw_intent=text,
                params=trade_intent,
                confidence=0.8,
            )
        
        # 2. 检查是否是服务意图
        if any(kw in text_lower for kw in ["帮你", "help you", "design", "设计", "报价", "收费"]):
            return ParsedIntent(
                type=IntentType.SERVICE,
                route=SettlementRoute.P2P_ESCROW,
                agent_id=agent_id,
                raw_intent=text,
                params={"description": text},
                confidence=0.6,
            )
        
        # 3. 检查是否是信号/预测意图
        if any(kw in text_lower for kw in ["预测", "predict", "涨", "跌", "信心", "confidence"]):
            return ParsedIntent(
                type=IntentType.SIGNAL,
                route=SettlementRoute.ORACLE_SETTLE,
                agent_id=agent_id,
                raw_intent=text,
                params={"prediction": text},
                confidence=0.6,
            )
        
        # 4. 检查是否是协作意图
        if any(kw in text_lower for kw in ["分成", "split", "合作", "collab", "一起"]):
            return ParsedIntent(
                type=IntentType.COLLAB,
                route=SettlementRoute.REVENUE_SHARE,
                agent_id=agent_id,
                raw_intent=text,
                params={"proposal": text},
                confidence=0.6,
            )
        
        # 5. 检查是否是兑换意图
        if any(kw in text_lower for kw in ["swap", "兑换", "换成", "exchange"]):
            return ParsedIntent(
                type=IntentType.SWAP,
                route=SettlementRoute.ATOMIC_SWAP,
                agent_id=agent_id,
                raw_intent=text,
                params={"swap": text},
                confidence=0.6,
            )
        
        # 无法识别
        return ParsedIntent(
            type=IntentType.UNKNOWN,
            route=SettlementRoute.P2P_ESCROW,
            agent_id=agent_id,
            raw_intent=text,
            params={},
            confidence=0.3,
        )
    
    def _detect_trade(self, text: str) -> Optional[dict]:
        """检测交易意图"""
        
        side = None
        direction = 0
        
        # 检测方向
        for keyword, (side_name, dir_val) in self.TRADE_KEYWORDS.items():
            if keyword in text:
                side = side_name
                direction = dir_val
                break
        
        if not side:
            return None
        
        # 检测资产
        asset = None
        for keyword, asset_name in self.ASSETS.items():
            if keyword in text:
                asset = asset_name
                break
        
        if not asset:
            return None
        
        # 检测杠杆
        leverage = 1
        leverage_match = re.search(r'(\d+)x|杠杆(\d+)|leverage\s*(\d+)', text)
        if leverage_match:
            leverage = int(leverage_match.group(1) or leverage_match.group(2) or leverage_match.group(3))
        
        # 检测金额
        size = 100  # 默认
        size_match = re.search(r'(\d+)\s*(usdc|usd|u|\$)', text)
        if size_match:
            size = int(size_match.group(1))
        
        return {
            "action": side,
            "asset": asset,
            "leverage": leverage,
            "size_usdc": size,
        }
    
    def _determine_route(self, intent_type: IntentType, params: dict) -> SettlementRoute:
        """确定结算路由"""
        
        routing = {
            IntentType.TRADE: SettlementRoute.AI_PERP_DEX,
            IntentType.SERVICE: SettlementRoute.P2P_ESCROW,
            IntentType.SIGNAL: SettlementRoute.ORACLE_SETTLE,
            IntentType.COLLAB: SettlementRoute.REVENUE_SHARE,
            IntentType.SWAP: SettlementRoute.ATOMIC_SWAP,
            IntentType.UNKNOWN: SettlementRoute.P2P_ESCROW,
        }
        
        route = routing.get(intent_type, SettlementRoute.P2P_ESCROW)
        
        # 大额交易可能路由到外部 DEX
        if intent_type == IntentType.TRADE:
            size = params.get("size_usdc", 0) or params.get("size", 0)
            if size > 100000:  # > 100k 路由到外部
                route = SettlementRoute.EXTERNAL_DEX
        
        return route


# 测试
if __name__ == "__main__":
    parser = IntentParser()
    
    test_intents = [
        "long BTC 10x 1000 USDC",
        "做空 ETH 杠杆5",
        "帮你设计 tokenomics，收费 100 MOLT",
        "预测 ETH 24h 内涨 5%，信心 80%",
        "你出 Alpha 我出执行，分成 60/40",
        "swap 1000 USDC for MOLT",
        {"type": "trade", "action": "long", "asset": "BTC-PERP", "size_usdc": 1000, "leverage": 10},
    ]
    
    print("🧪 Intent Parser 测试")
    print("=" * 60)
    
    for intent in test_intents:
        result = parser.parse(intent, "test_agent")
        print(f"\n输入: {intent}")
        print(f"类型: {result.type.value}")
        print(f"路由: {result.route.value}")
        print(f"参数: {result.params}")
        print(f"置信度: {result.confidence}")
