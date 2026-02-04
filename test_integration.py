#!/usr/bin/env python3
"""
Integration Test for AI Perp DEX P2P Trading
Tests: Trader Request → MM Quote → Accept → Position
"""

import asyncio
import json
import aiohttp
from datetime import datetime

BASE_URL = "http://localhost:8080"

async def test_p2p_flow():
    print("=" * 60)
    print("🧪 AI Perp DEX P2P Integration Test")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. Health check
        print("\n1️⃣ Health Check...")
        async with session.get(f"{BASE_URL}/health") as resp:
            data = await resp.json()
            print(f"   Status: {data['status']}")
        
        # 2. Get markets
        print("\n2️⃣ Markets Info...")
        async with session.get(f"{BASE_URL}/markets") as resp:
            data = await resp.json()
            for m in data['data']:
                print(f"   {m['market']}: ${m['current_price']}")
        
        # 3. Create trade request (Trader)
        print("\n3️⃣ Creating Trade Request (Trader Agent)...")
        trader_id = f"trader_{datetime.now().strftime('%H%M%S')}"
        request_data = {
            "agent_id": trader_id,
            "market": "BTC-PERP",
            "side": "long",
            "size_usdc": 100.0,
            "leverage": 10,
            "max_funding_rate": 0.02,
            "expires_in": 300
        }
        async with session.post(f"{BASE_URL}/trade/request", json=request_data) as resp:
            result = await resp.json()
            if not result.get('success'):
                print(f"   ❌ Error: {result.get('error')}")
                return
            trade_request = result['data']
            request_id = trade_request['id']
            print(f"   ✅ Request ID: {request_id}")
            print(f"   Market: {trade_request['market']}, Size: ${trade_request['size_usdc']}")
        
        # 4. Create quote (MM Agent)
        print("\n4️⃣ Creating Quote (MM Agent)...")
        mm_id = f"mm_{datetime.now().strftime('%H%M%S')}"
        quote_data = {
            "request_id": request_id,
            "agent_id": mm_id,
            "funding_rate": 0.01,  # 1%
            "collateral_usdc": 15.0,  # MM puts up $15 collateral
            "valid_for": 60
        }
        async with session.post(f"{BASE_URL}/trade/quote", json=quote_data) as resp:
            result = await resp.json()
            if not result.get('success'):
                print(f"   ❌ Error: {result.get('error')}")
                return
            quote = result['data']
            quote_id = quote['id']
            print(f"   ✅ Quote ID: {quote_id}")
            print(f"   Funding Rate: {quote['funding_rate']*100}%")
        
        # 5. Accept quote (Trader)
        print("\n5️⃣ Accepting Quote (Position Created)...")
        accept_data = {
            "request_id": request_id,
            "quote_id": quote_id,
            "signature": "mock_signature_for_testing"
        }
        async with session.post(f"{BASE_URL}/trade/accept", json=accept_data) as resp:
            result = await resp.json()
            if not result.get('success'):
                print(f"   ❌ Error: {result.get('error')}")
                return
            position = result['data']
            position_id = position['id']
            print(f"   ✅ Position ID: {position_id}")
            print(f"   Entry Price: ${position['entry_price']}")
            print(f"   Trader: {position['trader_agent']}")
            print(f"   MM: {position['mm_agent']}")
        
        # 6. Check positions
        print("\n6️⃣ Checking Positions...")
        async with session.get(f"{BASE_URL}/positions/{trader_id}") as resp:
            result = await resp.json()
            positions = result.get('data', [])
            print(f"   Trader has {len(positions)} position(s)")
        
        # 7. Close position
        print("\n7️⃣ Closing Position...")
        close_data = {
            "position_id": position_id,
            "agent_id": trader_id,
            "size_percent": 100
        }
        async with session.post(f"{BASE_URL}/trade/close", json=close_data) as resp:
            result = await resp.json()
            if not result.get('success'):
                print(f"   ❌ Error: {result.get('error')}")
                return
            close_result = result['data']
            print(f"   ✅ Position Closed")
            print(f"   Trader PnL: ${close_result['pnl_trader']:.2f}")
            print(f"   MM PnL: ${close_result['pnl_mm']:.2f}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! P2P trading flow works correctly.")
        print("=" * 60)
        
        # Summary
        print("\n📊 Summary:")
        print(f"   • Program ID (Devnet): 6F37235k7H3JXTPvRv9w1uAAdPKkcD9avVqmzUTxGpRC")
        print(f"   • Trade Router: {BASE_URL}")
        print(f"   • Request → Quote → Position → Close: ✅")


if __name__ == "__main__":
    asyncio.run(test_p2p_flow())
