#!/usr/bin/env python3
"""
AI Perp DEX - 初始化 Devnet 交易所
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

# Devnet USDC mint
USDC_MINT = Pubkey.from_string("Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr")

# SPL Token program
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# Rent sysvar
RENT_SYSVAR = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# Anchor discriminator for "initialize" instruction
# sha256("global:initialize")[:8]
INITIALIZE_DISCRIMINATOR = bytes([175, 175, 109, 31, 13, 152, 155, 237])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

async def initialize_exchange():
    print("🚀 初始化 AI Perp DEX Exchange")
    print("=" * 50)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    # 加载钱包
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 检查余额
    balance = await client.get_balance(wallet.pubkey())
    print(f"余额: {balance.value / 1e9:.4f} SOL")
    
    # 找到 PDAs
    exchange_pda, exchange_bump = find_pda([b"exchange"], PROGRAM_ID)
    print(f"Exchange PDA: {exchange_pda}")
    
    vault_pda, vault_bump = find_pda([b"vault"], PROGRAM_ID)
    print(f"Vault PDA: {vault_pda}")
    
    # 检查是否已初始化
    exchange_info = await client.get_account_info(exchange_pda)
    if exchange_info.value:
        print("⚠️ Exchange 已经初始化!")
        await client.close()
        return
    
    # 构建 initialize 指令
    # 参数: fee_rate_bps (u16) = 30 (0.3%)
    fee_rate_bps = 30
    data = INITIALIZE_DISCRIMINATOR + struct.pack("<H", fee_rate_bps)
    
    # 账户列表 (按 Anchor 定义的顺序)
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),    # authority
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),      # exchange
        AccountMeta(pubkey=USDC_MINT, is_signer=False, is_writable=False),        # collateral_mint
        AccountMeta(pubkey=vault_pda, is_signer=False, is_writable=True),         # vault
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),   # system_program
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),    # token_program
        AccountMeta(pubkey=RENT_SYSVAR, is_signer=False, is_writable=False),      # rent
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    # 获取最新区块哈希
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    # 构建交易
    msg = Message.new_with_blockhash(
        [ix],
        wallet.pubkey(),
        blockhash
    )
    tx = Transaction([wallet], msg, blockhash)
    
    print("\n发送初始化交易...")
    try:
        result = await client.send_transaction(tx)
        print(f"✅ 交易发送成功!")
        print(f"   签名: {result.value}")
        
        # 等待确认
        print("等待确认...")
        await asyncio.sleep(3)
        
        # 验证
        exchange_info = await client.get_account_info(exchange_pda)
        if exchange_info.value:
            print(f"✅ Exchange 初始化成功!")
            print(f"   数据大小: {len(exchange_info.value.data)} bytes")
        else:
            print("❌ 初始化失败 - 账户未创建")
            
    except Exception as e:
        print(f"❌ 交易失败: {e}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(initialize_exchange())
