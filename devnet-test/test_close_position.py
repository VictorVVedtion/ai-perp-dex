#!/usr/bin/env python3
"""
AI Perp DEX - 测试平仓交易
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

# sha256('global:close_position')[:8]
CLOSE_POSITION_DISC = bytes([123, 134, 81, 0, 49, 68, 98, 98])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

async def close_position():
    print("📉 AI Perp DEX - 测试平仓交易")
    print("=" * 60)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # PDAs
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    
    market_index = 0  # BTC
    market_pda, _ = find_pda([b"market", market_index.to_bytes(1, 'little')], PROGRAM_ID)
    position_pda, _ = find_pda(
        [b"position", bytes(agent_pda), bytes([market_index])],
        PROGRAM_ID
    )
    
    # 检查当前仓位
    position_info = await client.get_account_info(position_pda)
    if not position_info.value:
        print("❌ 没有仓位可平!")
        await client.close()
        return
    
    data = bytes(position_info.value.data)
    pos_size = struct.unpack('<q', data[41:49])[0]
    entry_price = struct.unpack('<Q', data[49:57])[0]
    
    print(f"\n当前仓位:")
    print(f"  Size: {pos_size / 1_000_000} BTC")
    print(f"  Entry: ${entry_price / 1_000_000}")
    
    # 平仓参数 - 假设价格涨到 $98,000
    exit_price = 98_000_000_000  # $98,000
    
    print(f"\n平仓参数:")
    print(f"  Exit Price: ${exit_price / 1_000_000}")
    print(f"  预计盈亏: ${(exit_price - entry_price) * pos_size / 1e12}")
    
    # 构建指令
    data = CLOSE_POSITION_DISC
    data += struct.pack("<B", market_index)  # market_index
    data += struct.pack("<Q", exit_price)    # exit_price
    
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=False),  # authority
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),     # exchange
        AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),        # agent
        AccountMeta(pubkey=position_pda, is_signer=False, is_writable=True),     # position
        AccountMeta(pubkey=market_pda, is_signer=False, is_writable=True),       # market
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    print(f"\n📤 发送平仓交易...")
    
    try:
        result = await client.send_transaction(tx)
        print(f"✅ 平仓成功! 签名: {result.value}")
        
        await asyncio.sleep(2)
        
        # 验证 Agent 状态
        agent_info = await client.get_account_info(agent_pda)
        if agent_info.value:
            data = bytes(agent_info.value.data)
            collateral = struct.unpack('<Q', data[72:80])[0]
            realized_pnl = struct.unpack('<q', data[88:96])[0]
            total_trades = struct.unpack('<Q', data[96:104])[0]
            win_count = struct.unpack('<Q', data[104:112])[0]
            
            print(f"\n📊 平仓后状态:")
            print(f"   抵押金: ${collateral / 1e6}")
            print(f"   已实现盈亏: ${realized_pnl / 1e6}")
            print(f"   总交易数: {total_trades}")
            print(f"   获胜次数: {win_count}")
        
        # 检查仓位是否已关闭
        position_info = await client.get_account_info(position_pda)
        if position_info.value:
            data = bytes(position_info.value.data)
            pos_size = struct.unpack('<q', data[41:49])[0]
            print(f"   仓位大小: {pos_size / 1e6} (应为 0)")
            
    except Exception as e:
        error_str = str(e)
        print(f"\n❌ 平仓失败: {error_str[:500]}")
    
    await client.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(close_position())
