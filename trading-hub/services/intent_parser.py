
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
        # Matches all 12 supported assets + common aliases
        market_match = re.search(
            r'\b(btc|eth|sol|doge|pepe|wif|arb|op|sui|avax|link|aave|'
            r'bitcoin|ethereum|solana|dogecoin|arbitrum|optimism|avalanche|chainlink)\b',
            text
        )
        if market_match:
            symbol = market_match.group(1)
            # Normalize to ticker
            symbol_map = {
                'bitcoin': 'BTC', 'btc': 'BTC',
                'ethereum': 'ETH', 'eth': 'ETH',
                'solana': 'SOL', 'sol': 'SOL',
                'dogecoin': 'DOGE', 'doge': 'DOGE',
                'pepe': 'PEPE',
                'wif': 'WIF',
                'arbitrum': 'ARB', 'arb': 'ARB',
                'optimism': 'OP', 'op': 'OP',
                'sui': 'SUI',
                'avalanche': 'AVAX', 'avax': 'AVAX',
                'chainlink': 'LINK', 'link': 'LINK',
                'aave': 'AAVE',
            }
            market = f"{symbol_map[symbol]}-PERP"

        # 2. Size detection
        # Matches: $100, 100刀, 100美元, 100 usdc, 100 u, 100 dollars, 50 bucks
        # Also matches bare numbers when context is clear (e.g. "sell DOGE 50 at 3x")
        # Group 1: $100 -> 100
        # Group 2: 100 -> 100 (followed by unit)
        size_match = re.search(r'\$(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:刀|美元|usdc|usd|u|dollars?|bucks?)\b', text)
        if not size_match:
            # Fallback: bare number in trading context (e.g. "sell DOGE 50 at 3x")
            size_match = re.search(r'(?:long|short|buy|sell|做多|做空|买入|卖空)\s+\w+[\s-]*(?:perp\s+)?(\d+(?:\.\d+)?)\b', text)
            if size_match:
                try:
                    size = float(size_match.group(1))
                except ValueError:
                    pass
        else:
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
        # Matches: 跌破 90, 涨到 100, drops to 60000, reaches 100000
        price_match = re.search(r'(?:跌破|涨到|到达|突破|drops?\s*to|reaches?|hits?|below|above)\s*\$?(\d+(?:\.\d+)?)', text)
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
