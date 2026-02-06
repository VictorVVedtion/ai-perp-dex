
import re
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel

class ParsedIntent(BaseModel):
    action: str
    market: Optional[str] = None
    size: Optional[float] = None
    leverage: Optional[int] = None
    price: Optional[float] = None
    confidence: float = 1.0  # Regex is certain, LLM might not be
    raw_command: str

class IntentParser:
    """
    Parses natural language commands into structured intents.
    Currently uses Regex, but designed to be swapped/augmented with LLM.
    """

    def parse(self, text: str) -> ParsedIntent:
        text = text.lower().strip()
        raw_command = text # Keep original for reference if needed, but we use lowercased for processing

        # Defaults
        market = None
        size = None
        leverage = None
        price = None
        action = "unknown"

        # 1. Market detection
        # Matches: btc, eth, sol, bitcoin, ethereum, solana
        market_match = re.search(r'\b(btc|eth|sol|bitcoin|ethereum|solana)\b', text)
        if market_match:
            symbol = market_match.group(1)
            # Normalize
            symbol_map = {
                'bitcoin': 'BTC',
                'ethereum': 'ETH',
                'solana': 'SOL',
                'btc': 'BTC',
                'eth': 'ETH',
                'sol': 'SOL'
            }
            market = f"{symbol_map[symbol]}-PERP"

        # 2. Size detection
        # Matches: $100, 100刀, 100美元, 100 usdc, 100 u
        # Group 1: $100 -> 100
        # Group 2: 100 -> 100 (followed by unit)
        size_match = re.search(r'\$(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:刀|美元|usdc|u)', text)
        if size_match:
            size_str = size_match.group(1) or size_match.group(2)
            try:
                size = float(size_str)
            except ValueError:
                pass

        # 3. Leverage detection
        # Matches: 5倍, 5x, 5倍杠杆
        leverage_match = re.search(r'(\d+)\s*(?:倍|x|倍杠杆)', text)
        if leverage_match:
            try:
                leverage = int(leverage_match.group(1))
            except ValueError:
                pass

        # 4. Price detection (for alerts)
        # Matches: 跌破 90, 涨到 100
        price_match = re.search(r'(?:跌破|涨到|到达|突破)\s*(\d+(?:\.\d+)?)', text)
        if price_match:
            try:
                price = float(price_match.group(1))
            except ValueError:
                pass

        # 5. Action detection
        if re.search(r'帮助|help|\?', text):
            action = 'help'
        
        elif re.search(r'做多|开多|买入|long|buy', text) and not re.search(r'盯|alert|watch', text):
            action = 'long'
            if leverage is None:
                leverage = 5 # Default leverage
        
        elif re.search(r'做空|开空|卖空|short|sell', text):
            action = 'short'
            if leverage is None:
                leverage = 5 # Default leverage
        
        elif re.search(r'平掉|关闭|平仓|close', text):
            action = 'close'
        
        elif re.search(r'持仓|仓位|position|显示|查看', text) and not market:
            action = 'positions'
            
        elif re.search(r'盯|watch|alert|提醒|通知', text):
            action = 'alert'

        return ParsedIntent(
            action=action,
            market=market,
            size=size,
            leverage=leverage,
            price=price,
            raw_command=text
        )

# Global instance
intent_parser = IntentParser()
