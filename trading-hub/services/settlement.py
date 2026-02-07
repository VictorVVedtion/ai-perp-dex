"""
Settlement Layer - 结算层

支持:
1. 链上结算 (Base L2)
2. 模拟结算 (测试用)
3. 多签结算 (大额交易)
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import uuid
import hashlib
import json

# Redis 持久化
_redis_client = None
def get_redis():
    global _redis_client
    if _redis_client is None and os.environ.get("USE_REDIS", "true").lower() == "true":
        try:
            import redis
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            print(f"⚠️ Settlement Redis connection failed: {e}")
            _redis_client = False  # Mark as failed
    return _redis_client if _redis_client else None


class SettlementStatus(Enum):
    PENDING = "pending"
    CONFIRMING = "confirming"
    SETTLED = "settled"
    FAILED = "failed"


class SettlementType(Enum):
    INTERNAL = "internal"    # 内部记账
    ONCHAIN = "onchain"      # 链上结算
    MULTISIG = "multisig"    # 多签结算
    DEPOSIT = "deposit"      # 链上充值 (Lite 模式)
    WITHDRAW = "withdraw"    # 链上提现 (Lite 模式)


@dataclass
class Settlement:
    """结算记录"""
    settlement_id: str
    settlement_type: SettlementType
    
    # 交易双方
    from_agent: str
    to_agent: str
    
    # 金额
    amount_usdc: float
    fee_usdc: float = 0.0
    
    # 关联交易
    match_id: Optional[str] = None
    position_id: Optional[str] = None
    bet_id: Optional[str] = None
    
    # 链上数据
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    chain: str = "base"  # base, ethereum, solana
    
    # 状态
    status: SettlementStatus = SettlementStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    settled_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "settlement_id": self.settlement_id,
            "type": self.settlement_type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "amount_usdc": self.amount_usdc,
            "fee_usdc": self.fee_usdc,
            "tx_hash": self.tx_hash,
            "chain": self.chain,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentBalance:
    """Agent 余额"""
    agent_id: str
    balance_usdc: float = 0.0  # 起始 $0，需要先存款
    locked_usdc: float = 0.0  # 锁定中 (等待结算)
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def available(self) -> float:
        return self.balance_usdc - self.locked_usdc
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "balance": self.balance_usdc,
            "locked": self.locked_usdc,
            "available": self.available,
        }


class SettlementEngine:
    """
    结算引擎
    
    用法:
        engine = SettlementEngine()
        
        # 内部结算 (即时)
        settlement = await engine.settle_internal(
            from_agent="agent_001",
            to_agent="agent_002",
            amount=100,
        )
        
        # 链上结算
        settlement = await engine.settle_onchain(
            from_agent="agent_001",
            to_agent="agent_002",
            amount=1000,
        )
    """
    
    # 配置
    MIN_ONCHAIN_AMOUNT = 100  # $100 以上走链上
    ONCHAIN_FEE_RATE = 0.001  # 0.1% 链上手续费
    MULTISIG_THRESHOLD = 10000  # $10000 以上需要多签
    
    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
        self.settlements: Dict[str, Settlement] = {}
        self.balances: Dict[str, AgentBalance] = {}
        
        # 链上配置 (Base L2)
        self.chain_config = {
            "base": {
                "rpc": "https://mainnet.base.org",
                "usdc_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "settlement_contract": None,  # TODO: 部署合约
            }
        }
        
        print(f"💰 Settlement Engine started (simulation={self.simulation_mode})")
        
        # 从 Redis 加载所有余额
        self._load_all_balances_from_redis()
    
    def _load_all_balances_from_redis(self):
        """从 Redis 批量加载所有余额"""
        r = get_redis()
        if not r:
            print(f"⚠️ Redis not available for balance loading")
            return
        
        try:
            all_data = r.hgetall("perpdex:balances")
            loaded = 0
            for agent_id, data_str in all_data.items():
                try:
                    d = json.loads(data_str)
                    balance = AgentBalance(
                        agent_id=d["agent_id"],
                        balance_usdc=d.get("balance_usdc", 0),
                        locked_usdc=d.get("locked_usdc", 0),
                        total_deposited=d.get("total_deposited", 0),
                        total_withdrawn=d.get("total_withdrawn", 0),
                        last_updated=datetime.fromisoformat(d["last_updated"]) if d.get("last_updated") else None,
                    )
                    self.balances[agent_id] = balance
                    loaded += 1
                except Exception as e:
                    print(f"⚠️ Failed to load balance for {agent_id}: {e}")
            
            if loaded > 0:
                print(f"💰 Loaded {loaded} balances from Redis")
        except Exception as e:
            print(f"⚠️ Failed to load balances from Redis: {e}")
    
    def _save_balance_to_redis(self, balance: AgentBalance):
        """保存余额到 Redis"""
        r = get_redis()
        if r:
            data = {
                "agent_id": balance.agent_id,
                "balance_usdc": balance.balance_usdc,
                "locked_usdc": balance.locked_usdc,
                "total_deposited": balance.total_deposited,
                "total_withdrawn": balance.total_withdrawn,
                "last_updated": balance.last_updated.isoformat() if balance.last_updated else None,
            }
            r.hset("perpdex:balances", balance.agent_id, json.dumps(data))
    
    def _load_balance_from_redis(self, agent_id: str) -> Optional[AgentBalance]:
        """从 Redis 加载余额"""
        r = get_redis()
        if r:
            data = r.hget("perpdex:balances", agent_id)
            if data:
                d = json.loads(data)
                return AgentBalance(
                    agent_id=d["agent_id"],
                    balance_usdc=d.get("balance_usdc", 0),
                    locked_usdc=d.get("locked_usdc", 0),
                    total_deposited=d.get("total_deposited", 0),
                    total_withdrawn=d.get("total_withdrawn", 0),
                    last_updated=datetime.fromisoformat(d["last_updated"]) if d.get("last_updated") else None,
                )
        return None
    
    def get_balance(self, agent_id: str) -> AgentBalance:
        """获取余额"""
        # 先查内存
        if agent_id in self.balances:
            return self.balances[agent_id]
        
        # 从 Redis 加载
        balance = self._load_balance_from_redis(agent_id)
        if balance:
            self.balances[agent_id] = balance
            return balance
        
        # 新建
        self.balances[agent_id] = AgentBalance(agent_id=agent_id)
        return self.balances[agent_id]
    
    def deposit(self, agent_id: str, amount: float) -> AgentBalance:
        """入金"""
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive, got {amount}")
        balance = self.get_balance(agent_id)
        balance.balance_usdc += amount
        balance.total_deposited += amount
        balance.last_updated = datetime.now()
        self._save_balance_to_redis(balance)
        return balance
    
    def withdraw(self, agent_id: str, amount: float) -> bool:
        """出金 (Paper Trading 内部记账)"""
        balance = self.get_balance(agent_id)
        if balance.available < amount:
            return False
        balance.balance_usdc -= amount
        balance.total_withdrawn += amount
        balance.last_updated = datetime.now()
        self._save_balance_to_redis(balance)
        return True

    # === Lite 模式: 链上充提 ===

    async def deposit_with_tx_verification(
        self,
        agent_id: str,
        amount: float,
        tx_signature: str,
        from_wallet: str,
    ) -> dict:
        """
        链上充值 (Lite 模式)

        流程:
        1. 调用 SolanaClient 验证链上 tx
        2. 验证通过后增加余额
        3. 记录结算记录

        Returns:
            {"success": True/False, "balance": ..., "settlement": ..., "error": ...}
        """
        from services.solana_client import solana_client

        # 验证链上交易
        verification = await solana_client.verify_deposit_tx(
            tx_signature=tx_signature,
            expected_amount=amount,
            from_wallet=from_wallet,
        )

        if not verification.valid:
            return {
                "success": False,
                "error": verification.error,
            }

        # 增加余额
        balance = self.deposit(agent_id, verification.amount)

        # 创建结算记录
        settlement = Settlement(
            settlement_id=f"stl_{uuid.uuid4().hex[:12]}",
            settlement_type=SettlementType.DEPOSIT,
            from_agent=from_wallet,
            to_agent=agent_id,
            amount_usdc=verification.amount,
            tx_hash=tx_signature,
            chain="solana",
            status=SettlementStatus.SETTLED,
            settled_at=datetime.now(),
        )
        self.settlements[settlement.settlement_id] = settlement

        # 持久化结算记录
        r = get_redis()
        if r:
            r.hset(
                "perpdex:settlements",
                settlement.settlement_id,
                json.dumps(settlement.to_dict()),
            )

        return {
            "success": True,
            "balance": balance.to_dict(),
            "settlement": settlement.to_dict(),
            "tx_hash": tx_signature,
        }

    async def withdraw_onchain(
        self,
        agent_id: str,
        amount: float,
        wallet_address: str,
    ) -> dict:
        """
        链上提现 (Lite 模式)

        流程:
        1. 检查余额 & 锁定金额
        2. SolanaClient 从 Vault 发送 USDC
        3. 确认后扣减余额
        4. 失败则解锁金额

        Returns:
            {"success": True/False, "tx_hash": ..., "balance": ..., "error": ...}
        """
        from services.solana_client import solana_client

        # 检查余额
        balance = self.get_balance(agent_id)
        if balance.available < amount:
            return {
                "success": False,
                "error": f"Insufficient balance: available ${balance.available:.2f}, requested ${amount:.2f}",
            }

        # 锁定金额
        balance.locked_usdc += amount
        self._save_balance_to_redis(balance)

        try:
            # 从 Vault 发送 USDC
            result = await solana_client.send_usdc(
                to_wallet=wallet_address,
                amount=amount,
                agent_id=agent_id,
            )

            if not result.success:
                # 失败: 解锁金额
                balance.locked_usdc -= amount
                self._save_balance_to_redis(balance)
                return {
                    "success": False,
                    "error": result.error,
                }

            # 成功: 解锁并扣减
            balance.locked_usdc -= amount
            balance.balance_usdc -= amount
            balance.total_withdrawn += amount
            balance.last_updated = datetime.now()
            self._save_balance_to_redis(balance)

            # 创建结算记录
            settlement = Settlement(
                settlement_id=f"stl_{uuid.uuid4().hex[:12]}",
                settlement_type=SettlementType.WITHDRAW,
                from_agent=agent_id,
                to_agent=wallet_address,
                amount_usdc=amount,
                tx_hash=result.tx_signature,
                chain="solana",
                status=SettlementStatus.SETTLED,
                settled_at=datetime.now(),
            )
            self.settlements[settlement.settlement_id] = settlement

            # 持久化
            r = get_redis()
            if r:
                r.hset(
                    "perpdex:settlements",
                    settlement.settlement_id,
                    json.dumps(settlement.to_dict()),
                )

            return {
                "success": True,
                "tx_hash": result.tx_signature,
                "balance": balance.to_dict(),
                "settlement": settlement.to_dict(),
            }

        except Exception as e:
            # 异常: 解锁金额
            balance.locked_usdc -= amount
            self._save_balance_to_redis(balance)
            return {
                "success": False,
                "error": f"Withdrawal failed: {str(e)}",
            }
    
    async def settle_internal(
        self,
        from_agent: str,
        to_agent: str,
        amount: float,
        match_id: str = None,
        position_id: str = None,
        bet_id: str = None,
    ) -> Settlement:
        """
        内部结算 (即时，0 手续费)
        
        用于 Dark Pool 内部匹配
        """
        # 检查余额
        from_balance = self.get_balance(from_agent)
        if from_balance.available < amount:
            raise ValueError(f"Insufficient balance: {from_balance.available} < {amount}")
        
        # 创建结算记录
        settlement = Settlement(
            settlement_id=f"stl_{uuid.uuid4().hex[:12]}",
            settlement_type=SettlementType.INTERNAL,
            from_agent=from_agent,
            to_agent=to_agent,
            amount_usdc=amount,
            fee_usdc=0,
            match_id=match_id,
            position_id=position_id,
            bet_id=bet_id,
        )
        
        # 执行转账
        from_balance.balance_usdc -= amount
        to_balance = self.get_balance(to_agent)
        to_balance.balance_usdc += amount
        
        # 更新状态
        settlement.status = SettlementStatus.SETTLED
        settlement.settled_at = datetime.now()
        
        self.settlements[settlement.settlement_id] = settlement
        return settlement
    
    async def settle_onchain(
        self,
        from_agent: str,
        to_agent: str,
        amount: float,
        chain: str = "base",
    ) -> Settlement:
        """
        链上结算
        
        1. 锁定资金
        2. 发送链上交易
        3. 等待确认
        4. 解锁/转账
        """
        # 检查余额
        from_balance = self.get_balance(from_agent)
        if from_balance.available < amount:
            raise ValueError(f"Insufficient balance: {from_balance.available} < {amount}")
        
        fee = amount * self.ONCHAIN_FEE_RATE
        total = amount + fee
        
        # 创建结算记录
        settlement = Settlement(
            settlement_id=f"stl_{uuid.uuid4().hex[:12]}",
            settlement_type=SettlementType.ONCHAIN,
            from_agent=from_agent,
            to_agent=to_agent,
            amount_usdc=amount,
            fee_usdc=fee,
            chain=chain,
        )
        
        # 锁定资金
        from_balance.locked_usdc += total
        settlement.status = SettlementStatus.CONFIRMING
        
        self.settlements[settlement.settlement_id] = settlement
        
        if self.simulation_mode:
            # 模拟链上交易
            await asyncio.sleep(0.05)  # 模拟延迟 (优化: 50ms)
            
            # 生成模拟 tx hash
            tx_data = f"{from_agent}:{to_agent}:{amount}:{datetime.now().isoformat()}"
            settlement.tx_hash = "0x" + hashlib.sha256(tx_data.encode()).hexdigest()
            settlement.block_number = 12345678
            
            # 完成结算
            from_balance.locked_usdc -= total
            from_balance.balance_usdc -= total
            
            to_balance = self.get_balance(to_agent)
            to_balance.balance_usdc += amount
            
            settlement.status = SettlementStatus.SETTLED
            settlement.settled_at = datetime.now()
        else:
            # 真实链上交易
            try:
                tx_hash = await self._send_onchain_tx(
                    from_agent, to_agent, amount, chain
                )
                settlement.tx_hash = tx_hash
                
                # 等待确认
                confirmed = await self._wait_confirmation(tx_hash, chain)
                
                if confirmed:
                    from_balance.locked_usdc -= total
                    from_balance.balance_usdc -= total
                    
                    to_balance = self.get_balance(to_agent)
                    to_balance.balance_usdc += amount
                    
                    settlement.status = SettlementStatus.SETTLED
                    settlement.settled_at = datetime.now()
                else:
                    # 失败，解锁资金
                    from_balance.locked_usdc -= total
                    settlement.status = SettlementStatus.FAILED
                    settlement.error = "Transaction not confirmed"
                    
            except Exception as e:
                from_balance.locked_usdc -= total
                settlement.status = SettlementStatus.FAILED
                settlement.error = str(e)
        
        return settlement
    
    async def _send_onchain_tx(self, from_agent: str, to_agent: str, amount: float, chain: str) -> str:
        """发送链上交易 (需要实现)"""
        # TODO: 实现真实的链上交易
        # 1. 获取 Agent 的链上地址
        # 2. 构建 USDC transfer 交易
        # 3. 签名并发送
        raise NotImplementedError("Real onchain transactions not implemented")
    
    async def _wait_confirmation(self, tx_hash: str, chain: str, confirmations: int = 3) -> bool:
        """等待链上确认"""
        # TODO: 实现确认逻辑
        return True
    
    async def settle_multisig(
        self,
        from_agent: str,
        to_agent: str,
        amount: float,
        signers: List[str],
        required_signatures: int = 2,
    ) -> Settlement:
        """
        多签结算
        
        大额交易需要多个签名者确认
        """
        settlement = Settlement(
            settlement_id=f"stl_{uuid.uuid4().hex[:12]}",
            settlement_type=SettlementType.MULTISIG,
            from_agent=from_agent,
            to_agent=to_agent,
            amount_usdc=amount,
        )
        
        # TODO: 实现多签逻辑
        # 1. 创建多签请求
        # 2. 收集签名
        # 3. 达到阈值后执行
        
        self.settlements[settlement.settlement_id] = settlement
        return settlement
    
    def get_settlements(
        self,
        agent_id: str = None,
        status: SettlementStatus = None,
        limit: int = 100,
    ) -> List[Settlement]:
        """查询结算记录"""
        results = list(self.settlements.values())
        
        if agent_id:
            results = [s for s in results if s.from_agent == agent_id or s.to_agent == agent_id]
        
        if status:
            results = [s for s in results if s.status == status]
        
        return sorted(results, key=lambda s: s.created_at, reverse=True)[:limit]
    
    def get_stats(self) -> dict:
        """获取统计"""
        total_settled = sum(
            s.amount_usdc for s in self.settlements.values()
            if s.status == SettlementStatus.SETTLED
        )
        total_fees = sum(
            s.fee_usdc for s in self.settlements.values()
            if s.status == SettlementStatus.SETTLED
        )
        
        by_type = {}
        for s in self.settlements.values():
            t = s.settlement_type.value
            if t not in by_type:
                by_type[t] = {"count": 0, "volume": 0}
            by_type[t]["count"] += 1
            by_type[t]["volume"] += s.amount_usdc
        
        return {
            "total_settlements": len(self.settlements),
            "total_volume": total_settled,
            "total_fees": total_fees,
            "by_type": by_type,
        }


# 单例
settlement_engine = SettlementEngine(simulation_mode=True)
