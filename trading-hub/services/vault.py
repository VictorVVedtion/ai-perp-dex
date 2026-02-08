"""
Vault Service - AI Agent 委托资金管理

核心机制:
- 管理者 (Manager) 创建 Vault, 用合成账户 (vault_agent_id) 交易
- 投资者存入 USDC 获得份额, 按 NAV 赎回
- 绩效费: 20% 超额利润 (High Water Mark 机制)
- 回撤保护: -30% 自动暂停
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# === 精度工具 ===

_QUANT = Decimal("0.00000001")

def _d(v) -> Decimal:
    """转换为 Decimal"""
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v)).quantize(_QUANT, rounding=ROUND_DOWN)

def _f(d: Decimal) -> float:
    """Decimal -> float (JSON 序列化)"""
    return float(d)


# === 枚举 & 数据模型 ===

class VaultStatus(Enum):
    ACTIVE = "active"
    PAUSED_DRAWDOWN = "paused_drawdown"
    PAUSED_MANUAL = "paused_manual"
    CLOSED = "closed"


@dataclass
class Vault:
    vault_id: str
    manager_agent_id: str
    vault_agent_id: str          # 合成交易账户
    name: str
    status: VaultStatus = VaultStatus.ACTIVE
    nav_per_share: Decimal = _d(1)
    hwm_nav_per_share: Decimal = _d(1)
    peak_nav_per_share: Decimal = _d(1)
    total_shares: Decimal = _d(0)
    manager_shares: Decimal = _d(0)
    perf_fee_rate: Decimal = _d("0.20")
    accrued_perf_fee_usdc: Decimal = _d(0)
    paid_perf_fee_usdc: Decimal = _d(0)
    manager_min_share_ratio: Decimal = _d("0.10")
    drawdown_limit_pct: Decimal = _d("0.30")
    tweet_verified: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "vault_id": self.vault_id,
            "manager_agent_id": self.manager_agent_id,
            "vault_agent_id": self.vault_agent_id,
            "name": self.name,
            "status": self.status.value,
            "nav_per_share": _f(self.nav_per_share),
            "hwm_nav_per_share": _f(self.hwm_nav_per_share),
            "peak_nav_per_share": _f(self.peak_nav_per_share),
            "total_shares": _f(self.total_shares),
            "manager_shares": _f(self.manager_shares),
            "perf_fee_rate": _f(self.perf_fee_rate),
            "accrued_perf_fee_usdc": _f(self.accrued_perf_fee_usdc),
            "paid_perf_fee_usdc": _f(self.paid_perf_fee_usdc),
            "drawdown_limit_pct": _f(self.drawdown_limit_pct),
            "tweet_verified": self.tweet_verified,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class VaultInvestor:
    vault_id: str
    investor_agent_id: str
    shares: Decimal = _d(0)
    cost_basis_usdc: Decimal = _d(0)

    def to_dict(self) -> dict:
        return {
            "vault_id": self.vault_id,
            "investor_agent_id": self.investor_agent_id,
            "shares": _f(self.shares),
            "cost_basis_usdc": _f(self.cost_basis_usdc),
        }


@dataclass
class VaultFlow:
    flow_id: str
    vault_id: str
    investor_agent_id: str
    flow_type: str  # "deposit" | "withdraw"
    amount_usdc: Decimal
    shares: Decimal
    nav_per_share: Decimal
    idempotency_key: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "flow_id": self.flow_id,
            "vault_id": self.vault_id,
            "investor_agent_id": self.investor_agent_id,
            "flow_type": self.flow_type,
            "amount_usdc": _f(self.amount_usdc),
            "shares": _f(self.shares),
            "nav_per_share": _f(self.nav_per_share),
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
        }


# === Vault 服务 ===

class VaultService:
    """
    Vault 生命周期管理

    依赖注入:
    - settlement_engine: 资金转账
    - position_manager: 持仓查询 (NAV 计算)
    - price_feed: 价格查询 (NAV 计算)
    """

    def __init__(self):
        self.vaults: Dict[str, Vault] = {}
        self.investors: Dict[str, Dict[str, VaultInvestor]] = {}  # vault_id -> {agent_id -> investor}
        self.flows: List[VaultFlow] = []
        self.nav_snapshots: List[dict] = []

        # 依赖 (startup 时注入)
        self.settlement_engine = None
        self.position_manager = None
        self.price_feed = None

    def set_dependencies(self, settlement_engine, position_manager, price_feed=None):
        """注入依赖"""
        self.settlement_engine = settlement_engine
        self.position_manager = position_manager
        self.price_feed = price_feed

    # === 创建 ===

    def create_vault(
        self,
        manager_id: str,
        name: str,
        seed_amount_usdc: float,
        perf_fee_rate: float = 0.20,
        drawdown_limit_pct: float = 0.30,
    ) -> Vault:
        """
        创建 Vault + 合成账户 + 管理者首笔存款

        Raises:
            ValueError: 参数非法或余额不足
        """
        if not name or len(name.strip()) == 0:
            raise ValueError("Vault name is required")
        if seed_amount_usdc < 100:
            raise ValueError("Minimum seed amount is $100")
        if not (0 <= perf_fee_rate <= 0.50):
            raise ValueError("Performance fee rate must be 0-50%")

        # 检查管理者余额
        if self.settlement_engine:
            balance = self.settlement_engine.get_balance(manager_id)
            if balance.available < seed_amount_usdc:
                raise ValueError(
                    f"Insufficient balance: ${balance.available:.2f} < ${seed_amount_usdc:.2f}"
                )

        vault_id = f"vault_{uuid.uuid4().hex[:12]}"
        vault_agent_id = f"va_{uuid.uuid4().hex[:12]}"

        vault = Vault(
            vault_id=vault_id,
            manager_agent_id=manager_id,
            vault_agent_id=vault_agent_id,
            name=name.strip(),
            perf_fee_rate=_d(perf_fee_rate),
            drawdown_limit_pct=_d(drawdown_limit_pct),
        )
        self.vaults[vault_id] = vault
        self.investors[vault_id] = {}

        # 管理者种子存款 (从 manager -> vault_agent)
        if self.settlement_engine:
            self.settlement_engine.withdraw(manager_id, seed_amount_usdc)
            self.settlement_engine.deposit(vault_agent_id, seed_amount_usdc)

        # 分配份额 (NAV=1, shares=seed_amount)
        seed = _d(seed_amount_usdc)
        vault.total_shares = seed
        vault.manager_shares = seed

        investor = VaultInvestor(
            vault_id=vault_id,
            investor_agent_id=manager_id,
            shares=seed,
            cost_basis_usdc=seed,
        )
        self.investors[vault_id][manager_id] = investor

        # 记录 flow
        flow = VaultFlow(
            flow_id=f"flow_{uuid.uuid4().hex[:8]}",
            vault_id=vault_id,
            investor_agent_id=manager_id,
            flow_type="deposit",
            amount_usdc=seed,
            shares=seed,
            nav_per_share=_d(1),
        )
        self.flows.append(flow)

        logger.info(f"Vault created: {vault_id} by {manager_id}, seed=${seed_amount_usdc}")
        return vault

    # === 存入 ===

    def deposit(
        self,
        vault_id: str,
        investor_id: str,
        amount_usdc: float,
        idempotency_key: str = None,
    ) -> dict:
        """
        投资者存入 USDC

        Returns:
            {"vault": ..., "shares_received": ..., "nav_per_share": ..., "flow": ...}
        """
        vault = self._get_vault(vault_id)
        if vault.status != VaultStatus.ACTIVE:
            raise ValueError(f"Vault is {vault.status.value}, deposits not allowed")

        amount = _d(amount_usdc)
        if amount < _d(10):
            raise ValueError("Minimum deposit is $10")

        # 幂等检查
        if idempotency_key:
            for f in self.flows:
                if (f.vault_id == vault_id and f.investor_agent_id == investor_id
                        and f.flow_type == "deposit" and f.idempotency_key == idempotency_key):
                    return {
                        "vault": vault.to_dict(),
                        "shares_received": _f(f.shares),
                        "nav_per_share": _f(f.nav_per_share),
                        "flow": f.to_dict(),
                        "idempotent": True,
                    }

        # 刷新 NAV
        self._recompute_nav(vault)

        # 检查投资者余额
        if self.settlement_engine:
            balance = self.settlement_engine.get_balance(investor_id)
            if balance.available < amount_usdc:
                raise ValueError(f"Insufficient balance: ${balance.available:.2f}")

        # 计算份额: shares = amount / nav_per_share
        nav = vault.nav_per_share if vault.nav_per_share > _d(0) else _d(1)
        shares = (amount / nav).quantize(_QUANT, rounding=ROUND_DOWN)

        # 转账
        if self.settlement_engine:
            self.settlement_engine.withdraw(investor_id, amount_usdc)
            self.settlement_engine.deposit(vault.vault_agent_id, amount_usdc)

        # 更新 Vault
        vault.total_shares += shares

        # 更新投资者
        inv = self.investors[vault_id].get(investor_id)
        if inv:
            inv.shares += shares
            inv.cost_basis_usdc += amount
        else:
            inv = VaultInvestor(
                vault_id=vault_id,
                investor_agent_id=investor_id,
                shares=shares,
                cost_basis_usdc=amount,
            )
            self.investors[vault_id][investor_id] = inv

        # 记录 flow
        flow = VaultFlow(
            flow_id=f"flow_{uuid.uuid4().hex[:8]}",
            vault_id=vault_id,
            investor_agent_id=investor_id,
            flow_type="deposit",
            amount_usdc=amount,
            shares=shares,
            nav_per_share=nav,
            idempotency_key=idempotency_key,
        )
        self.flows.append(flow)

        return {
            "vault": vault.to_dict(),
            "shares_received": _f(shares),
            "nav_per_share": _f(nav),
            "flow": flow.to_dict(),
        }

    # === 提现 ===

    def withdraw(
        self,
        vault_id: str,
        investor_id: str,
        shares: float = None,
    ) -> dict:
        """
        投资者赎回份额

        Args:
            shares: 赎回份额数量 (None = 全部赎回)

        Returns:
            {"vault": ..., "amount_usdc": ..., "shares_redeemed": ..., "flow": ...}
        """
        vault = self._get_vault(vault_id)
        inv = self.investors.get(vault_id, {}).get(investor_id)
        if not inv or inv.shares <= _d(0):
            raise ValueError("No shares to withdraw")

        # 刷新 NAV
        self._recompute_nav(vault)

        shares_to_redeem = _d(shares) if shares else inv.shares
        if shares_to_redeem > inv.shares:
            raise ValueError(f"Insufficient shares: {_f(inv.shares)} < {_f(shares_to_redeem)}")

        # 管理者最小份额检查
        if investor_id == vault.manager_agent_id:
            remaining = inv.shares - shares_to_redeem
            min_shares = vault.total_shares * vault.manager_min_share_ratio
            if remaining < min_shares and remaining > _d(0):
                raise ValueError(
                    f"Manager must retain at least {_f(vault.manager_min_share_ratio * 100)}% of shares"
                )

        # 计算赎回金额
        nav = vault.nav_per_share if vault.nav_per_share > _d(0) else _d(1)
        amount = (shares_to_redeem * nav).quantize(_QUANT, rounding=ROUND_DOWN)

        # 检查 Vault 流动性 (vault_agent 余额)
        if self.settlement_engine:
            vault_balance = self.settlement_engine.get_balance(vault.vault_agent_id)
            if vault_balance.available < float(amount):
                raise ValueError(
                    f"Insufficient vault liquidity: ${vault_balance.available:.2f} "
                    f"< ${_f(amount):.2f}. Close positions first."
                )

        # 转账: vault_agent -> investor
        if self.settlement_engine:
            self.settlement_engine.withdraw(vault.vault_agent_id, float(amount))
            self.settlement_engine.deposit(investor_id, float(amount))

        # 更新
        vault.total_shares -= shares_to_redeem
        if investor_id == vault.manager_agent_id:
            vault.manager_shares -= shares_to_redeem
        inv.shares -= shares_to_redeem

        # 记录 flow
        flow = VaultFlow(
            flow_id=f"flow_{uuid.uuid4().hex[:8]}",
            vault_id=vault_id,
            investor_agent_id=investor_id,
            flow_type="withdraw",
            amount_usdc=amount,
            shares=shares_to_redeem,
            nav_per_share=nav,
        )
        self.flows.append(flow)

        return {
            "vault": vault.to_dict(),
            "amount_usdc": _f(amount),
            "shares_redeemed": _f(shares_to_redeem),
            "flow": flow.to_dict(),
        }

    # === NAV 计算 ===

    def _recompute_nav(self, vault: Vault):
        """
        刷新 NAV

        equity = cash + used_margin + unrealized_pnl - accrued_fee
        nav = equity / total_shares (shares=0 → nav=1)
        """
        if vault.total_shares <= _d(0):
            vault.nav_per_share = _d(1)
            return

        equity = self._compute_equity(vault)
        nav = (equity / vault.total_shares).quantize(_QUANT, rounding=ROUND_DOWN)
        vault.nav_per_share = nav

        # 绩效费计提
        self._crystallize_performance_fee(vault, nav)

        # 回撤检查
        self._check_drawdown(vault)

        # 更新 peak
        if nav > vault.peak_nav_per_share:
            vault.peak_nav_per_share = nav

        # 快照
        self.nav_snapshots.append({
            "vault_id": vault.vault_id,
            "nav_per_share": _f(nav),
            "total_equity": _f(equity),
            "snapshot_at": datetime.now().isoformat(),
        })

    def _compute_equity(self, vault: Vault) -> Decimal:
        """计算 Vault 总权益"""
        cash = _d(0)
        used_margin = _d(0)
        unrealized_pnl = _d(0)

        if self.settlement_engine:
            balance = self.settlement_engine.get_balance(vault.vault_agent_id)
            cash = _d(balance.balance_usdc)

        if self.position_manager:
            positions = self.position_manager.get_positions(vault.vault_agent_id, only_open=True)
            for pos in positions:
                # 更新价格
                if self.price_feed:
                    asset = pos.asset.replace("-PERP", "")
                    price = self.price_feed.get_price(asset)
                    if price:
                        pos.update_pnl(price)
                used_margin += _d(pos.size_usdc / pos.leverage)
                unrealized_pnl += _d(pos.unrealized_pnl)

        equity = cash + used_margin + unrealized_pnl - vault.accrued_perf_fee_usdc
        return max(equity, _d(0))

    # === 绩效费 ===

    def _crystallize_performance_fee(self, vault: Vault, nav_before_fee: Decimal):
        """
        计提绩效费 (两步法: 先 accrue, 后 claim)

        if nav_before_fee > hwm:
            profit = (nav_before_fee - hwm) * total_shares
            fee = profit * perf_fee_rate
            accrued_perf_fee += fee
            hwm = (equity - accrued_fee) / total_shares
        """
        if nav_before_fee <= vault.hwm_nav_per_share:
            return

        profit_per_share = nav_before_fee - vault.hwm_nav_per_share
        total_profit = profit_per_share * vault.total_shares
        fee = (total_profit * vault.perf_fee_rate).quantize(_QUANT, rounding=ROUND_DOWN)

        if fee > _d(0):
            vault.accrued_perf_fee_usdc += fee
            # 更新 HWM (扣费后的 NAV)
            equity = self._compute_equity(vault)
            if vault.total_shares > _d(0):
                vault.hwm_nav_per_share = (equity / vault.total_shares).quantize(
                    _QUANT, rounding=ROUND_DOWN
                )
            logger.info(f"Vault {vault.vault_id}: accrued fee ${_f(fee)}, HWM={_f(vault.hwm_nav_per_share)}")

    def claim_performance_fee(self, vault_id: str, manager_id: str) -> dict:
        """
        管理者提取已计提的绩效费

        Returns:
            {"claimed_usdc": float, "vault": dict}
        """
        vault = self._get_vault(vault_id)
        if vault.manager_agent_id != manager_id:
            raise ValueError("Only vault manager can claim fees")

        amount = vault.accrued_perf_fee_usdc
        if amount <= _d(0):
            raise ValueError("No accrued fees to claim")

        # 转账: vault_agent -> manager
        if self.settlement_engine:
            vault_balance = self.settlement_engine.get_balance(vault.vault_agent_id)
            if vault_balance.available < float(amount):
                raise ValueError(f"Insufficient vault liquidity for fee claim")
            self.settlement_engine.withdraw(vault.vault_agent_id, float(amount))
            self.settlement_engine.deposit(manager_id, float(amount))

        vault.paid_perf_fee_usdc += amount
        vault.accrued_perf_fee_usdc = _d(0)

        return {
            "claimed_usdc": _f(amount),
            "vault": vault.to_dict(),
        }

    # === 回撤保护 ===

    def _check_drawdown(self, vault: Vault):
        """(peak - current) / peak > limit → 自动暂停"""
        if vault.status != VaultStatus.ACTIVE:
            return
        if vault.peak_nav_per_share <= _d(0):
            return

        drawdown = (vault.peak_nav_per_share - vault.nav_per_share) / vault.peak_nav_per_share
        if drawdown > vault.drawdown_limit_pct:
            vault.status = VaultStatus.PAUSED_DRAWDOWN
            logger.warning(
                f"Vault {vault.vault_id} PAUSED: drawdown {_f(drawdown * 100):.1f}% "
                f"> limit {_f(vault.drawdown_limit_pct * 100):.0f}%"
            )

    # === 交易前检查 ===

    def pre_trade_check(self, vault_agent_id: str) -> bool:
        """检查 vault 是否允许交易 (暂停状态禁止新开仓)"""
        for vault in self.vaults.values():
            if vault.vault_agent_id == vault_agent_id:
                if vault.status != VaultStatus.ACTIVE:
                    raise ValueError(
                        f"Vault {vault.vault_id} is {vault.status.value}: new trades blocked"
                    )
                return True
        return True  # 非 vault 账户不受限

    # === 平仓回调 ===

    def on_position_close(self, vault_agent_id: str, position_id: str, pnl: float):
        """平仓后刷新 NAV + 检查回撤"""
        for vault in self.vaults.values():
            if vault.vault_agent_id == vault_agent_id:
                self._recompute_nav(vault)
                break

    # === 查询 ===

    def get_vault(self, vault_id: str) -> Optional[Vault]:
        return self.vaults.get(vault_id)

    def _get_vault(self, vault_id: str) -> Vault:
        vault = self.vaults.get(vault_id)
        if not vault:
            raise ValueError(f"Vault not found: {vault_id}")
        return vault

    def list_vaults(self) -> List[Vault]:
        return list(self.vaults.values())

    def get_investors(self, vault_id: str) -> List[VaultInvestor]:
        return list(self.investors.get(vault_id, {}).values())

    def get_my_vaults(self, agent_id: str) -> List[dict]:
        """查询某个 agent 参与的所有 Vault"""
        results = []
        for vault_id, inv_map in self.investors.items():
            if agent_id in inv_map:
                vault = self.vaults.get(vault_id)
                if vault:
                    inv = inv_map[agent_id]
                    results.append({
                        "vault": vault.to_dict(),
                        "my_shares": _f(inv.shares),
                        "my_value_usdc": _f(inv.shares * vault.nav_per_share),
                        "is_manager": vault.manager_agent_id == agent_id,
                    })
        return results

    def get_performance(self, vault_id: str) -> List[dict]:
        """获取 NAV 曲线"""
        return [s for s in self.nav_snapshots if s["vault_id"] == vault_id]

    def get_vault_with_details(self, vault_id: str) -> dict:
        """Vault 详情 (含 NAV、持仓、投资者)"""
        vault = self._get_vault(vault_id)
        self._recompute_nav(vault)

        positions = []
        if self.position_manager:
            positions = [
                p.to_dict()
                for p in self.position_manager.get_positions(vault.vault_agent_id, only_open=True)
            ]

        investors = [inv.to_dict() for inv in self.get_investors(vault_id)]

        return {
            **vault.to_dict(),
            "positions": positions,
            "investors": investors,
            "total_equity_usdc": _f(self._compute_equity(vault)),
        }


# 单例
vault_service = VaultService()
