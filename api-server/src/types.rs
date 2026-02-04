//! API Types
//! 
//! All request/response types for AI Perp DEX API.

use serde::{Deserialize, Serialize};

// ==================== Common ====================

#[derive(Debug, Serialize)]
pub struct ApiResponse {
    pub success: bool,
    pub message: String,
}

#[derive(Debug, Serialize)]
pub struct WithdrawResponse {
    pub success: bool,
    pub tx_signature: Option<String>,
    pub message: String,
}

// ==================== Agent ====================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskParams {
    pub max_leverage: u8,
    pub max_position_size_usd: f64,
    pub max_daily_loss_usd: f64,
    pub max_positions: u8,
    pub circuit_breaker_enabled: bool,
    pub circuit_breaker_loss_pct: f64,
}

impl Default for RiskParams {
    fn default() -> Self {
        Self {
            max_leverage: 10,
            max_position_size_usd: 10000.0,
            max_daily_loss_usd: 1000.0,
            max_positions: 10,
            circuit_breaker_enabled: true,
            circuit_breaker_loss_pct: 50.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AgentStats {
    pub total_trades: u64,
    pub total_volume_usd: f64,
    pub total_pnl_usd: f64,
    pub win_rate: f64,
    pub avg_leverage: f64,
    pub max_drawdown: f64,
}

#[derive(Debug, Serialize)]
pub struct AgentInfo {
    pub agent_id: String,
    pub pubkey: String,
    pub name: String,
    pub created_at: i64,
    pub risk_params: RiskParams,
    pub stats: AgentStats,
}

// ==================== Orders ====================

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OrderSide {
    Long,
    Short,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OrderType {
    Market,
    Limit,
    Stop,
    StopLimit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OrderStatus {
    Pending,
    Open,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
    Expired,
}

#[derive(Debug, Serialize)]
pub struct Order {
    pub order_id: String,
    pub client_order_id: Option<String>,
    pub agent_id: String,
    pub market: String,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub size_usd: f64,
    pub filled_size_usd: f64,
    pub price: Option<f64>,
    pub avg_fill_price: Option<f64>,
    pub leverage: u8,
    pub stop_price: Option<f64>,
    pub take_profit: Option<f64>,
    pub stop_loss: Option<f64>,
    pub status: OrderStatus,
    pub created_at: i64,
    pub updated_at: i64,
}

// ==================== Positions ====================

#[derive(Debug, Serialize)]
pub struct Position {
    pub position_id: String,
    pub agent_id: String,
    pub market: String,
    pub side: OrderSide,
    pub size: f64,
    pub size_usd: f64,
    pub entry_price: f64,
    pub mark_price: f64,
    pub liquidation_price: f64,
    pub margin: f64,
    pub leverage: u8,
    pub unrealized_pnl: f64,
    pub unrealized_pnl_pct: f64,
    pub realized_pnl: f64,
    pub take_profit: Option<f64>,
    pub stop_loss: Option<f64>,
    pub opened_at: i64,
    pub updated_at: i64,
}

// ==================== Market Data ====================

#[derive(Debug, Serialize)]
pub struct Market {
    pub symbol: String,
    pub index: u8,
    pub base_asset: String,
    pub quote_asset: String,
    pub price: f64,
    pub index_price: f64,
    pub mark_price: f64,
    pub funding_rate: f64,
    pub next_funding_time: i64,
    pub open_interest: f64,
    pub volume_24h: f64,
    pub max_leverage: u8,
    pub min_size: f64,
    pub tick_size: f64,
}

#[derive(Debug, Serialize)]
pub struct PriceResponse {
    pub market: String,
    pub price: f64,
    pub index_price: f64,
    pub mark_price: f64,
    pub timestamp: i64,
}

#[derive(Debug, Serialize)]
pub struct OrderbookLevel {
    pub price: f64,
    pub size: f64,
}

#[derive(Debug, Serialize)]
pub struct Orderbook {
    pub market: String,
    pub bids: Vec<OrderbookLevel>,
    pub asks: Vec<OrderbookLevel>,
    pub timestamp: i64,
}

#[derive(Debug, Serialize)]
pub struct Trade {
    pub trade_id: String,
    pub market: String,
    pub side: OrderSide,
    pub price: f64,
    pub size: f64,
    pub timestamp: i64,
}

// ==================== Account ====================

#[derive(Debug, Serialize)]
pub struct Account {
    pub agent_id: String,
    pub pubkey: String,
    pub collateral: f64,
    pub available_margin: f64,
    pub used_margin: f64,
    pub total_position_value: f64,
    pub unrealized_pnl: f64,
    pub realized_pnl: f64,
    pub total_volume: f64,
    pub total_trades: u64,
}

#[derive(Debug, Serialize)]
pub struct TradeHistory {
    pub trade_id: String,
    pub order_id: String,
    pub market: String,
    pub side: OrderSide,
    pub price: f64,
    pub size_usd: f64,
    pub fee: f64,
    pub pnl: f64,
    pub timestamp: i64,
}
