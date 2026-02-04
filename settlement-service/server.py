#!/usr/bin/env python3
"""
AI Perp DEX - 链上结算服务
Trade Router 通过 HTTP 调用此服务进行链上结算
"""

import asyncio
import json
import os
import struct
from aiohttp import web
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solders.message import Message
from solders.system_program import ID as SYSTEM_PROGRAM

# 配置
DEVNET_URL = "https://api.devnet.solana.com"
PROGRAM_ID = Pubkey.from_string("AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

# Discriminators
OPEN_POSITION_DISC = bytes([135, 128, 47, 77, 15, 152, 240, 49])
CLOSE_POSITION_DISC = bytes([123, 134, 81, 0, 49, 68, 98, 98])

def find_pda(seeds: list, program_id: Pubkey) -> tuple[Pubkey, int]:
    return Pubkey.find_program_address(seeds, program_id)

class SettlementService:
    def __init__(self):
        self.client = None
        self.wallet = None
        
    async def init(self):
        self.client = AsyncClient(DEVNET_URL, commitment=Confirmed)
        
        # 加载钱包
        wallet_path = os.path.expanduser("~/.config/solana/id.json")
        with open(wallet_path) as f:
            keypair_data = json.load(f)
        self.wallet = Keypair.from_bytes(bytes(keypair_data))
        print(f"Settlement Service 已启动")
        print(f"Authority: {self.wallet.pubkey()}")
        print(f"Program: {PROGRAM_ID}")
        
    async def close(self):
        if self.client:
            await self.client.close()
    
    def get_agent_pda(self, owner: str) -> Pubkey:
        owner_pubkey = Pubkey.from_string(owner)
        return find_pda([b"agent", bytes(owner_pubkey)], PROGRAM_ID)[0]
    
    def get_position_pda(self, agent_pda: Pubkey, market_index: int) -> Pubkey:
        return find_pda([b"position", bytes(agent_pda), bytes([market_index])], PROGRAM_ID)[0]
    
    async def get_agent_collateral(self, owner: str) -> dict:
        """查询 Agent 抵押金"""
        agent_pda = self.get_agent_pda(owner)
        info = await self.client.get_account_info(agent_pda)
        
        if not info.value:
            return {"error": "Agent not found", "collateral": 0}
        
        data = bytes(info.value.data)
        collateral = struct.unpack('<Q', data[72:80])[0]
        
        return {
            "agent": str(agent_pda),
            "owner": owner,
            "collateral": collateral,
            "collateral_usd": collateral / 1_000_000
        }
    
    async def get_position(self, owner: str, market_index: int) -> dict:
        """查询链上仓位"""
        agent_pda = self.get_agent_pda(owner)
        position_pda = self.get_position_pda(agent_pda, market_index)
        
        info = await self.client.get_account_info(position_pda)
        
        if not info.value:
            return {"error": "Position not found", "size": 0}
        
        data = bytes(info.value.data)
        size = struct.unpack('<q', data[41:49])[0]
        entry_price = struct.unpack('<Q', data[49:57])[0]
        liq_price = struct.unpack('<Q', data[57:65])[0]
        margin = struct.unpack('<Q', data[65:73])[0]
        
        return {
            "position": str(position_pda),
            "size": size,
            "entry_price": entry_price,
            "liquidation_price": liq_price,
            "margin": margin
        }
    
    async def settle_open_position(
        self, 
        owner: str, 
        market_index: int, 
        size: int, 
        entry_price: int
    ) -> dict:
        """链上开仓结算"""
        exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
        agent_pda = self.get_agent_pda(owner)
        market_pda, _ = find_pda([b"market", market_index.to_bytes(1, 'little')], PROGRAM_ID)
        position_pda = self.get_position_pda(agent_pda, market_index)
        
        # 构建指令
        data = OPEN_POSITION_DISC
        data += struct.pack("<B", market_index)
        data += struct.pack("<q", size)
        data += struct.pack("<Q", entry_price)
        
        accounts = [
            AccountMeta(pubkey=self.wallet.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=False),
            AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=position_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=market_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.wallet.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ]
        
        ix = Instruction(PROGRAM_ID, data, accounts)
        
        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        
        msg = Message.new_with_blockhash([ix], self.wallet.pubkey(), blockhash)
        tx = Transaction([self.wallet], msg, blockhash)
        
        try:
            result = await self.client.send_transaction(tx)
            return {
                "success": True,
                "signature": str(result.value),
                "position": str(position_pda)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def settle_close_position(
        self, 
        owner: str, 
        market_index: int, 
        exit_price: int
    ) -> dict:
        """链上平仓结算"""
        exchange_pda, _ = find_pda([b"exchange"], PROGRAM_ID)
        agent_pda = self.get_agent_pda(owner)
        market_pda, _ = find_pda([b"market", market_index.to_bytes(1, 'little')], PROGRAM_ID)
        position_pda = self.get_position_pda(agent_pda, market_index)
        
        # 构建指令
        data = CLOSE_POSITION_DISC
        data += struct.pack("<B", market_index)
        data += struct.pack("<Q", exit_price)
        
        accounts = [
            AccountMeta(pubkey=self.wallet.pubkey(), is_signer=True, is_writable=False),
            AccountMeta(pubkey=exchange_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=agent_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=position_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=market_pda, is_signer=False, is_writable=True),
        ]
        
        ix = Instruction(PROGRAM_ID, data, accounts)
        
        blockhash_resp = await self.client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        
        msg = Message.new_with_blockhash([ix], self.wallet.pubkey(), blockhash)
        tx = Transaction([self.wallet], msg, blockhash)
        
        try:
            result = await self.client.send_transaction(tx)
            return {
                "success": True,
                "signature": str(result.value),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# HTTP Handlers
service = SettlementService()

async def health(request):
    return web.json_response({"status": "ok", "service": "settlement"})

async def get_collateral(request):
    owner = request.match_info['owner']
    result = await service.get_agent_collateral(owner)
    return web.json_response(result)

async def get_position(request):
    owner = request.match_info['owner']
    market_index = int(request.match_info.get('market', 0))
    result = await service.get_position(owner, market_index)
    return web.json_response(result)

async def open_position(request):
    data = await request.json()
    result = await service.settle_open_position(
        owner=data['owner'],
        market_index=data.get('market_index', 0),
        size=data['size'],
        entry_price=data['entry_price']
    )
    return web.json_response(result)

async def close_position(request):
    data = await request.json()
    result = await service.settle_close_position(
        owner=data['owner'],
        market_index=data.get('market_index', 0),
        exit_price=data['exit_price']
    )
    return web.json_response(result)

async def init_app():
    await service.init()
    
    app = web.Application()
    app.router.add_get('/health', health)
    app.router.add_get('/collateral/{owner}', get_collateral)
    app.router.add_get('/position/{owner}', get_position)
    app.router.add_get('/position/{owner}/{market}', get_position)
    app.router.add_post('/settle/open', open_position)
    app.router.add_post('/settle/close', close_position)
    
    return app

async def main():
    print("🚀 Starting Settlement Service on :8081")
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    print("✅ Settlement Service running at http://localhost:8081")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
