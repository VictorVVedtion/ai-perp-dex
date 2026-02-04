#!/usr/bin/env python3
"""
Price Fetcher for AI Perp DEX
Fetches real-time prices from CoinGecko
"""

import json
import time
import urllib.request
import urllib.error
from typing import Dict

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

MARKET_CONFIG = {
    "BTC_PERP": "bitcoin",
    "ETH_PERP": "ethereum", 
    "SOL_PERP": "solana",
}


def get_all_prices() -> Dict[str, float]:
    """Get prices for all markets from CoinGecko"""
    try:
        ids = ",".join(MARKET_CONFIG.values())
        url = f"{COINGECKO_API}?ids={ids}&vs_currencies=usd"
        
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode())
            
            prices = {}
            for market, cg_id in MARKET_CONFIG.items():
                if cg_id in data and "usd" in data[cg_id]:
                    prices[market] = round(data[cg_id]["usd"], 2)
            
            return prices
    except Exception as e:
        print(f"CoinGecko error: {e}")
        return {}


def price_loop(interval: int = 30):
    """Continuous price update loop"""
    print(f"🔄 Starting price fetcher (interval: {interval}s)")
    
    while True:
        try:
            prices = get_all_prices()
            if prices:
                print(f"📊 {time.strftime('%H:%M:%S')} - {json.dumps(prices)}")
            else:
                print(f"⚠️  {time.strftime('%H:%M:%S')} - No prices fetched")
        except Exception as e:
            print(f"Error in price loop: {e}")
        
        time.sleep(interval)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        prices = get_all_prices()
        print(json.dumps(prices, indent=2))
    else:
        price_loop()
