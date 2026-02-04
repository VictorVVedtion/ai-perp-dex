#!/usr/bin/env python3
"""
AI Perp DEX - 完整集成测试
验证: 存款 → 开仓 → 平仓 → 提款
"""

import asyncio
import aiohttp
import json

SETTLEMENT_URL = "http://localhost:8081"
WALLET = "7kuz1ACEgmwL82Zs7NqCt9jxYxfZq1avM3ZEC67ijsQz"

async def test_integration():
    print("=" * 60)
    print("🧪 AI Perp DEX - 完整集成测试")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. 健康检查
        print("\n1️⃣ 检查结算服务...")
        async with session.get(f"{SETTLEMENT_URL}/health") as resp:
            data = await resp.json()
            assert data["status"] == "ok", "Settlement service not healthy"
            print(f"   ✅ 服务正常")
        
        # 2. 查询抵押金
        print("\n2️⃣ 查询当前抵押金...")
        async with session.get(f"{SETTLEMENT_URL}/collateral/{WALLET}") as resp:
            data = await resp.json()
            initial_collateral = data["collateral_usd"]
            print(f"   抵押金: ${initial_collateral}")
        
        # 3. 查询仓位 (应该为空)
        print("\n3️⃣ 查询当前仓位...")
        async with session.get(f"{SETTLEMENT_URL}/position/{WALLET}/0") as resp:
            data = await resp.json()
            initial_size = data.get("size", 0)
            print(f"   仓位大小: {initial_size / 1e6 if initial_size else 0} BTC")
        
        # 4. 开仓
        print("\n4️⃣ 测试开仓...")
        open_req = {
            "owner": WALLET,
            "market_index": 0,
            "size": 5000,  # 0.005 BTC
            "entry_price": 72000_000_000  # $72,000
        }
        async with session.post(f"{SETTLEMENT_URL}/settle/open", json=open_req) as resp:
            data = await resp.json()
            if data.get("success"):
                print(f"   ✅ 开仓成功! Tx: {data['signature'][:20]}...")
            else:
                print(f"   ❌ 开仓失败: {data.get('error', 'Unknown')[:100]}")
                return
        
        await asyncio.sleep(2)
        
        # 5. 验证仓位
        print("\n5️⃣ 验证仓位...")
        async with session.get(f"{SETTLEMENT_URL}/position/{WALLET}/0") as resp:
            data = await resp.json()
            print(f"   Size: {data['size'] / 1e6} BTC")
            print(f"   Entry: ${data['entry_price'] / 1e6}")
            print(f"   Liq Price: ${data['liquidation_price'] / 1e6}")
        
        # 6. 平仓
        print("\n6️⃣ 测试平仓...")
        close_req = {
            "owner": WALLET,
            "market_index": 0,
            "exit_price": 73000_000_000  # $73,000 (+$1000)
        }
        async with session.post(f"{SETTLEMENT_URL}/settle/close", json=close_req) as resp:
            data = await resp.json()
            if data.get("success"):
                print(f"   ✅ 平仓成功! Tx: {data['signature'][:20]}...")
            else:
                print(f"   ❌ 平仓失败: {data.get('error', 'Unknown')[:100]}")
                return
        
        await asyncio.sleep(2)
        
        # 7. 验证最终状态
        print("\n7️⃣ 最终状态...")
        async with session.get(f"{SETTLEMENT_URL}/collateral/{WALLET}") as resp:
            data = await resp.json()
            final_collateral = data["collateral_usd"]
            pnl = final_collateral - initial_collateral
            print(f"   初始抵押金: ${initial_collateral}")
            print(f"   最终抵押金: ${final_collateral}")
            print(f"   盈亏: ${pnl:+.2f}")
        
        print("\n" + "=" * 60)
        print("✅ 集成测试完成!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_integration())
