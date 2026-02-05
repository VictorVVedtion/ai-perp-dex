"""
AI Perp DEX SDK - Standalone Package

可直接复制此文件使用，无需安装依赖
"""

import asyncio
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import re


@dataclass
class TradeResult:
    success: bool
    intent_id: Optional[str] = None
    position_id: Optional[str] = None
    message: str = ""
    data: dict = None


class AIperpDEX:
    """
    AI Perp DEX SDK
    
    用法:
        dex = AIperpDEX("https://api.ai-perp-dex.com", api_key="your_key")
        
        # 自然语言交易
        result = dex.trade("long ETH $100 5x")
        
        # 查看持仓
        positions = dex.positions()
        
        # 回测
        bt = dex.backtest("momentum", "ETH", 30)
    """
    
    def __init__(self, base_url: str, api_key: str = None, agent_name: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.agent_name = agent_name or "Agent"
        self.agent_id = None
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """同步 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.agent_id:
            headers["X-Agent-ID"] = self.agent_id
        
        body = json.dumps(data).encode() if data else None
        
        req = Request(url, data=body, headers=headers, method=method)
        
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            return {"error": error_body, "status": e.code}
    
    def _ensure_agent(self):
        """确保 Agent 已注册"""
        if self.agent_id:
            return
        
        # 尝试查找已有 agent
        resp = self._request("GET", "/agents")
        if "agents" in resp:
            for agent in resp["agents"]:
                if agent.get("display_name") == self.agent_name:
                    self.agent_id = agent["agent_id"]
                    return
        
        # 注册新 agent
        resp = self._request("POST", "/agents/register", {
            "wallet_address": f"0x{hash(self.agent_name) & 0xFFFFFFFF:08x}",
            "display_name": self.agent_name,
        })
        if "agent" in resp:
            self.agent_id = resp["agent"]["agent_id"]
    
    # ==========================================
    # 交易 API
    # ==========================================
    
    def trade(self, instruction: str) -> TradeResult:
        """
        自然语言交易
        
        支持:
        - "long ETH $100 5x"
        - "short BTC $200"
        - "做多 ETH 100刀 10倍"
        """
        parsed = self._parse_instruction(instruction)
        if not parsed:
            return TradeResult(success=False, message=f"Cannot parse: {instruction}")
        
        self._ensure_agent()
        
        resp = self._request("POST", "/intents", {
            "agent_id": self.agent_id,
            "intent_type": parsed["direction"],
            "asset": parsed["asset"],
            "size_usdc": parsed["size"],
            "leverage": parsed.get("leverage", 1),
        })
        
        if resp.get("success"):
            return TradeResult(
                success=True,
                intent_id=resp.get("intent", {}).get("intent_id"),
                position_id=resp.get("position", {}).get("position_id"),
                message=f"✅ {parsed['direction'].upper()} {parsed['asset']} ${parsed['size']}",
                data=resp,
            )
        else:
            return TradeResult(success=False, message=resp.get("error", "Failed"), data=resp)
    
    def _parse_instruction(self, text: str) -> Optional[dict]:
        """解析自然语言指令"""
        text = text.lower()
        
        # 方向
        direction = None
        if any(w in text for w in ["long", "做多", "buy", "买"]):
            direction = "long"
        elif any(w in text for w in ["short", "做空", "sell", "卖"]):
            direction = "short"
        if not direction:
            return None
        
        # 资产
        asset = None
        for a in ["btc", "eth", "sol"]:
            if a in text:
                asset = f"{a.upper()}-PERP"
                break
        if not asset:
            return None
        
        # 金额
        size = 100
        match = re.search(r'\$?(\d+(?:\.\d+)?)', text)
        if match:
            size = float(match.group(1))
        
        # 杠杆
        leverage = 1
        lev_match = re.search(r'(\d+)\s*(?:x|倍)', text)
        if lev_match:
            leverage = int(lev_match.group(1))
        
        return {"direction": direction, "asset": asset, "size": size, "leverage": leverage}
    
    def long(self, asset: str, size: float, leverage: int = 1) -> TradeResult:
        """做多"""
        return self.trade(f"long {asset} ${size} {leverage}x")
    
    def short(self, asset: str, size: float, leverage: int = 1) -> TradeResult:
        """做空"""
        return self.trade(f"short {asset} ${size} {leverage}x")
    
    # ==========================================
    # 持仓 API
    # ==========================================
    
    def positions(self) -> List[dict]:
        """查看持仓"""
        self._ensure_agent()
        resp = self._request("GET", f"/positions/{self.agent_id}")
        return resp.get("positions", [])
    
    def portfolio(self) -> dict:
        """投资组合"""
        self._ensure_agent()
        return self._request("GET", f"/portfolio/{self.agent_id}")
    
    def close_position(self, position_id: str) -> dict:
        """平仓"""
        return self._request("POST", f"/positions/{position_id}/close")
    
    # ==========================================
    # 账户 API
    # ==========================================
    
    def balance(self) -> dict:
        """余额"""
        self._ensure_agent()
        return self._request("GET", f"/balance/{self.agent_id}")
    
    def deposit(self, amount: float) -> dict:
        """入金"""
        self._ensure_agent()
        return self._request("POST", "/deposit", {"agent_id": self.agent_id, "amount": amount})
    
    def withdraw(self, amount: float) -> dict:
        """出金"""
        self._ensure_agent()
        return self._request("POST", "/withdraw", {"agent_id": self.agent_id, "amount": amount})
    
    # ==========================================
    # 回测 API
    # ==========================================
    
    def backtest(self, strategy: str, asset: str = "ETH", days: int = 30) -> dict:
        """策略回测"""
        return self._request("POST", "/backtest", {
            "strategy": strategy,
            "asset": asset,
            "days": days,
            "use_real_data": True,
        })
    
    # ==========================================
    # 信号 API
    # ==========================================
    
    def create_signal(self, asset: str, direction: str, target: float, stake: float = 50) -> dict:
        """创建信号"""
        self._ensure_agent()
        return self._request("POST", "/signals", {
            "agent_id": self.agent_id,
            "asset": asset,
            "signal_type": f"price_{'above' if direction == 'long' else 'below'}",
            "target_value": target,
            "stake_amount": stake,
        })
    
    def fade_signal(self, signal_id: str) -> dict:
        """Fade 信号"""
        self._ensure_agent()
        return self._request("POST", "/signals/fade", {
            "signal_id": signal_id,
            "fader_id": self.agent_id,
        })
    
    def open_signals(self) -> List[dict]:
        """查看开放信号"""
        resp = self._request("GET", "/signals/open")
        return resp.get("signals", [])
    
    # ==========================================
    # 价格 API
    # ==========================================
    
    def prices(self) -> dict:
        """获取价格"""
        resp = self._request("GET", "/prices")
        return resp.get("prices", resp)


# 便捷函数
def connect(url: str = "http://localhost:8082", api_key: str = None) -> AIperpDEX:
    """快速连接"""
    return AIperpDEX(url, api_key)


# 使用示例
if __name__ == "__main__":
    dex = connect()
    
    print("🔗 连接 AI Perp DEX")
    print(f"💰 价格: {dex.prices()}")
    
    result = dex.trade("long ETH $50 5x")
    print(f"📈 交易: {result.message}")
    
    print(f"📊 持仓: {len(dex.positions())} 个")
