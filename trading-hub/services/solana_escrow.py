"""
Solana Escrow - 链上资金托管

功能:
1. USDC 存入托管账户
2. 交易结算
3. 提现
4. 多签授权
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import hashlib
import base58
import json


class EscrowStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RELEASING = "releasing"
    RELEASED = "released"
    DISPUTED = "disputed"


@dataclass
class EscrowAccount:
    """托管账户"""
    escrow_id: str
    agent_id: str
    
    # 链上地址
    escrow_address: str  # PDA
    agent_wallet: str
    
    # 金额
    deposited_amount: float
    available_amount: float
    locked_amount: float = 0.0
    
    # 状态
    status: EscrowStatus = EscrowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    # 链上数据
    deposit_tx: Optional[str] = None
    last_tx: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "escrow_id": self.escrow_id,
            "agent_id": self.agent_id,
            "escrow_address": self.escrow_address,
            "agent_wallet": self.agent_wallet,
            "deposited": self.deposited_amount,
            "available": self.available_amount,
            "locked": self.locked_amount,
            "status": self.status.value,
        }


@dataclass
class EscrowTransaction:
    """托管交易记录"""
    tx_id: str
    escrow_id: str
    tx_type: str  # "deposit", "lock", "unlock", "settle", "withdraw"
    amount: float
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    tx_hash: Optional[str] = None
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "escrow_id": self.escrow_id,
            "type": self.tx_type,
            "amount": self.amount,
            "tx_hash": self.tx_hash,
            "status": self.status,
            "timestamp": self.created_at.isoformat(),
        }


class SolanaEscrow:
    """
    Solana 托管服务
    
    架构:
    - 每个 Agent 一个 PDA (Program Derived Address) 托管账户
    - USDC SPL Token
    - 交易所程序控制资金流转
    
    用法:
        escrow = SolanaEscrow()
        
        # 创建托管账户
        account = await escrow.create_account("agent_001", "wallet_address")
        
        # 存入资金
        tx = await escrow.deposit("agent_001", 1000)
        
        # 锁定资金 (开仓)
        await escrow.lock("agent_001", 100)
        
        # 结算 (平仓)
        await escrow.settle("agent_001", "agent_002", 50)
        
        # 提现
        await escrow.withdraw("agent_001", 500)
    """
    
    # Solana 配置
    PROGRAM_ID = "EscrowProgramID111111111111111111111111111"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
        self.accounts: Dict[str, EscrowAccount] = {}
        self.transactions: List[EscrowTransaction] = []
        
        # Solana 连接
        self.rpc_url = "https://api.mainnet-beta.solana.com"
        
        print(f"🔐 Solana Escrow started (simulation={self.simulation_mode})")
    
    def _generate_pda(self, agent_id: str) -> str:
        """生成 PDA 地址"""
        # 简化版: 实际应使用 Solana SDK
        seed = f"escrow:{agent_id}".encode()
        hash_bytes = hashlib.sha256(seed).digest()[:32]
        return base58.b58encode(hash_bytes).decode()
    
    async def create_account(self, agent_id: str, wallet_address: str) -> EscrowAccount:
        """创建托管账户"""
        import uuid
        
        escrow_address = self._generate_pda(agent_id)
        
        account = EscrowAccount(
            escrow_id=f"esc_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            escrow_address=escrow_address,
            agent_wallet=wallet_address,
            deposited_amount=0,
            available_amount=0,
            status=EscrowStatus.ACTIVE,
        )
        
        if not self.simulation_mode:
            # 真实创建链上账户
            # TODO: 调用 Solana 程序创建 PDA 账户
            pass
        
        self.accounts[agent_id] = account
        return account
    
    def get_account(self, agent_id: str) -> Optional[EscrowAccount]:
        """获取托管账户"""
        return self.accounts.get(agent_id)
    
    async def deposit(self, agent_id: str, amount: float) -> EscrowTransaction:
        """存入资金"""
        import uuid
        
        account = self.accounts.get(agent_id)
        if not account:
            raise ValueError("Escrow account not found")
        
        tx = EscrowTransaction(
            tx_id=f"etx_{uuid.uuid4().hex[:12]}",
            escrow_id=account.escrow_id,
            tx_type="deposit",
            amount=amount,
        )
        
        if self.simulation_mode:
            # 模拟存款
            tx.tx_hash = "sim_" + hashlib.sha256(f"{agent_id}:{amount}:{datetime.now()}".encode()).hexdigest()[:32]
            tx.status = "confirmed"
            
            account.deposited_amount += amount
            account.available_amount += amount
            account.deposit_tx = tx.tx_hash
            account.last_tx = tx.tx_hash
        else:
            # 真实存款
            # TODO: 监听 USDC transfer 到 PDA
            pass
        
        self.transactions.append(tx)
        return tx
    
    async def lock(self, agent_id: str, amount: float, reason: str = "trade") -> EscrowTransaction:
        """锁定资金 (开仓时)"""
        import uuid
        
        account = self.accounts.get(agent_id)
        if not account:
            raise ValueError("Escrow account not found")
        
        if account.available_amount < amount:
            raise ValueError(f"Insufficient available balance: {account.available_amount} < {amount}")
        
        tx = EscrowTransaction(
            tx_id=f"etx_{uuid.uuid4().hex[:12]}",
            escrow_id=account.escrow_id,
            tx_type="lock",
            amount=amount,
        )
        
        account.available_amount -= amount
        account.locked_amount += amount
        
        tx.status = "confirmed"
        tx.tx_hash = "sim_lock_" + hashlib.sha256(f"{agent_id}:{amount}".encode()).hexdigest()[:16]
        
        self.transactions.append(tx)
        return tx
    
    async def unlock(self, agent_id: str, amount: float) -> EscrowTransaction:
        """解锁资金 (平仓时)"""
        import uuid
        
        account = self.accounts.get(agent_id)
        if not account:
            raise ValueError("Escrow account not found")
        
        amount = min(amount, account.locked_amount)
        
        tx = EscrowTransaction(
            tx_id=f"etx_{uuid.uuid4().hex[:12]}",
            escrow_id=account.escrow_id,
            tx_type="unlock",
            amount=amount,
        )
        
        account.locked_amount -= amount
        account.available_amount += amount
        
        tx.status = "confirmed"
        self.transactions.append(tx)
        return tx
    
    async def settle(
        self,
        from_agent: str,
        to_agent: str,
        amount: float,
        reason: str = "trade_settlement",
    ) -> EscrowTransaction:
        """结算 (从一方转到另一方)"""
        import uuid
        
        from_account = self.accounts.get(from_agent)
        to_account = self.accounts.get(to_agent)
        
        if not from_account or not to_account:
            raise ValueError("Escrow account not found")
        
        # 从锁定金额中扣除
        actual_amount = min(amount, from_account.locked_amount)
        
        tx = EscrowTransaction(
            tx_id=f"etx_{uuid.uuid4().hex[:12]}",
            escrow_id=from_account.escrow_id,
            tx_type="settle",
            amount=actual_amount,
            from_agent=from_agent,
            to_agent=to_agent,
        )
        
        if self.simulation_mode:
            from_account.locked_amount -= actual_amount
            to_account.available_amount += actual_amount
            
            tx.status = "confirmed"
            tx.tx_hash = "sim_settle_" + hashlib.sha256(f"{from_agent}:{to_agent}:{amount}".encode()).hexdigest()[:16]
        else:
            # 真实链上结算
            # TODO: 调用 Solana 程序转账
            pass
        
        self.transactions.append(tx)
        return tx
    
    async def withdraw(self, agent_id: str, amount: float, to_wallet: str = None) -> EscrowTransaction:
        """提现"""
        import uuid
        
        account = self.accounts.get(agent_id)
        if not account:
            raise ValueError("Escrow account not found")
        
        if account.available_amount < amount:
            raise ValueError(f"Insufficient available balance: {account.available_amount} < {amount}")
        
        tx = EscrowTransaction(
            tx_id=f"etx_{uuid.uuid4().hex[:12]}",
            escrow_id=account.escrow_id,
            tx_type="withdraw",
            amount=amount,
        )
        
        if self.simulation_mode:
            account.available_amount -= amount
            account.deposited_amount -= amount
            
            tx.status = "confirmed"
            tx.tx_hash = "sim_withdraw_" + hashlib.sha256(f"{agent_id}:{amount}".encode()).hexdigest()[:16]
        else:
            # 真实提现
            # TODO: 调用 Solana 程序转账 USDC 到用户钱包
            pass
        
        self.transactions.append(tx)
        return tx
    
    def get_transactions(self, agent_id: str = None, limit: int = 50) -> List[EscrowTransaction]:
        """获取交易记录"""
        txs = self.transactions
        if agent_id:
            account = self.accounts.get(agent_id)
            if account:
                txs = [t for t in txs if t.escrow_id == account.escrow_id]
        return txs[-limit:]
    
    def get_total_tvl(self) -> dict:
        """获取总 TVL"""
        total_deposited = sum(a.deposited_amount for a in self.accounts.values())
        total_available = sum(a.available_amount for a in self.accounts.values())
        total_locked = sum(a.locked_amount for a in self.accounts.values())
        
        return {
            "total_deposited": total_deposited,
            "total_available": total_available,
            "total_locked": total_locked,
            "accounts": len(self.accounts),
        }


# 单例
solana_escrow = SolanaEscrow(simulation_mode=True)
