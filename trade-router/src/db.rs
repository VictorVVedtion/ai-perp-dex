//! SQLite persistence layer

use rusqlite::{Connection, params};
use std::sync::Mutex;
use uuid::Uuid;
use chrono::{DateTime, Utc};

use crate::types::{AgentInfo, AgentStats, Market, Position, PositionStatus, PositionWithPnl, Side};
use crate::funding::{FundingPayment, FundingSummary};

pub struct Database {
    conn: Mutex<Connection>,
}

impl Database {
    pub fn new(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
        let db = Self { conn: Mutex::new(conn) };
        db.init_tables()?;
        Ok(db)
    }
    
    pub fn in_memory() -> rusqlite::Result<Self> {
        Self::new(":memory:")
    }
    
    fn init_tables(&self) -> rusqlite::Result<()> {
        let conn = self.conn.lock().unwrap();
        
        conn.execute_batch(r#"
            -- Agents table
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                name TEXT,
                is_mm INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            
            -- Positions table
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                quote_id TEXT NOT NULL,
                trader_agent TEXT NOT NULL,
                mm_agent TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                size_usdc REAL NOT NULL,
                leverage INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                funding_rate REAL NOT NULL,
                trader_collateral REAL NOT NULL,
                mm_collateral REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                closed_at TEXT,
                pnl_trader REAL,
                pnl_mm REAL
            );
            
            -- Trades table (history)
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                position_id TEXT NOT NULL,
                trader_agent TEXT NOT NULL,
                mm_agent TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                size_usdc REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                pnl_trader REAL,
                pnl_mm REAL,
                created_at TEXT NOT NULL,
                closed_at TEXT
            );
            
            -- Funding payments table
            CREATE TABLE IF NOT EXISTS funding_payments (
                id TEXT PRIMARY KEY,
                position_id TEXT NOT NULL,
                trader_agent TEXT NOT NULL,
                mm_agent TEXT NOT NULL,
                funding_rate REAL NOT NULL,
                position_size REAL NOT NULL,
                payment_amount REAL NOT NULL,
                settled_at TEXT NOT NULL
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_positions_trader ON positions(trader_agent);
            CREATE INDEX IF NOT EXISTS idx_positions_mm ON positions(mm_agent);
            CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
            CREATE INDEX IF NOT EXISTS idx_agents_api_key ON agents(api_key);
            CREATE INDEX IF NOT EXISTS idx_funding_trader ON funding_payments(trader_agent);
            CREATE INDEX IF NOT EXISTS idx_funding_mm ON funding_payments(mm_agent);
            CREATE INDEX IF NOT EXISTS idx_funding_settled ON funding_payments(settled_at);
        "#)?;
        
        Ok(())
    }
    
    // ========== Agent Operations ==========
    
