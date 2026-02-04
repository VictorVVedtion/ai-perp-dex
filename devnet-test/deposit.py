#!/usr/bin/env python3
"""
AI Perp DEX - 存入 USDC 抵押金
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
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

DEVNET_URL = "https://api.devnet.solana.com"
PROGRAM_ID = Pubkey.from_string("AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT")

# Devnet USDC mint
USDC_MINT = Pubkey.from_string("Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr")

# SPL Token program
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# Anchor discriminator for "deposit"
DEPOSIT_DISCRIMINATOR = bytes([242, 35, 198, 137, 82, 225, 242, 182])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

def get_associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """计算 ATA 地址"""
    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    )[0]

async def deposit(amount: int = 100_000_000):  # 100 USDC (6 decimals)
    print(f"💰 存入 {amount / 1_000_000} USDC")
    print("=" * 50)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    # 加载钱包
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    print(f"钱包: {wallet.pubkey()}")
    
    # 找到所有需要的地址
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    vault_pda, _ = find_pda([b"vault"], PROGRAM_ID)
    
    # 用户的 USDC ATA
    user_ata = get_associated_token_address(wallet.pubkey(), USDC_MINT)
    
    print(f"Exchange: {exchange_pda}")
    print(f"Agent: {agent_pda}")
    print(f"Vault: {vault_pda}")
    print(f"User ATA: {user_ata}")
    
    # 检查用户 USDC 余额
    user_balance = await client.get_token_account_balance(user_ata)
    if user_balance.value:
        print(f"USDC 余额: {int(user_balance.value.amount) / 1_000_000}")
    else:
        print("❌ 没有 USDC 余额!")
        print("请先获取 Devnet USDC:")
        print(f"  spl-token airdrop 100 {USDC_MINT} --owner {wallet.pubkey()}")
        await client.close()
        return
    
    # 构建指令数据: amount (u64)
    data = DEPOSIT_DISCRIMINATOR + struct.pack("<Q", amount)
    
    # 账户列表
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),   # depositor
        AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),        # agent
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),     # exchange
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),         # from (user ATA)
        AccountMeta(pubkey=vault_pda, is_signer=False, is_writable=True),        # to (vault)
        AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),   # token_program
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    # 获取区块哈希
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    # 构建交易
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    print("\n发送存款交易...")
    try:
        result = await client.send_transaction(tx)
        print(f"✅ 交易发送成功!")
        print(f"   签名: {result.value}")
        
        await asyncio.sleep(3)
        print("✅ 存款完成!")
            
    except Exception as e:
        print(f"❌ 交易失败: {e}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(deposit())
