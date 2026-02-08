"""
SQLite Database for AI Perp DEX
Persistent storage for agents, positions, signals, etc.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json

DB_PATH = os.environ.get("PERP_DEX_DB", "perp_dex.db")


def get_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Agents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            wallet_address TEXT UNIQUE NOT NULL,
            description TEXT,
            api_key_hash TEXT,
            balance REAL DEFAULT 0.0,
            locked_balance REAL DEFAULT 0.0,
            total_deposited REAL DEFAULT 0.0,
            total_withdrawn REAL DEFAULT 0.0,
            total_trades INTEGER DEFAULT 0,
            total_volume REAL DEFAULT 0.0,
            pnl REAL DEFAULT 0.0,
            reputation_score REAL DEFAULT 0.5,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # API Keys table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT DEFAULT 'default',
            scopes TEXT DEFAULT '["read","write"]',
            is_active INTEGER DEFAULT 1,
            last_used TIMESTAMP,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)
    
    # Positions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            position_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            asset TEXT NOT NULL,
            side TEXT NOT NULL,
            size_usdc REAL NOT NULL,
            entry_price REAL NOT NULL,
            leverage INTEGER DEFAULT 1,
            liquidation_price REAL,
            stop_loss REAL,
            take_profit REAL,
            is_open INTEGER DEFAULT 1,
            close_price REAL,
            realized_pnl REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)
    
    # Signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            asset TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            target_value REAL NOT NULL,
            confidence REAL DEFAULT 0.5,
            stake_amount REAL NOT NULL,
            rationale TEXT,
            status TEXT DEFAULT 'open',
            outcome TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            settled_at TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)
    
    # Bets table (Signal Fades)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            bet_id TEXT PRIMARY KEY,
            signal_id TEXT NOT NULL,
            fader_id TEXT NOT NULL,
            stake REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            pnl REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            settled_at TIMESTAMP,
            FOREIGN KEY (signal_id) REFERENCES signals(signal_id),
            FOREIGN KEY (fader_id) REFERENCES agents(agent_id)
        )
    """)
    
    # Transactions table (deposits, withdrawals, fees)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_after REAL,
            reference_id TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        )
    """)
    
    # Trades table (execution history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            position_id TEXT,
            asset TEXT NOT NULL,
            side TEXT NOT NULL,
            size_usdc REAL NOT NULL,
            price REAL NOT NULL,
            fee REAL DEFAULT 0.0,
            venue TEXT DEFAULT 'internal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
            FOREIGN KEY (position_id) REFERENCES positions(position_id)
        )
    """)
    
    # === Vault 表 ===

    # Vault 主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vaults (
            vault_id TEXT PRIMARY KEY,
            manager_agent_id TEXT NOT NULL,
            vault_agent_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            nav_per_share REAL NOT NULL DEFAULT 1.0,
            hwm_nav_per_share REAL NOT NULL DEFAULT 1.0,
            peak_nav_per_share REAL NOT NULL DEFAULT 1.0,
            total_shares REAL NOT NULL DEFAULT 0,
            manager_shares REAL NOT NULL DEFAULT 0,
            perf_fee_rate REAL NOT NULL DEFAULT 0.20,
            accrued_perf_fee_usdc REAL NOT NULL DEFAULT 0,
            paid_perf_fee_usdc REAL NOT NULL DEFAULT 0,
            drawdown_limit_pct REAL NOT NULL DEFAULT 0.30,
            tweet_verified INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 投资者份额
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_investors (
            vault_id TEXT NOT NULL,
            investor_agent_id TEXT NOT NULL,
            shares REAL NOT NULL DEFAULT 0,
            cost_basis_usdc REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (vault_id, investor_agent_id)
        )
    """)

    # 资金流水 (deposit/withdraw)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_flows (
            flow_id TEXT PRIMARY KEY,
            vault_id TEXT NOT NULL,
            investor_agent_id TEXT NOT NULL,
            flow_type TEXT NOT NULL CHECK(flow_type IN ('deposit','withdraw')),
            amount_usdc REAL NOT NULL,
            shares REAL NOT NULL,
            nav_per_share REAL NOT NULL,
            idempotency_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # NAV 快照 (净值曲线)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_nav_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vault_id TEXT NOT NULL,
            nav_per_share REAL NOT NULL,
            total_equity REAL NOT NULL,
            snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Agent 验证字段 (ALTER TABLE 兼容已有数据)
    try:
        cursor.execute("ALTER TABLE agents ADD COLUMN verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    try:
        cursor.execute("ALTER TABLE agents ADD COLUMN verification_nonce TEXT")
    except sqlite3.OperationalError:
        pass

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_agent ON positions(agent_id, is_open)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status, expires_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_signal ON bets(signal_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_agent ON transactions(agent_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_agent ON api_keys(agent_id)")

    # Vault indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vaults_manager ON vaults(manager_agent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_investors_agent ON vault_investors(investor_agent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_flows_vault ON vault_flows(vault_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_nav_vault ON vault_nav_snapshots(vault_id, snapshot_at)")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_vault_flows_idempo
        ON vault_flows(vault_id, investor_agent_id, flow_type, idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_PATH}")


class AgentDB:
    """Agent database operations"""
    
    @staticmethod
    def create(agent_id: str, display_name: str, wallet_address: str, 
               description: str = "", api_key_hash: str = "") -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO agents (agent_id, display_name, wallet_address, description, api_key_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, display_name, wallet_address, description, api_key_hash))
            conn.commit()
            return AgentDB.get(agent_id)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Agent already exists or wallet taken: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def get(agent_id: str) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_wallet(wallet_address: str) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE wallet_address = ?", (wallet_address,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def list_all(limit: int = 100) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents ORDER BY pnl DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_balance(agent_id: str, balance: float, locked: float = None) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        if locked is not None:
            cursor.execute("""
                UPDATE agents SET balance = ?, locked_balance = ?, updated_at = ?
                WHERE agent_id = ?
            """, (balance, locked, datetime.now(), agent_id))
        else:
            cursor.execute("""
                UPDATE agents SET balance = ?, updated_at = ?
                WHERE agent_id = ?
            """, (balance, datetime.now(), agent_id))
        conn.commit()
        conn.close()
        return AgentDB.get(agent_id)
    
    @staticmethod
    def update_stats(agent_id: str, trades: int = 0, volume: float = 0, pnl: float = 0):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agents SET 
                total_trades = total_trades + ?,
                total_volume = total_volume + ?,
                pnl = pnl + ?,
                updated_at = ?
            WHERE agent_id = ?
        """, (trades, volume, pnl, datetime.now(), agent_id))
        conn.commit()
        conn.close()


