#!/usr/bin/env python3
"""
创建测试 USDC 代币并 mint 给自己
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

# SPL Token program
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

def get_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        ATA_PROGRAM
    )[0]

async def create_test_token():
    print("🪙 创建测试 USDC 代币")
    print("=" * 50)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    # 加载钱包
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 创建新的 mint keypair
    mint_keypair = Keypair()
    print(f"新 Mint: {mint_keypair.pubkey()}")
    
    # 获取 rent
    mint_rent = await client.get_minimum_balance_for_rent_exemption(82)
    print(f"Mint rent: {mint_rent.value / 1e9} SOL")
    
    # 1. 创建 Mint 账户
    create_mint_ix = Instruction(
        program_id=SYSTEM_PROGRAM,
        accounts=[
            AccountMeta(wallet.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(mint_keypair.pubkey(), is_signer=True, is_writable=True),
        ],
        data=struct.pack("<IQQ", 0, mint_rent.value, 82) + bytes(TOKEN_PROGRAM)
    )
    
    # 2. Initialize Mint (6 decimals like USDC)
    # InitializeMint2 instruction: [1, decimals(1), mint_authority(32), freeze_authority_option(1), freeze_authority(32)]
    init_mint_data = bytes([20])  # InitializeMint2 = 20
    init_mint_data += bytes([6])  # 6 decimals
    init_mint_data += bytes(wallet.pubkey())  # mint authority
    init_mint_data += bytes([0])  # no freeze authority
    
    init_mint_ix = Instruction(
        program_id=TOKEN_PROGRAM,
        accounts=[
            AccountMeta(mint_keypair.pubkey(), is_signer=False, is_writable=True),
        ],
        data=init_mint_data
    )
    
    # 获取区块哈希
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    # 构建交易 1: 创建 mint
    msg1 = Message.new_with_blockhash(
        [create_mint_ix, init_mint_ix], 
        wallet.pubkey(), 
        blockhash
    )
    tx1 = Transaction([wallet, mint_keypair], msg1, blockhash)
    
    print("\n📤 发送创建 Mint 交易...")
    try:
        result = await client.send_transaction(tx1)
        print(f"✅ Mint 创建成功! 签名: {result.value}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"❌ 创建 Mint 失败: {e}")
        await client.close()
        return
    
    # 3. 创建 ATA
    user_ata = get_ata(wallet.pubkey(), mint_keypair.pubkey())
    print(f"\n用户 ATA: {user_ata}")
    
    create_ata_ix = Instruction(
        program_id=ATA_PROGRAM,
        accounts=[
            AccountMeta(wallet.pubkey(), is_signer=True, is_writable=True),    # payer
            AccountMeta(user_ata, is_signer=False, is_writable=True),          # ata
            AccountMeta(wallet.pubkey(), is_signer=False, is_writable=False),  # owner
            AccountMeta(mint_keypair.pubkey(), is_signer=False, is_writable=False),  # mint
            AccountMeta(SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(TOKEN_PROGRAM, is_signer=False, is_writable=False),
        ],
        data=bytes([])
    )
    
    # 获取新的区块哈希
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg2 = Message.new_with_blockhash([create_ata_ix], wallet.pubkey(), blockhash)
    tx2 = Transaction([wallet], msg2, blockhash)
    
    print("📤 发送创建 ATA 交易...")
    try:
        result = await client.send_transaction(tx2)
        print(f"✅ ATA 创建成功! 签名: {result.value}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"❌ 创建 ATA 失败: {e}")
        await client.close()
        return
    
    # 4. Mint 1000 USDC
    amount = 1000_000_000  # 1000 USDC (6 decimals)
    
    # MintTo instruction: [7, amount(8 bytes)]
    mint_to_data = bytes([7]) + struct.pack("<Q", amount)
    
    mint_to_ix = Instruction(
        program_id=TOKEN_PROGRAM,
        accounts=[
            AccountMeta(mint_keypair.pubkey(), is_signer=False, is_writable=True),  # mint
            AccountMeta(user_ata, is_signer=False, is_writable=True),               # destination
            AccountMeta(wallet.pubkey(), is_signer=True, is_writable=False),        # authority
        ],
        data=mint_to_data
    )
    
    # 获取新的区块哈希
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg3 = Message.new_with_blockhash([mint_to_ix], wallet.pubkey(), blockhash)
    tx3 = Transaction([wallet], msg3, blockhash)
    
    print(f"📤 Mint {amount / 1_000_000} USDC...")
    try:
        result = await client.send_transaction(tx3)
        print(f"✅ Mint 成功! 签名: {result.value}")
    except Exception as e:
        print(f"❌ Mint 失败: {e}")
        await client.close()
        return
    
    await asyncio.sleep(2)
    
    # 验证余额
    balance = await client.get_token_account_balance(user_ata)
    if balance.value:
        print(f"\n💰 最终余额: {int(balance.value.amount) / 1_000_000} USDC")
    
    # 保存 mint 地址
    config = {
        "test_usdc_mint": str(mint_keypair.pubkey()),
        "user_ata": str(user_ata),
        "wallet": str(wallet.pubkey()),
    }
    
    with open("test_token_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n📝 配置已保存到 test_token_config.json")
    
    print("\n" + "=" * 50)
    print("✅ 测试代币创建完成!")
    print(f"   Mint: {mint_keypair.pubkey()}")
    print(f"   余额: 1000 USDC")
    print("=" * 50)
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(create_test_token())