    pub fn save_agent(&self, agent: &AgentInfo) -> rusqlite::Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO agents (id, api_key, name, is_mm, created_at) VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                agent.id,
                agent.api_key,
                agent.name,
                agent.is_mm as i32,
                agent.created_at.to_rfc3339(),
            ],
        )?;
        Ok(())
    }
    
    pub fn get_agent_by_api_key(&self, api_key: &str) -> rusqlite::Result<Option<AgentInfo>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, api_key, name, is_mm, created_at FROM agents WHERE api_key = ?1")?;
        
        let mut rows = stmt.query(params![api_key])?;
        if let Some(row) = rows.next()? {
            Ok(Some(AgentInfo {
                id: row.get(0)?,
                api_key: row.get(1)?,
                name: row.get(2)?,
                is_mm: row.get::<_, i32>(3)? != 0,
                created_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(4)?)
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(|_| Utc::now()),
            }))
        } else {
            Ok(None)
        }
    }
    
    pub fn get_agent(&self, agent_id: &str) -> rusqlite::Result<Option<AgentInfo>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, api_key, name, is_mm, created_at FROM agents WHERE id = ?1")?;
        
        let mut rows = stmt.query(params![agent_id])?;
        if let Some(row) = rows.next()? {
            Ok(Some(AgentInfo {
                id: row.get(0)?,
                api_key: row.get(1)?,
                name: row.get(2)?,
                is_mm: row.get::<_, i32>(3)? != 0,
                created_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(4)?)
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(|_| Utc::now()),
            }))
        } else {
            Ok(None)
        }
    }
    
    // ========== Position Operations ==========
    
    pub fn save_position(&self, pos: &Position) -> rusqlite::Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            r#"INSERT OR REPLACE INTO positions 
               (id, request_id, quote_id, trader_agent, mm_agent, market, side, 
                size_usdc, leverage, entry_price, funding_rate, trader_collateral, 
                mm_collateral, status, created_at, closed_at)
               VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)"#,
            params![
                pos.id.to_string(),
                pos.request_id.to_string(),
                pos.quote_id.to_string(),
                pos.trader_agent,
                pos.mm_agent,
                format!("{:?}", pos.market),
                format!("{:?}", pos.side),
                pos.size_usdc,
                pos.leverage,
                pos.entry_price,
                pos.funding_rate,
                pos.trader_collateral,
                pos.mm_collateral,
                format!("{:?}", pos.status),
                pos.created_at.to_rfc3339(),
                pos.closed_at.map(|dt| dt.to_rfc3339()),
            ],
        )?;
        Ok(())
    }
    
    pub fn get_positions_by_agent(&self, agent_id: &str) -> rusqlite::Result<Vec<Position>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT * FROM positions WHERE (trader_agent = ?1 OR mm_agent = ?1) AND status = 'Active'"
        )?;
        
        let mut positions = Vec::new();
        let mut rows = stmt.query(params![agent_id])?;
        
        while let Some(row) = rows.next()? {
            if let Ok(pos) = self.row_to_position(row) {
                positions.push(pos);
            }
        }
        
        Ok(positions)
    }
    
    /// 查询历史仓位 (已平仓)，支持分页
    pub fn get_closed_positions_by_agent(
        &self, 
        agent_id: &str, 
        limit: u32, 
        offset: u32
    ) -> rusqlite::Result<(Vec<PositionWithPnl>, u32)> {
        let conn = self.conn.lock().unwrap();
        
        // 获取总数
        let total: u32 = conn.query_row(
            "SELECT COUNT(*) FROM positions WHERE (trader_agent = ?1 OR mm_agent = ?1) AND status = 'Closed'",
            params![agent_id],
            |row| row.get(0),
        )?;
        
        // 查询分页数据
        let mut stmt = conn.prepare(
            "SELECT * FROM positions 
             WHERE (trader_agent = ?1 OR mm_agent = ?1) AND status = 'Closed'
             ORDER BY closed_at DESC
             LIMIT ?2 OFFSET ?3"
        )?;
        
        let mut positions = Vec::new();
        let mut rows = stmt.query(params![agent_id, limit, offset])?;
        
        while let Some(row) = rows.next()? {
            if let Ok(pos) = self.row_to_position(row) {
                // 读取 PnL 字段
                let pnl_trader: Option<f64> = row.get(16).ok();
                let pnl_mm: Option<f64> = row.get(17).ok();
                
                positions.push(PositionWithPnl {
                    position: pos,
                    pnl_trader,
                    pnl_mm,
                });
            }
        }
        
        Ok((positions, total))
    }
    
    pub fn close_position(&self, position_id: &Uuid, pnl_trader: f64, pnl_mm: f64) -> rusqlite::Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE positions SET status = 'Closed', closed_at = ?1, pnl_trader = ?2, pnl_mm = ?3 WHERE id = ?4",
            params![
                Utc::now().to_rfc3339(),
                pnl_trader,
                pnl_mm,
                position_id.to_string(),
            ],
        )?;
        Ok(())
    }
    
    /// 获取 Agent 交易统计 (从 positions 表聚合)
    pub fn get_agent_stats(&self, agent_id: &str) -> rusqlite::Result<AgentStats> {
        let conn = self.conn.lock().unwrap();
        
        // 查询该 agent 作为 trader 的已平仓仓位统计
        let (total_trades, wins, losses, total_pnl, total_volume): (u32, u32, u32, f64, f64) = conn.query_row(
            r#"SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl_trader > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl_trader <= 0 THEN 1 ELSE 0 END) as losses,
                COALESCE(SUM(pnl_trader), 0) as total_pnl,
                COALESCE(SUM(size_usdc), 0) as total_volume
            FROM positions 
            WHERE trader_agent = ?1 AND status = 'Closed'"#,
            params![agent_id],
            |row| Ok((
                row.get::<_, u32>(0)?,
                row.get::<_, u32>(1)?,
                row.get::<_, u32>(2)?,
                row.get::<_, f64>(3)?,
                row.get::<_, f64>(4)?,
            )),
        )?;
        
        let win_rate = if total_trades > 0 {
            wins as f64 / total_trades as f64
        } else {
            0.0
        };
        
        let avg_pnl = if total_trades > 0 {
            total_pnl / total_trades as f64
        } else {
            0.0
        };
        
        Ok(AgentStats {
            agent_id: agent_id.to_string(),
            total_trades,
            wins,
            losses,
            win_rate,
            total_pnl,
            avg_pnl,
            total_volume,
        })
    }
    
    // ========== Funding Operations ==========
    
    pub fn save_funding_payment(&self, payment: &FundingPayment) -> rusqlite::Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            r#"INSERT INTO funding_payments 
               (id, position_id, trader_agent, mm_agent, funding_rate, position_size, payment_amount, settled_at)
               VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)"#,
            params![
                payment.id.to_string(),
                payment.position_id.to_string(),
                payment.trader_agent,
                payment.mm_agent,
                payment.funding_rate,
                payment.position_size,
                payment.payment_amount,
                payment.settled_at.to_rfc3339(),
            ],
        )?;
        Ok(())
    }
    
    pub fn get_funding_payments(&self, agent_id: &str, limit: u32) -> rusqlite::Result<Vec<FundingPayment>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            r#"SELECT id, position_id, trader_agent, mm_agent, funding_rate, position_size, payment_amount, settled_at
               FROM funding_payments 
               WHERE trader_agent = ?1 OR mm_agent = ?1
               ORDER BY settled_at DESC
               LIMIT ?2"#
        )?;
        
        let mut payments = Vec::new();
        let mut rows = stmt.query(params![agent_id, limit])?;
        
        while let Some(row) = rows.next()? {
            payments.push(FundingPayment {
                id: Uuid::parse_str(&row.get::<_, String>(0)?).unwrap_or_default(),
                position_id: Uuid::parse_str(&row.get::<_, String>(1)?).unwrap_or_default(),
                trader_agent: row.get(2)?,
                mm_agent: row.get(3)?,
                funding_rate: row.get(4)?,
                position_size: row.get(5)?,
                payment_amount: row.get(6)?,
                settled_at: chrono::DateTime::parse_from_rfc3339(&row.get::<_, String>(7)?)
                    .map(|dt| dt.with_timezone(&Utc))
                    .unwrap_or_else(|_| Utc::now()),
            });
        }
        
        Ok(payments)
    }
    
    pub fn get_funding_summary(&self, agent_id: &str) -> rusqlite::Result<FundingSummary> {
        let conn = self.conn.lock().unwrap();
        
        // Total paid as trader
        let total_paid: f64 = conn.query_row(
            "SELECT COALESCE(SUM(payment_amount), 0) FROM funding_payments WHERE trader_agent = ?1",
            params![agent_id],
            |row| row.get(0),
        )?;
        
        // Total received as MM
        let total_received: f64 = conn.query_row(
            "SELECT COALESCE(SUM(payment_amount), 0) FROM funding_payments WHERE mm_agent = ?1",
            params![agent_id],
            |row| row.get(0),
        )?;
        
        // Payment count
        let payment_count: u32 = conn.query_row(
            "SELECT COUNT(*) FROM funding_payments WHERE trader_agent = ?1 OR mm_agent = ?1",
            params![agent_id],
            |row| row.get(0),
        )?;
        
        Ok(FundingSummary {
            agent_id: agent_id.to_string(),
            total_paid,
            total_received,
            net: total_received - total_paid,
            payment_count,
        })
    }
    
    fn row_to_position(&self, row: &rusqlite::Row) -> rusqlite::Result<Position> {
        Ok(Position {
            id: Uuid::parse_str(&row.get::<_, String>(0)?).unwrap_or_default(),
            request_id: Uuid::parse_str(&row.get::<_, String>(1)?).unwrap_or_default(),
            quote_id: Uuid::parse_str(&row.get::<_, String>(2)?).unwrap_or_default(),
            trader_agent: row.get(3)?,
            mm_agent: row.get(4)?,
            market: parse_market(&row.get::<_, String>(5)?),
            side: parse_side(&row.get::<_, String>(6)?),
            size_usdc: row.get(7)?,
            leverage: row.get(8)?,
            entry_price: row.get(9)?,
            funding_rate: row.get(10)?,
            trader_collateral: row.get(11)?,
            mm_collateral: row.get(12)?,
            status: parse_status(&row.get::<_, String>(13)?),
            created_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(14)?)
                .map(|dt| dt.with_timezone(&Utc))
                .unwrap_or_else(|_| Utc::now()),
            closed_at: row.get::<_, Option<String>>(15)?
                .and_then(|s| DateTime::parse_from_rfc3339(&s).ok())
                .map(|dt| dt.with_timezone(&Utc)),
        })
    }
}

fn parse_market(s: &str) -> Market {
    match s {
        "BtcPerp" | "BTC-PERP" => Market::BtcPerp,
        "EthPerp" | "ETH-PERP" => Market::EthPerp,
        "SolPerp" | "SOL-PERP" => Market::SolPerp,
        "DogePerp" | "DOGE-PERP" => Market::DogePerp,
        "AvaxPerp" | "AVAX-PERP" => Market::AvaxPerp,
        "LinkPerp" | "LINK-PERP" => Market::LinkPerp,
        _ => Market::BtcPerp,
    }
}

fn parse_side(s: &str) -> Side {
    match s.to_lowercase().as_str() {
        "long" => Side::Long,
        "short" => Side::Short,
        _ => Side::Long,
    }
}

fn parse_status(s: &str) -> PositionStatus {
    match s {
        "Active" => PositionStatus::Active,
        "Closed" => PositionStatus::Closed,
        "Liquidated" => PositionStatus::Liquidated,
        _ => PositionStatus::Pending,
    }
}
