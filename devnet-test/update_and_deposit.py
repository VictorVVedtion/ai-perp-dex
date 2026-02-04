#!/usr/bin/env python3
"""
更新 USDC Mint 并存入抵押金
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
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
RENT_SYSVAR = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# Discriminators
UPDATE_COLLATERAL_DISC = bytes([218, 227, 184, 124, 133, 81, 157, 131])
DEPOSIT_DISC = bytes([242, 35, 198, 137, 82, 225, 242, 182])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

def get_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    )[0]

async def update_collateral_mint(wallet, client, new_mint):
    """更新抵押品 mint"""
    print(f"\n1️⃣ 更新 USDC Mint 到: {new_mint}")
    
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    new_vault_pda, _ = find_pda([b"vault", bytes(new_mint)], PROGRAM_ID)
    
    print(f"   Exchange: {exchange_pda}")
    print(f"   New Vault: {new_vault_pda}")
    
    # 检查新 vault 是否已存在
    vault_info = await client.get_account_info(new_vault_pda)
    if vault_info.value:
        print(f"   ⚠️ Vault 已存在，跳过更新")
        return True
    
    data = UPDATE_COLLATERAL_DISC
    
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),   # authority
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),     # exchange
        AccountMeta(pubkey=new_mint, is_signer=False, is_writable=False),        # new_collateral_mint
        AccountMeta(pubkey=new_vault_pda, is_signer=False, is_writable=True),    # new_vault
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),  # system_program
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),   # token_program
        AccountMeta(pubkey=RENT_SYSVAR, is_signer=False, is_writable=False),     # rent
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    try:
        result = await client.send_transaction(tx)
        print(f"   ✅ Mint 更新成功! 签名: {result.value}")
        await asyncio.sleep(2)
        return True
    except Exception as e:
        print(f"   ❌ 更新失败: {str(e)[:300]}")
        return False

async def deposit_collateral(wallet, client, new_mint, amount):
    """存入抵押金"""
    print(f"\n2️⃣ 存入 {amount / 1e6} USDC")
    
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    
    # 从 Exchange 账户读取 vault 地址
    exchange_info = await client.get_account_info(exchange_pda)
    if not exchange_info.value:
        print("   ❌ Exchange 不存在")
        return False
    data = bytes(exchange_info.value.data)
    vault_pda = Pubkey.from_bytes(data[72:104])
    
    user_ata = get_ata(wallet.pubkey(), new_mint)
    
    print(f"   User ATA: {user_ata}")
    print(f"   Vault: {vault_pda}")
    
    # 检查余额
    try:
        balance = await client.get_token_account_balance(user_ata)
        if balance.value:
            print(f"   当前余额: {int(balance.value.amount) / 1e6} USDC")
    except:
        print(f"   ⚠️ 无法获取余额")
    
    data = DEPOSIT_DISC + struct.pack("<Q", amount)
    
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),   # owner
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),     # exchange
        AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),        # agent
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),         # owner_token_account
        AccountMeta(pubkey=vault_pda, is_signer=False, is_writable=True),        # vault
        AccountMeta(pubkey=new_mint, is_signer=False, is_writable=False),        # mint
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),   # token_program
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    try:
        result = await client.send_transaction(tx)
        print(f"   ✅ 存款成功! 签名: {result.value}")
        return True
    except Exception as e:
        print(f"   ❌ 存款失败: {str(e)[:300]}")
        return False

async def main():
    print("💰 AI Perp DEX - 更新 USDC Mint 并存入抵押金")
    print("=" * 60)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 加载测试代币配置
    config_path = "/Users/vvedition/clawd/ai-perp-dex/test_token_config.json"
    if not os.path.exists(config_path):
        print("❌ 测试代币配置不存在！请先运行 create_test_token.py")
        await client.close()
        return
    
    with open(config_path) as f:
        token_config = json.load(f)
    
    new_mint = Pubkey.from_string(token_config["test_usdc_mint"])
    print(f"测试 USDC Mint: {new_mint}")
    
    # Step 1: 更新 USDC Mint
    success = await update_collateral_mint(wallet, client, new_mint)
    if not success:
        print("\n⚠️ Mint 更新失败，尝试继续...")
    
    # Step 2: 存入 100 USDC
    deposit_amount = 100_000_000  # 100 USDC
    await deposit_collateral(wallet, client, new_mint, deposit_amount)
    
    # 验证
    print("\n3️⃣ 验证状态...")
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    agent_info = await client.get_account_info(agent_pda)
    if agent_info.value:
        data = bytes(agent_info.value.data)
        if len(data) >= 80:
            collateral = struct.unpack("<Q", data[72:80])[0]
            print(f"   Agent 抵押金: {collateral / 1e6} USDC")
    
    await client.close()
    print("\n" + "=" * 60)
    print("✅ 完成！现在可以测试交易了")

if __name__ == "__main__":
    asyncio.run(main())
