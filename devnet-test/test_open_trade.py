#!/usr/bin/env python3
"""
AI Perp DEX - 测试开仓交易
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

# sha256('global:open_position')[:8]
OPEN_POSITION_DISC = bytes([135, 128, 47, 77, 15, 152, 240, 49])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

async def open_position():
    print("📈 AI Perp DEX - 测试开仓交易")
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
    
    print(f"\nPDAs:")
    print(f"  Exchange: {exchange_pda}")
    print(f"  Agent: {agent_pda}")
    print(f"  Market: {market_pda}")
    print(f"  Position: {position_pda}")
    
    # 检查 Agent 抵押金
    agent_info = await client.get_account_info(agent_pda)
    if agent_info.value:
        data = bytes(agent_info.value.data)
        collateral = struct.unpack('<Q', data[72:80])[0]
        print(f"\n当前抵押金: {collateral / 1e6} USDC")
    
    # 开仓参数
    market_index = 0
    size = 10_000  # 0.01 BTC (合约精度)
    entry_price = 97_000_000_000  # $97,000 (6 decimals)
    
    # Required margin = (size * price / 1e6) * (initial_margin_rate / 10000)
    # = (10000 * 97000000000 / 1e6) * (1000 / 10000)
    # = 97000000 * 0.1 = 9700000 = 9.7 USDC
    
    print(f"\n交易参数:")
    print(f"  市场: BTC-PERP")
    print(f"  方向: 做多 (Long)")
    print(f"  大小: {size / 1_000_000} BTC")
    print(f"  价格: ${entry_price / 1_000_000}")
    print(f"  预计保证金: ~$9.7")
    
    # 构建指令
    data = OPEN_POSITION_DISC
    data += struct.pack("<B", market_index)  # market_index
    data += struct.pack("<q", size)          # size (i64, positive = long)
    data += struct.pack("<Q", entry_price)   # entry_price (u64)
    
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=False),  # authority
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=False),    # exchange
        AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),        # agent
        AccountMeta(pubkey=position_pda, is_signer=False, is_writable=True),     # position
        AccountMeta(pubkey=market_pda, is_signer=False, is_writable=True),       # market
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),   # payer
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),  # system_program
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    print(f"\n📤 发送开仓交易...")
    
    try:
        result = await client.send_transaction(tx)
        print(f"✅ 开仓成功! 签名: {result.value}")
        
        await asyncio.sleep(2)
        
        # 验证仓位
        position_info = await client.get_account_info(position_pda)
        if position_info.value:
            data = bytes(position_info.value.data)
            # Position: disc(8) + agent(32) + market_index(1) + size(8) + entry_price(8) + ...
            pos_size = struct.unpack('<q', data[41:49])[0]
            pos_price = struct.unpack('<Q', data[49:57])[0]
            pos_margin = struct.unpack('<Q', data[73:81])[0]
            print(f"\n📊 仓位详情:")
            print(f"   大小: {pos_size / 1_000_000} BTC")
            print(f"   入场价: ${pos_price / 1_000_000}")
            print(f"   保证金: ${pos_margin / 1_000_000}")
        
        # 验证 Agent 抵押金变化
        agent_info = await client.get_account_info(agent_pda)
        if agent_info.value:
            data = bytes(agent_info.value.data)
            collateral = struct.unpack('<Q', data[72:80])[0]
            print(f"   剩余抵押金: {collateral / 1e6} USDC")
            
    except Exception as e:
        error_str = str(e)
        print(f"\n❌ 开仓失败: {error_str[:500]}")
        
        if "InsufficientCollateral" in error_str or "0x1770" in error_str:
            print("   💡 抵押金不足")
        elif "Unauthorized" in error_str:
            print("   💡 权限不足 - 检查 authority")
    
    await client.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(open_position())
