use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// 交易市场
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Market {
    #[serde(rename = "BTC-PERP")]
    BtcPerp,
    #[serde(rename = "ETH-PERP")]
    EthPerp,
    #[serde(rename = "SOL-PERP")]
    SolPerp,
}

/// 交易方向
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Side {
    Long,
    Short,
}

/// 交易请求 - Agent A 发起
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeRequest {
    pub id: Uuid,
    pub agent_id: String,
    pub market: Market,
    pub side: Side,
    pub size_usdc: f64,
    pub leverage: u8,
    pub max_funding_rate: f64,
    pub expires_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
}

/// 创建交易请求的输入
#[derive(Debug, Deserialize)]
pub struct CreateTradeRequest {
    pub agent_id: String,
    pub market: Market,
    pub side: Side,
    pub size_usdc: f64,
    pub leverage: u8,
    pub max_funding_rate: f64,
    pub expires_in: u64, // 秒
}

/// 报价 - MM Agent 响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Quote {
    pub id: Uuid,
    pub request_id: Uuid,
    pub agent_id: String,
    pub funding_rate: f64,
    pub collateral_usdc: f64,
    pub valid_until: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
}

/// 创建报价的输入
#[derive(Debug, Deserialize)]
pub struct CreateQuote {
    pub request_id: Uuid,
    pub agent_id: String,
    pub funding_rate: f64,
    pub collateral_usdc: f64,
    pub valid_for: u64, // 秒
}

/// 接受报价
#[derive(Debug, Deserialize)]
pub struct AcceptQuote {
    pub request_id: Uuid,
    pub quote_id: Uuid,
    pub signature: String,
}

/// 仓位状态
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum PositionStatus {
    Pending,   // 等待链上确认
    Active,    // 活跃
    Closing,   // 正在平仓
    Closed,    // 已平仓
    Liquidated, // 已清算
}

/// 仓位
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub id: Uuid,
    pub request_id: Uuid,
    pub quote_id: Uuid,
    pub trader_agent: String,    // 交易方
    pub mm_agent: String,        // 做市商
    pub market: Market,
    pub side: Side,              // trader 的方向
    pub size_usdc: f64,
    pub leverage: u8,
    pub entry_price: f64,
    pub funding_rate: f64,
    pub trader_collateral: f64,
    pub mm_collateral: f64,
    pub status: PositionStatus,
    pub created_at: DateTime<Utc>,
    pub closed_at: Option<DateTime<Utc>>,
}

/// 平仓请求
#[derive(Debug, Deserialize)]
pub struct ClosePosition {
    pub position_id: Uuid,
    pub agent_id: String,
    pub size_percent: u8, // 1-100
}

/// WebSocket 消息类型
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "data")]
pub enum WsMessage {
    // Server -> Client
    #[serde(rename = "trade_request")]
    TradeRequest(TradeRequest),
    #[serde(rename = "quote_accepted")]
    QuoteAccepted { request_id: Uuid, quote_id: Uuid, position_id: Uuid },
    #[serde(rename = "position_opened")]
    PositionOpened(Position),
    #[serde(rename = "position_closed")]
    PositionClosed { position_id: Uuid, pnl_trader: f64, pnl_mm: f64 },
    #[serde(rename = "liquidation")]
    Liquidation { position_id: Uuid, liquidated_agent: String },
    #[serde(rename = "error")]
    Error { message: String },
    
    // Client -> Server
    #[serde(rename = "subscribe")]
    Subscribe { markets: Vec<Market> },
    #[serde(rename = "unsubscribe")]
    Unsubscribe { markets: Vec<Market> },
}

/// 市场信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketInfo {
    pub market: Market,
    pub current_price: f64,
    pub funding_rate_24h: f64,
    pub open_interest: f64,
    pub volume_24h: f64,
}

/// API 响应
#[derive(Debug, Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}

impl<T: Serialize> ApiResponse<T> {
    pub fn ok(data: T) -> Self {
        Self {
            success: true,
            data: Some(data),
            error: None,
        }
    }
}

impl ApiResponse<()> {
    pub fn err(msg: impl Into<String>) -> Self {
        ApiResponse {
            success: false,
            data: None,
            error: Some(msg.into()),
        }
    }
}
