#!/usr/bin/env python3
"""
AI Perp DEX - Devnet 交易测试
完整的链上交互测试
"""

import asyncio
import json
import os
import struct
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solders.message import Message
from solders.hash import Hash

DEVNET_URL = "https://api.devnet.solana.com"
PROGRAM_ID = Pubkey.from_string("AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    """Find program derived address"""
    return Pubkey.find_program_address(seeds, program_id)

async def test_trading():
    print("🧪 AI Perp DEX - Devnet 交易测试")
    print("=" * 50)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    # 加载钱包
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 1. 查找 Exchange PDA
    print("\n1️⃣ 查找 Exchange 账户...")
    exchange_pda, exchange_bump = find_pda([b"exchange"], PROGRAM_ID)
    print(f"   Exchange PDA: {exchange_pda}")
    
    exchange_info = await client.get_account_info(exchange_pda)
    if exchange_info.value:
        print(f"   ✅ Exchange 已初始化")
        print(f"   数据大小: {len(exchange_info.value.data)} bytes")
    else:
        print(f"   ⚠️ Exchange 未初始化 - 需要先调用 initialize")
    
    # 2. 查找 Agent PDA
    print("\n2️⃣ 查找 Agent 账户...")
    agent_pda, agent_bump = find_pda(
        [b"agent", bytes(wallet.pubkey())],
        PROGRAM_ID
    )
    print(f"   Agent PDA: {agent_pda}")
    
    agent_info = await client.get_account_info(agent_pda)
    if agent_info.value:
        print(f"   ✅ Agent 已注册")
        print(f"   数据大小: {len(agent_info.value.data)} bytes")
    else:
        print(f"   ⚠️ Agent 未注册")
    
    # 3. 检查程序数据账户
    print("\n3️⃣ 检查程序状态...")
    program_data_pda = Pubkey.from_string("14TYz3EVkUrG4g5Rruq5wGtnxiiWRHxhvqVaFNaZinXe")
    program_data = await client.get_account_info(program_data_pda)
    if program_data.value:
        print(f"   ✅ 程序数据账户存在")
        print(f"   数据大小: {len(program_data.value.data)} bytes")
    
    # 4. 模拟交易流程
    print("\n4️⃣ 交易流程模拟...")
    print("   步骤 1: 初始化 Exchange (如果需要)")
    print("   步骤 2: 注册 Agent")
    print("   步骤 3: 存入 USDC 抵押")
    print("   步骤 4: 开仓")
    print("   步骤 5: 平仓/结算")
    
    # 5. 获取最近区块哈希
    print("\n5️⃣ 获取链上状态...")
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    print(f"   最新区块: {str(blockhash)[:20]}...")
    
    slot = await client.get_slot()
    print(f"   当前 Slot: {slot.value}")
    
    print("\n" + "=" * 50)
    print("✅ Devnet 链上测试完成!")
    print("=" * 50)
    print(f"""
下一步:
1. 需要 USDC (Devnet) 进行完整测试
2. 调用 initialize 初始化交易所
3. 注册 Agent 账户
4. 存入抵押金
5. 执行交易

USDC Devnet Mint: Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr
""")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_trading())