class PositionDB:
    """Position database operations"""
    
    @staticmethod
    def create(position_id: str, agent_id: str, asset: str, side: str,
               size_usdc: float, entry_price: float, leverage: int = 1,
               liquidation_price: float = None, stop_loss: float = None,
               take_profit: float = None) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO positions 
            (position_id, agent_id, asset, side, size_usdc, entry_price, 
             leverage, liquidation_price, stop_loss, take_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (position_id, agent_id, asset, side, size_usdc, entry_price,
              leverage, liquidation_price, stop_loss, take_profit))
        conn.commit()
        conn.close()
        return PositionDB.get(position_id)
    
    @staticmethod
    def get(position_id: str) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions WHERE position_id = ?", (position_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_open_by_agent(agent_id: str) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM positions 
            WHERE agent_id = ? AND is_open = 1
            ORDER BY created_at DESC
        """, (agent_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def close(position_id: str, close_price: float, realized_pnl: float) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE positions SET 
                is_open = 0, close_price = ?, realized_pnl = ?, closed_at = ?
            WHERE position_id = ?
        """, (close_price, realized_pnl, datetime.now(), position_id))
        conn.commit()
        conn.close()
        return PositionDB.get(position_id)
    
    @staticmethod
    def update_sl_tp(position_id: str, stop_loss: float = None, take_profit: float = None):
        conn = get_connection()
        cursor = conn.cursor()
        if stop_loss is not None:
            cursor.execute("UPDATE positions SET stop_loss = ? WHERE position_id = ?", 
                          (stop_loss, position_id))
        if take_profit is not None:
            cursor.execute("UPDATE positions SET take_profit = ? WHERE position_id = ?",
                          (take_profit, position_id))
        conn.commit()
        conn.close()


class SignalDB:
    """Signal database operations"""
    
    @staticmethod
    def create(signal_id: str, agent_id: str, asset: str, signal_type: str,
               target_value: float, stake_amount: float, confidence: float = 0.5,
               rationale: str = "", expires_at: datetime = None) -> Dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals 
            (signal_id, agent_id, asset, signal_type, target_value, stake_amount,
             confidence, rationale, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (signal_id, agent_id, asset, signal_type, target_value, stake_amount,
              confidence, rationale, expires_at))
        conn.commit()
        conn.close()
        return SignalDB.get(signal_id)
    
    @staticmethod
    def get(signal_id: str) -> Optional[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_open() -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM signals 
            WHERE status = 'open' AND expires_at > ?
            ORDER BY created_at DESC
        """, (datetime.now(),))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_status(signal_id: str, status: str, outcome: str = None):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE signals SET status = ?, outcome = ?, settled_at = ?
            WHERE signal_id = ?
        """, (status, outcome, datetime.now() if status == 'settled' else None, signal_id))
        conn.commit()
        conn.close()


class TransactionDB:
    """Transaction log operations"""
    
    @staticmethod
    def log(tx_id: str, agent_id: str, tx_type: str, amount: float,
            balance_after: float = None, reference_id: str = None,
            description: str = None):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions 
            (tx_id, agent_id, tx_type, amount, balance_after, reference_id, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tx_id, agent_id, tx_type, amount, balance_after, reference_id, description))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_agent(agent_id: str, limit: int = 100) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE agent_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (agent_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# Initialize on import
if __name__ == "__main__":
    init_db()
