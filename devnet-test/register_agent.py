#!/usr/bin/env python3
"""
AI Perp DEX - 注册 Agent
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
from solders.system_program import ID as SYSTEM_PROGRAM

DEVNET_URL = "https://api.devnet.solana.com"
PROGRAM_ID = Pubkey.from_string("AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT")

# Anchor discriminator for "register_agent"
# sha256("global:register_agent")[:8]
REGISTER_AGENT_DISCRIMINATOR = bytes([135, 157, 66, 195, 2, 113, 175, 30])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

async def register_agent(name: str = "TestAgent"):
    print(f"🤖 注册 Agent: {name}")
    print("=" * 50)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    # 加载钱包
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 找到 PDAs
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    
    print(f"Exchange: {exchange_pda}")
    print(f"Agent PDA: {agent_pda}")
    
    # 检查是否已注册
    agent_info = await client.get_account_info(agent_pda)
    if agent_info.value:
        print("✅ Agent 已经注册!")
        await client.close()
        return agent_pda
    
    # 构建指令数据
    # 参数: name (String) - Anchor 编码: 4字节长度 + UTF-8 字节
    name_bytes = name.encode('utf-8')
    data = REGISTER_AGENT_DISCRIMINATOR + struct.pack("<I", len(name_bytes)) + name_bytes
    
    # 账户列表 (按 Anchor 定义顺序: owner, exchange, agent, system_program)
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),   # owner
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),     # exchange
        AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),        # agent
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),  # system_program
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    # 获取区块哈希
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    # 构建交易
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    print("\n发送注册交易...")
    try:
        result = await client.send_transaction(tx)
        print(f"✅ 交易发送成功!")
        print(f"   签名: {result.value}")
        
        await asyncio.sleep(3)
        
        # 验证
        agent_info = await client.get_account_info(agent_pda)
        if agent_info.value:
            print(f"✅ Agent 注册成功!")
            print(f"   数据大小: {len(agent_info.value.data)} bytes")
        else:
            print("❌ 注册失败")
            
    except Exception as e:
        print(f"❌ 交易失败: {e}")
    
    await client.close()
    return agent_pda

if __name__ == "__main__":
    asyncio.run(register_agent("AI_Trader_Bot"))
