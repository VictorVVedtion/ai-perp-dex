"""
Bridge Base ETH to Hyperliquid (via Arbitrum USDC)

步骤:
1. Base ETH → Arbitrum USDC (deBridge)
2. Arbitrum USDC → Hyperliquid (deposit)
"""

import os
import time
import requests
from web3 import Web3
from eth_account import Account

# 配置
ARIA_ADDRESS = "0xc900999f72D3058604E57746f117a2412d62E44a"
ARIA_PRIVATE_KEY = "3ec78dffab0788e353cb53a14e8d52dfcc2320d22fd8fc77be9e7db429752c36"

# Chain IDs
BASE_CHAIN_ID = 8453
ARBITRUM_CHAIN_ID = 42161

# RPCs
BASE_RPC = "https://mainnet.base.org"
ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

# Token addresses
ETH_ADDRESS = "0x0000000000000000000000000000000000000000"
USDC_ARBITRUM = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

def get_bridge_quote(amount_wei: int):
    """获取 deBridge 报价"""
    params = {
        'srcChainId': BASE_CHAIN_ID,
        'srcChainTokenIn': ETH_ADDRESS,
        'srcChainTokenInAmount': str(amount_wei),
        'dstChainId': ARBITRUM_CHAIN_ID,
        'dstChainTokenOut': USDC_ARBITRUM,
        'dstChainTokenOutRecipient': ARIA_ADDRESS,
        'prependOperatingExpenses': 'true',
    }
    
    resp = requests.get('https://api.dln.trade/v1.0/dln/order/quote', params=params)
    return resp.json()

def create_bridge_tx(amount_wei: int):
    """创建桥接交易"""
    params = {
        'srcChainId': BASE_CHAIN_ID,
        'srcChainTokenIn': ETH_ADDRESS,
        'srcChainTokenInAmount': str(amount_wei),
        'dstChainId': ARBITRUM_CHAIN_ID,
        'dstChainTokenOut': USDC_ARBITRUM,
        'dstChainTokenOutRecipient': ARIA_ADDRESS,
        'srcChainOrderAuthorityAddress': ARIA_ADDRESS,
        'dstChainOrderAuthorityAddress': ARIA_ADDRESS,
        'prependOperatingExpenses': 'true',
    }
    
    resp = requests.get('https://api.dln.trade/v1.0/dln/order/create-tx', params=params)
    return resp.json()

def main():
    print("🌉 Bridge Base ETH → Hyperliquid")
    print("=" * 50)
    
    # 连接 Base
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    account = Account.from_key(ARIA_PRIVATE_KEY)
    
    print(f"Address: {account.address}")
    
    # 检查余额
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = balance_wei / 1e18
    print(f"Base ETH Balance: {balance_eth:.6f} ETH")
    
    if balance_eth < 0.01:
        print("❌ Not enough ETH")
        return
    
    # 留一点 gas，桥接 0.045 ETH
    bridge_amount_eth = 0.045
    bridge_amount_wei = int(bridge_amount_eth * 1e18)
    
    print(f"\nBridging: {bridge_amount_eth} ETH")
    
    # 获取报价
    print("\n📊 Getting quote...")
    quote = get_bridge_quote(bridge_amount_wei)
    
    if 'estimation' not in quote:
        print(f"❌ Quote failed: {quote}")
        return
    
    out_amount = int(quote['estimation']['dstChainTokenOut']['amount']) / 1e6
    print(f"Expected output: ~${out_amount:.2f} USDC on Arbitrum")
    
    # 创建交易
    print("\n📝 Creating transaction...")
    tx_data = create_bridge_tx(bridge_amount_wei)
    
    if 'tx' not in tx_data:
        print(f"❌ TX creation failed: {tx_data}")
        return
    
    tx = tx_data['tx']
    
    # 构建交易
    transaction = {
        'from': account.address,
        'to': Web3.to_checksum_address(tx['to']),
        'value': int(tx['value']),
        'data': tx['data'],
        'gas': 300000,  # 估计 gas
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
        'chainId': BASE_CHAIN_ID,
    }
    
    print(f"\nTransaction:")
    print(f"  To: {transaction['to']}")
    print(f"  Value: {transaction['value'] / 1e18:.6f} ETH")
    print(f"  Gas Price: {transaction['gasPrice'] / 1e9:.2f} gwei")
    
    # 确认
    confirm = input("\n⚠️ Send transaction? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return
    
    # 签名并发送
    print("\n🚀 Signing and sending...")
    signed = account.sign_transaction(transaction)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    
    print(f"✅ Transaction sent!")
    print(f"   Hash: {tx_hash.hex()}")
    print(f"   Explorer: https://basescan.org/tx/{tx_hash.hex()}")
    
    # 等待确认
    print("\n⏳ Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt['status'] == 1:
        print(f"✅ Bridge initiated successfully!")
        print(f"\n📍 Next steps:")
        print(f"   1. Wait 1-5 minutes for bridge to complete")
        print(f"   2. Check Arbitrum for USDC")
        print(f"   3. Deposit to Hyperliquid")
    else:
        print(f"❌ Transaction failed!")

if __name__ == "__main__":
    main()
