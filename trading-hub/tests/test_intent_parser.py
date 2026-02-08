
import pytest
import sys
from pathlib import Path

# Ensure tests work regardless of how pytest is invoked.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.intent_parser import intent_parser

def test_market_parsing():
    # ETH
    res = intent_parser.parse("Buy ETH $100")
    assert res.market == "ETH-PERP"
    assert res.action == "long"
    
    # BTC
    res = intent_parser.parse("Short Bitcoin 5x")
    assert res.market == "BTC-PERP"
    assert res.action == "short"

    # SOL
    res = intent_parser.parse("Long SOLANA")
    assert res.market == "SOL-PERP"

def test_size_parsing():
    # $ format
    res = intent_parser.parse("Buy ETH $100.50")
    assert res.size == 100.50

    # 'usdc' format
    res = intent_parser.parse("Buy ETH 500 usdc")
    assert res.size == 500.0

    # 'u' format
    res = intent_parser.parse("Buy ETH 1000u")
    assert res.size == 1000.0

def test_leverage_parsing():
    res = intent_parser.parse("Buy ETH $100 10x")
    assert res.leverage == 10

    res = intent_parser.parse("Buy ETH $100 5倍")
    assert res.leverage == 5

    # Default logic (service defaults to 5 if action is long/short but no leverage specified in text)
    # Note: original frontend code had `leverage: leverage || 5`. The python code implements this.
    res = intent_parser.parse("Buy ETH $100")
    assert res.leverage == 5

def test_actions():
    assert intent_parser.parse("help").action == "help"
    assert intent_parser.parse("close position").action == "close"
    assert intent_parser.parse("my positions").action == "positions"
    assert intent_parser.parse("alert if price below 100").action == "alert"

def test_complex_chinese_command():
    # "做多 ETH 100刀 20倍"
    res = intent_parser.parse("做多 ETH 100刀 20倍")
    assert res.action == "long"
    assert res.market == "ETH-PERP"
    assert res.size == 100.0
    assert res.leverage == 20
