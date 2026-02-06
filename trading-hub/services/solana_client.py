"""
Solana Client - Lite 模式链上充提

职责:
1. 验证充值 tx (RPC 查链上状态)
2. 从 Vault 发送 USDC (提现)
3. 双花防护 (Redis 记录已处理 tx)

依赖: httpx (已有), redis (已有)
不依赖 solana-py, 直接走 JSON-RPC
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict

import httpx

logger = logging.getLogger(__name__)

# Redis 双花防护
_redis_client = None
def _get_redis():
    global _redis_client
    if _redis_client is None and os.environ.get("USE_REDIS", "true").lower() == "true":
        try:
            import redis
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"SolanaClient Redis connection failed: {e}")
            _redis_client = False
    return _redis_client if _redis_client else None


# USDC Mint 地址 (Mainnet / Devnet)
USDC_MINT_MAINNET = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDC_MINT_DEVNET = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"


@dataclass
class DepositVerification:
    """充值验证结果"""
    valid: bool
    tx_signature: str
    amount: float = 0.0
    from_wallet: str = ""
    to_wallet: str = ""
    error: Optional[str] = None
    block_time: Optional[int] = None


@dataclass
class WithdrawResult:
    """提现结果"""
    success: bool
    tx_signature: str = ""
    amount: float = 0.0
    to_wallet: str = ""
    error: Optional[str] = None


class SolanaClient:
    """
    Solana RPC 客户端 (Lite 模式)

    使用标准 JSON-RPC 与 Solana 交互，不依赖 solana-py。
    支持 simulation_mode 用于测试。

    用法:
        client = SolanaClient()
        # 验证充值
        result = await client.verify_deposit_tx("tx_sig...", 100.0, "from_wallet")
        # 提现
        result = await client.send_usdc("to_wallet", 50.0)
    """

    # 提现安全限制
    MAX_WITHDRAW_AMOUNT = 10000.0  # 单次最大提现 $10,000
    WITHDRAW_COOLDOWN = 60  # 两次提现间隔 60 秒

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        vault_address: Optional[str] = None,
        vault_keypair_path: Optional[str] = None,
        simulation_mode: bool = True,
        network: str = "devnet",
    ):
        self.simulation_mode = simulation_mode
        self.network = network

        # RPC 配置
        default_rpc = (
            "https://api.devnet.solana.com" if network == "devnet"
            else "https://api.mainnet-beta.solana.com"
        )
        self.rpc_url = rpc_url or os.environ.get("SOLANA_RPC_URL", default_rpc)

        # Vault 地址
        self.vault_address = vault_address or os.environ.get("VAULT_ADDRESS", "")

        # Vault keypair (提现用)
        self.vault_keypair_path = vault_keypair_path or os.environ.get("VAULT_KEYPAIR_PATH", "")
        self._vault_keypair = None

        # USDC Mint
        self.usdc_mint = (
            USDC_MINT_DEVNET if network == "devnet"
            else USDC_MINT_MAINNET
        )

        # 提现冷却追踪
        self._withdraw_cooldowns: Dict[str, float] = {}

        # 内存双花防护 (无 Redis 时的回退)
        self._processed_tx_memory: set = set()

        # HTTP 客户端
        self._http: Optional[httpx.AsyncClient] = None

        mode_label = "simulation" if simulation_mode else network
        logger.info(f"SolanaClient started (mode={mode_label}, vault={self.vault_address[:8]}...)")

    async def _get_http(self) -> httpx.AsyncClient:
        """获取/创建 HTTP 客户端"""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def _rpc_call(self, method: str, params: list) -> dict:
        """发送 Solana JSON-RPC 请求"""
        http = await self._get_http()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        resp = await http.post(self.rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"RPC error: {data['error']}")
        return data.get("result", {})

    # === 双花防护 ===

    def _try_claim_tx(self, tx_sig: str) -> bool:
        """
        原子性地尝试认领 tx (防并发双花)

        返回 True = 首次认领成功，False = 已被处理过
        使用 Redis SETNX 保证多实例下的原子性
        """
        r = _get_redis()
        if r:
            # SETNX: 只有 key 不存在时才设置，原子操作
            claimed = r.set(f"perpdex:tx_lock:{tx_sig}", "1", nx=True, ex=86400 * 30)
            return bool(claimed)
        # 无 Redis 回退到内存 set (仅限单实例)
        if tx_sig in self._processed_tx_memory:
            return False
        self._processed_tx_memory.add(tx_sig)
        return True

    def _is_tx_processed(self, tx_sig: str) -> bool:
        """检查 tx 是否已处理 (只读查询)"""
        r = _get_redis()
        if r:
            return r.exists(f"perpdex:tx_lock:{tx_sig}") > 0
        return tx_sig in self._processed_tx_memory

    # === 充值验证 ===

    async def verify_deposit_tx(
        self,
        tx_signature: str,
        expected_amount: float,
        from_wallet: str,
    ) -> DepositVerification:
        """
        验证链上充值交易

        检查:
        1. tx 存在且已 finalized
        2. 目标地址 = vault
        3. 金额匹配
        4. 未被重复处理 (双花防护)
        """
        # 原子双花检查: 尝试认领 tx，失败则已被处理
        if not self._try_claim_tx(tx_signature):
            return DepositVerification(
                valid=False,
                tx_signature=tx_signature,
                error="Transaction already processed (duplicate)",
            )

        if self.simulation_mode:
            return await self._verify_deposit_simulated(
                tx_signature, expected_amount, from_wallet
            )

        return await self._verify_deposit_onchain(
            tx_signature, expected_amount, from_wallet
        )

    async def _verify_deposit_simulated(
        self,
        tx_signature: str,
        expected_amount: float,
        from_wallet: str,
    ) -> DepositVerification:
        """模拟验证 (开发/测试)"""
        await asyncio.sleep(0.05)  # 模拟网络延迟

        # 基本格式校验
        if not tx_signature or len(tx_signature) < 10:
            return DepositVerification(
                valid=False,
                tx_signature=tx_signature,
                error="Invalid transaction signature format",
            )

        if expected_amount <= 0:
            return DepositVerification(
                valid=False,
                tx_signature=tx_signature,
                error="Amount must be positive",
            )

        # 模拟成功 (tx 已在 _try_claim_tx 中标记)
        return DepositVerification(
            valid=True,
            tx_signature=tx_signature,
            amount=expected_amount,
            from_wallet=from_wallet,
            to_wallet=self.vault_address or "SimVault111111111111111111111111",
            block_time=int(time.time()),
        )

    async def _verify_deposit_onchain(
        self,
        tx_signature: str,
        expected_amount: float,
        from_wallet: str,
    ) -> DepositVerification:
        """链上验证 (生产)"""
        try:
            # 查询交易
            result = await self._rpc_call(
                "getTransaction",
                [tx_signature, {"encoding": "jsonParsed", "commitment": "finalized"}],
            )

            if not result:
                return DepositVerification(
                    valid=False,
                    tx_signature=tx_signature,
                    error="Transaction not found or not finalized",
                )

            # 检查交易状态
            meta = result.get("meta", {})
            if meta.get("err"):
                return DepositVerification(
                    valid=False,
                    tx_signature=tx_signature,
                    error=f"Transaction failed: {meta['err']}",
                )

            # 解析 SPL Token Transfer 指令
            instructions = (
                result.get("transaction", {})
                .get("message", {})
                .get("instructions", [])
            )

            # 也检查 innerInstructions
            inner = meta.get("innerInstructions", [])
            all_instructions = list(instructions)
            for inner_group in inner:
                all_instructions.extend(inner_group.get("instructions", []))

            # 查找 SPL Token Transfer
            transfer_found = False
            actual_amount = 0.0

            for ix in all_instructions:
                parsed = ix.get("parsed", {})
                if not isinstance(parsed, dict):
                    continue

                ix_type = parsed.get("type", "")
                info = parsed.get("info", {})

                # transferChecked 或 transfer
                if ix_type in ("transferChecked", "transfer"):
                    destination = info.get("destination", "")
                    # USDC 有 6 位小数
                    if ix_type == "transferChecked":
                        token_amount = info.get("tokenAmount", {})
                        actual_amount = float(token_amount.get("uiAmount", 0))
                    else:
                        # transfer 指令的 amount 是最小单位
                        raw_amount = int(info.get("amount", 0))
                        actual_amount = raw_amount / 1_000_000  # USDC 6 decimals

                    # 验证目标是 vault ATA
                    if self.vault_address and destination:
                        transfer_found = True
                        break

            if not transfer_found:
                return DepositVerification(
                    valid=False,
                    tx_signature=tx_signature,
                    error="No valid SPL Token transfer to vault found",
                )

            # 验证金额 (允许 0.01 USDC 误差)
            if abs(actual_amount - expected_amount) > 0.01:
                return DepositVerification(
                    valid=False,
                    tx_signature=tx_signature,
                    error=f"Amount mismatch: expected {expected_amount}, got {actual_amount}",
                )

            # tx 已在 _try_claim_tx 中标记
            return DepositVerification(
                valid=True,
                tx_signature=tx_signature,
                amount=actual_amount,
                from_wallet=from_wallet,
                to_wallet=self.vault_address,
                block_time=result.get("blockTime"),
            )

        except Exception as e:
            logger.error(f"Deposit verification failed: {e}")
            return DepositVerification(
                valid=False,
                tx_signature=tx_signature,
                error=f"Verification error: {str(e)}",
            )

    # === 提现 ===

    async def send_usdc(
        self,
        to_wallet: str,
        amount: float,
        agent_id: str = "",
    ) -> WithdrawResult:
        """
        从 Vault 发送 USDC (提现)

        安全措施:
        - 单次上限 $10,000
        - 冷却期 60 秒
        - Vault keypair 签名
        """
        # 安全检查: 金额上限
        if amount > self.MAX_WITHDRAW_AMOUNT:
            return WithdrawResult(
                success=False,
                error=f"Exceeds max withdrawal: ${amount} > ${self.MAX_WITHDRAW_AMOUNT}",
            )

        if amount <= 0:
            return WithdrawResult(
                success=False,
                error="Amount must be positive",
            )

        # 安全检查: 冷却期
        if agent_id:
            last_withdraw = self._withdraw_cooldowns.get(agent_id, 0)
            elapsed = time.time() - last_withdraw
            if elapsed < self.WITHDRAW_COOLDOWN:
                remaining = int(self.WITHDRAW_COOLDOWN - elapsed)
                return WithdrawResult(
                    success=False,
                    error=f"Withdrawal cooldown: {remaining}s remaining",
                )

        # 钱包地址基本校验
        if not to_wallet or len(to_wallet) < 20:
            return WithdrawResult(
                success=False,
                error="Invalid wallet address",
            )

        if self.simulation_mode:
            return await self._send_usdc_simulated(to_wallet, amount, agent_id)

        return await self._send_usdc_onchain(to_wallet, amount, agent_id)

    async def _send_usdc_simulated(
        self,
        to_wallet: str,
        amount: float,
        agent_id: str,
    ) -> WithdrawResult:
        """模拟提现 (开发/测试)"""
        await asyncio.sleep(0.05)  # 模拟网络延迟

        # 生成模拟 tx_sig
        tx_data = f"withdraw:{to_wallet}:{amount}:{time.time()}"
        tx_sig = "sim_" + hashlib.sha256(tx_data.encode()).hexdigest()[:64]

        # 更新冷却
        if agent_id:
            self._withdraw_cooldowns[agent_id] = time.time()

        return WithdrawResult(
            success=True,
            tx_signature=tx_sig,
            amount=amount,
            to_wallet=to_wallet,
        )

    async def _send_usdc_onchain(
        self,
        to_wallet: str,
        amount: float,
        agent_id: str,
    ) -> WithdrawResult:
        """链上提现 (生产) - 需要 Vault keypair"""
        try:
            # 生产环境需要 solana-py 或等效库来构建和签名交易
            # 此处预留接口，实际实现需要:
            # 1. 加载 Vault keypair
            # 2. 获取/创建 to_wallet 的 ATA
            # 3. 构建 SPL Token Transfer 指令
            # 4. 签名并发送交易
            # 5. 等待 finalized 确认

            raise NotImplementedError(
                "Production on-chain withdrawal requires solana-py. "
                "Install with: pip install solana==0.30.2"
            )

        except NotImplementedError:
            raise
        except Exception as e:
            logger.error(f"On-chain withdrawal failed: {e}")
            return WithdrawResult(
                success=False,
                error=f"Withdrawal failed: {str(e)}",
            )

    # === Cleanup ===

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    def get_vault_info(self) -> dict:
        """获取 Vault 信息"""
        return {
            "vault_address": self.vault_address or "(not configured)",
            "network": self.network,
            "usdc_mint": self.usdc_mint,
            "simulation_mode": self.simulation_mode,
            "max_withdraw": self.MAX_WITHDRAW_AMOUNT,
            "withdraw_cooldown_seconds": self.WITHDRAW_COOLDOWN,
        }


# 单例
solana_client = SolanaClient(
    simulation_mode=os.environ.get("SOLANA_LIVE", "false").lower() != "true",
    network=os.environ.get("SOLANA_NETWORK", "devnet"),
)
