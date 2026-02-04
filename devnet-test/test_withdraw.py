#!/usr/bin/env python3
"""
AI Perp DEX - 测试提款
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

DEVNET_URL = "https://api.devnet.solana.com"
PROGRAM_ID = Pubkey.from_string("AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# sha256('global:withdraw')[:8]
WITHDRAW_DISC = bytes([183, 18, 70, 156, 148, 109, 161, 34])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

def get_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    )[0]

async def withdraw(amount: int = 50_000_000):  # 50 USDC
    print(f"💸 AI Perp DEX - 提款 {amount / 1e6} USDC")
    print("=" * 60)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 加载测试代币配置
    with open("/Users/vvedition/clawd/ai-perp-dex/test_token_config.json") as f:
        token_config = json.load(f)
    mint = Pubkey.from_string(token_config["test_usdc_mint"])
    
    # PDAs
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    
    # 从 Exchange 读取 vault
    exchange_info = await client.get_account_info(exchange_pda)
    vault_pda = Pubkey.from_bytes(bytes(exchange_info.value.data)[72:104])
    
    user_ata = get_ata(wallet.pubkey(), mint)
    
    # 检查当前状态
    agent_info = await client.get_account_info(agent_pda)
    if agent_info.value:
        data = bytes(agent_info.value.data)
        collateral = struct.unpack('<Q', data[72:80])[0]
        print(f"\n当前抵押金: ${collateral / 1e6}")
    
    user_balance = await client.get_token_account_balance(user_ata)
    if user_balance.value:
        print(f"钱包 USDC: ${int(user_balance.value.amount) / 1e6}")
    
    print(f"\n提款金额: ${amount / 1e6}")
    
    # 构建指令
    data = WITHDRAW_DISC + struct.pack("<Q", amount)
    
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),   # owner
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),     # exchange
        AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),        # agent
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),         # owner_token_account
        AccountMeta(pubkey=vault_pda, is_signer=False, is_writable=True),        # vault
        AccountMeta(pubkey=mint, is_signer=False, is_writable=False),            # mint
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),   # token_program
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    print(f"\n📤 发送提款交易...")
    
    try:
        result = await client.send_transaction(tx)
        print(f"✅ 提款成功! 签名: {result.value}")
        
        await asyncio.sleep(2)
        
        # 验证状态
        agent_info = await client.get_account_info(agent_pda)
        if agent_info.value:
            data = bytes(agent_info.value.data)
            collateral = struct.unpack('<Q', data[72:80])[0]
            print(f"\n📊 提款后状态:")
            print(f"   抵押金: ${collateral / 1e6}")
        
        user_balance = await client.get_token_account_balance(user_ata)
        if user_balance.value:
            print(f"   钱包 USDC: ${int(user_balance.value.amount) / 1e6}")
            
    except Exception as e:
        error_str = str(e)
        print(f"\n❌ 提款失败: {error_str[:500]}")
    
    await client.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(withdraw())
