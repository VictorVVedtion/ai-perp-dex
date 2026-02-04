#!/usr/bin/env python3
"""
AI Perp DEX - Devnet 测试
"""

import asyncio
import json
import os
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

DEVNET_URL = "https://api.devnet.solana.com"
PROGRAM_ID = "AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT"

async def test_devnet():
    print("🧪 AI Perp DEX Devnet 测试")
    print("=" * 50)
    
    client = AsyncClient(DEVNET_URL)
    
    # 1. 检查程序
    print("\n1️⃣ 检查程序状态...")
    program = await client.get_account_info(Pubkey.from_string(PROGRAM_ID))
    if program.value:
        print(f"   ✅ 程序已部署到 Devnet")
        print(f"   Owner: {program.value.owner}")
        print(f"   可执行: {program.value.executable}")
        print(f"   数据大小: {len(program.value.data)} bytes")
    else:
        print("   ❌ 程序未找到")
        await client.close()
        return
    
    # 2. 检查钱包
    print("\n2️⃣ 检查钱包...")
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    
    balance = await client.get_balance(wallet.pubkey())
    print(f"   地址: {wallet.pubkey()}")
    print(f"   余额: {balance.value / 1e9:.4f} SOL")
    
    # 3. 获取最近交易
    print("\n3️⃣ 查询程序最近交易...")
    sigs = await client.get_signatures_for_address(
        Pubkey.from_string(PROGRAM_ID),
        limit=5
    )
    print(f"   最近 {len(sigs.value)} 笔交易:")
    for sig in sigs.value[:3]:
        sig_str = str(sig.signature)
        print(f"   - {sig_str[:20]}... (slot: {sig.slot})")
    
    # 4. 测试 RPC
    print("\n4️⃣ RPC 测试...")
    slot = await client.get_slot()
    print(f"   当前 Slot: {slot.value}")
    
    version = await client.get_version()
    print(f"   Solana 版本: {version.value.solana_core}")
    
    print("\n" + "=" * 50)
    print("✅ Devnet 测试完成!")
    print(f"   程序 ID: {PROGRAM_ID}")
    print(f"   钱包: {wallet.pubkey()}")
    print(f"   余额: {balance.value / 1e9:.4f} SOL")
    print("=" * 50)
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_devnet())
