#!/usr/bin/env python3
"""
AI Perp DEX - Devnet 完整测试脚本
运行前需要:
1. 升级合约 (需要 ~3 SOL)
2. 或等待当前合约支持
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

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

def get_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    )[0]

# Anchor discriminators (sha256('global:<method>')[:8])
DISCRIMINATORS = {
    "create_market": bytes([103, 226, 97, 235, 200, 188, 251, 254]),
    "update_collateral": bytes([218, 227, 184, 124, 133, 81, 157, 131]),
    "deposit": bytes([242, 35, 198, 137, 82, 225, 242, 182]),
    "withdraw": bytes([183, 18, 70, 156, 148, 109, 161, 34]),
    "open_position": bytes([135, 128, 47, 77, 15, 152, 240, 49]),
}

async def check_status():
    """检查当前链上状态"""
    print("📊 AI Perp DEX - Devnet 状态检查")
    print("=" * 60)
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    
    # SOL 余额
    sol = await client.get_balance(wallet.pubkey())
    print(f"\n💰 钱包: {wallet.pubkey()}")
    print(f"   SOL: {sol.value / 1e9:.4f}")
    
    # Exchange
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    exchange_info = await client.get_account_info(exchange_pda)
    print(f"\n📦 Exchange: {exchange_pda}")
    print(f"   状态: {'✅ 已初始化' if exchange_info.value else '❌ 未初始化'}")
    
    if exchange_info.value:
        data = bytes(exchange_info.value.data)
        if len(data) >= 72:
            usdc_mint = Pubkey.from_bytes(data[40:72])
            print(f"   USDC Mint: {usdc_mint}")
    
    # Agent
    agent_pda, _ = find_pda([b"agent", bytes(wallet.pubkey())], PROGRAM_ID)
    agent_info = await client.get_account_info(agent_pda)
    print(f"\n🤖 Agent: {agent_pda}")
    print(f"   状态: {'✅ 已注册' if agent_info.value else '❌ 未注册'}")
    
    if agent_info.value:
        data = bytes(agent_info.value.data)
        if len(data) >= 80:
            collateral = struct.unpack("<Q", data[72:80])[0]
            print(f"   抵押金: {collateral / 1e6} USDC")
    
    # Market (BTC)
    market_pda, _ = find_pda([b"market", bytes([0])], PROGRAM_ID)
    market_info = await client.get_account_info(market_pda)
    print(f"\n📈 Market BTC: {market_pda}")
    print(f"   状态: {'✅ 已创建' if market_info.value else '❌ 未创建'}")
    
    # Vault
    vault_pda, _ = find_pda([b"vault"], PROGRAM_ID)
    vault_info = await client.get_account_info(vault_pda)
    print(f"\n🏦 Vault: {vault_pda}")
    print(f"   状态: {'✅ 已创建' if vault_info.value else '❌ 未创建'}")
    
    # 测试代币配置
    config_path = "/Users/vvedition/clawd/ai-perp-dex/devnet-test/test_token_config.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            token_config = json.load(f)
        test_mint = Pubkey.from_string(token_config["test_usdc_mint"])
        user_ata = get_ata(wallet.pubkey(), test_mint)
        
        print(f"\n🪙 测试 USDC:")
        print(f"   Mint: {test_mint}")
        
        try:
            balance = await client.get_token_account_balance(Pubkey.from_string(token_config["user_ata"]))
            if balance.value:
                print(f"   余额: {int(balance.value.amount) / 1e6} USDC")
        except:
            print(f"   余额: 无法获取")
    
    await client.close()
    
    # 下一步建议
    print("\n" + "=" * 60)
    print("📋 下一步操作:")
    print("-" * 60)
    print(f"1. 获取更多 SOL (当前: {sol.value / 1e9:.2f}, 需要: ~3 SOL)")
    print("   - 使用 https://faucet.solana.com/ (登录 GitHub 获得更多)")
    print("   - 或等待 CLI rate limit 恢复")
    print()
    print("2. 升级合约:")
    print("   cd /Users/vvedition/clawd/ai-perp-dex/solana-program")
    print("   anchor upgrade --program-id AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT \\")
    print("     target/deploy/ai_perp_dex.so --provider.cluster devnet")
    print()
    print("3. 创建市场 (BTC-PERP)")
    print("   python3 devnet-test/create_market.py")
    print()
    print("4. 更新 USDC Mint 并存入抵押金")
    print("   python3 devnet-test/update_and_deposit.py")
    print()
    print("5. 执行交易测试")
    print("   python3 devnet-test/test_trading.py")
    print("=" * 60)

async def create_market():
    """创建 BTC-PERP 市场"""
    print("📈 创建 BTC-PERP 市场...")
    
    client = AsyncClient(DEVNET_URL, commitment=Confirmed)
    
    wallet_path = os.path.expanduser("~/.config/solana/id.json")
    with open(wallet_path) as f:
        keypair_data = json.load(f)
    wallet = Keypair.from_bytes(bytes(keypair_data))
    
    exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
    market_index = 0
    market_pda, _ = find_pda([b"market", market_index.to_bytes(1, 'little')], PROGRAM_ID)
    
    # 检查是否已存在
    market_info = await client.get_account_info(market_pda)
    if market_info.value:
        print(f"   ⚠️ 市场已存在: {market_pda}")
        await client.close()
        return
    
    # Symbol: "BTC-PERP" padded to 16 bytes
    symbol = b"BTC-PERP" + b"\x00" * 8
    
    # 构建指令
    data = DISCRIMINATORS["create_market"]
    data += struct.pack("<B", market_index)  # market_index
    data += symbol  # symbol [u8; 16]
    data += struct.pack("<H", 1000)  # initial_margin_rate (10%)
    data += struct.pack("<H", 500)   # maintenance_margin_rate (5%)
    data += struct.pack("<B", 10)    # max_leverage (10x)
    
    accounts = [
        AccountMeta(pubkey=wallet.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=False),
        AccountMeta(pubkey=market_pda, is_signer=False, is_writable=True),
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
    ]
    
    ix = Instruction(PROGRAM_ID, data, accounts)
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    msg = Message.new_with_blockhash([ix], wallet.pubkey(), blockhash)
    tx = Transaction([wallet], msg, blockhash)
    
    try:
        result = await client.send_transaction(tx)
        print(f"   ✅ 市场创建成功! 签名: {result.value}")
    except Exception as e:
        print(f"   ❌ 创建失败: {str(e)[:200]}")
    
    await client.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "create-market":
        asyncio.run(create_market())
    else:
        asyncio.run(check_status())
