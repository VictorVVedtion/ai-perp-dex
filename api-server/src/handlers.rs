//! API Handlers
//! 
//! All REST API endpoint handlers for AI Perp DEX.

use axum::{
    Json,
    extract::{State, Path, Query},
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use chrono::Utc;
use uuid::Uuid;

use crate::AppState;
use crate::types::*;

// ==================== Agent Management ====================

#[derive(Debug, Deserialize)]
pub struct RegisterAgentRequest {
    pub pubkey: String,
    pub name: String,
    pub risk_params: Option<RiskParams>,
}

#[derive(Debug, Serialize)]
pub struct RegisterAgentResponse {
    pub success: bool,
    pub agent_id: String,
    pub message: String,
}

pub async fn register_agent(
    State(_state): State<Arc<AppState>>,
    Json(req): Json<RegisterAgentRequest>,
) -> Result<Json<RegisterAgentResponse>, StatusCode> {
    // TODO: Register agent on-chain and in database
    let agent_id = format!("agent_{}", &req.pubkey[..8]);
    
    Ok(Json(RegisterAgentResponse {
        success: true,
        agent_id: agent_id.clone(),
        message: format!("Agent '{}' registered with ID: {}", req.name, agent_id),
    }))
}

pub async fn get_agent_info(
    State(_state): State<Arc<AppState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<AgentInfo>, StatusCode> {
    let pubkey = params.get("pubkey").ok_or(StatusCode::BAD_REQUEST)?;
    
    // TODO: Get from database
    Ok(Json(AgentInfo {
        agent_id: format!("agent_{}", &pubkey[..8]),
        pubkey: pubkey.clone(),
        name: "AI Agent".to_string(),
        created_at: Utc::now().timestamp(),
        risk_params: RiskParams::default(),
        stats: AgentStats::default(),
    }))
}

pub async fn set_risk_params(
    State(_state): State<Arc<AppState>>,
    Json(params): Json<RiskParams>,
) -> Result<Json<ApiResponse>, StatusCode> {
    // TODO: Update risk params
    Ok(Json(ApiResponse {
        success: true,
        message: "Risk parameters updated".to_string(),
    }))
}

// ==================== Trading ====================

#[derive(Debug, Deserialize)]
pub struct SubmitOrderRequest {
    pub market: String,
    pub side: String,         // "long" or "short"
    pub order_type: String,   // "market", "limit", "stop"
    pub size_usd: f64,
    pub leverage: u8,
    pub price: Option<f64>,   // Required for limit orders
    pub stop_price: Option<f64>,
    pub take_profit: Option<f64>,
    pub stop_loss: Option<f64>,
    pub client_order_id: Option<String>,
    pub signature: String,
}

#[derive(Debug, Serialize)]
pub struct SubmitOrderResponse {
    pub success: bool,
    pub order_id: Option<String>,
    pub client_order_id: Option<String>,
    pub status: String,
    pub filled_size: f64,
    pub avg_price: Option<f64>,
    pub message: String,
}

pub async fn submit_order(
    State(_state): State<Arc<AppState>>,
    Json(req): Json<SubmitOrderRequest>,
) -> Result<Json<SubmitOrderResponse>, StatusCode> {
    // TODO: Validate signature
    // TODO: Check risk limits
    // TODO: Submit to matching engine
    
    let order_id = Uuid::new_v4().to_string();
    
    Ok(Json(SubmitOrderResponse {
        success: true,
        order_id: Some(order_id.clone()),
        client_order_id: req.client_order_id,
        status: "filled".to_string(),
        filled_size: req.size_usd,
        avg_price: Some(97500.0), // TODO: Get from matching engine
        message: format!(
            "Order {} {} {} ${} @ {}x",
            order_id, req.side, req.market, req.size_usd, req.leverage
        ),
    }))
}

pub async fn get_order(
    State(_state): State<Arc<AppState>>,
    Path(order_id): Path<String>,
) -> Result<Json<Order>, StatusCode> {
    // TODO: Get from database
    Err(StatusCode::NOT_FOUND)
}

pub async fn cancel_order(
    State(_state): State<Arc<AppState>>,
    Path(order_id): Path<String>,
) -> Result<Json<ApiResponse>, StatusCode> {
    // TODO: Cancel in matching engine
    Ok(Json(ApiResponse {
        success: true,
        message: format!("Order {} cancelled", order_id),
    }))
}

pub async fn get_orders(
    State(_state): State<Arc<AppState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<Order>>, StatusCode> {
    // TODO: Get from database
    Ok(Json(vec![]))
}

// ==================== Positions ====================

pub async fn get_positions(
    State(_state): State<Arc<AppState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<Position>>, StatusCode> {
    // TODO: Get from database
    Ok(Json(vec![]))
}

pub async fn get_position(
    State(_state): State<Arc<AppState>>,
    Path(market): Path<String>,
) -> Result<Json<Position>, StatusCode> {
    // TODO: Get from database
    Err(StatusCode::NOT_FOUND)
}

#[derive(Debug, Deserialize)]
pub struct ClosePositionRequest {
    pub market: String,
    pub size_percent: Option<f64>,  // Default 100%
}

pub async fn close_position(
    State(_state): State<Arc<AppState>>,
    Json(req): Json<ClosePositionRequest>,
) -> Result<Json<SubmitOrderResponse>, StatusCode> {
    let size_pct = req.size_percent.unwrap_or(100.0);
    
    // TODO: Get position and submit close order
    Ok(Json(SubmitOrderResponse {
        success: true,
        order_id: Some(Uuid::new_v4().to_string()),
        client_order_id: None,
        status: "filled".to_string(),
        filled_size: 0.0,
        avg_price: None,
        message: format!("Closed {}% of {} position", size_pct, req.market),
    }))
}

#[derive(Debug, Deserialize)]
pub struct ModifyPositionRequest {
    pub market: String,
    pub new_leverage: Option<u8>,
    pub add_margin: Option<f64>,
    pub take_profit: Option<f64>,
    pub stop_loss: Option<f64>,
}

pub async fn modify_position(
    State(_state): State<Arc<AppState>>,
    Json(req): Json<ModifyPositionRequest>,
) -> Result<Json<ApiResponse>, StatusCode> {
    // TODO: Modify position
    Ok(Json(ApiResponse {
        success: true,
        message: format!("Position {} modified", req.market),
    }))
}

// ==================== Market Data ====================

pub async fn get_markets(
    State(_state): State<Arc<AppState>>,
) -> Result<Json<Vec<Market>>, StatusCode> {
    Ok(Json(vec![
        Market {
            symbol: "BTC-PERP".to_string(),
            index: 0,
            base_asset: "BTC".to_string(),
            quote_asset: "USD".to_string(),
            price: 97500.0,
            index_price: 97520.0,
            mark_price: 97510.0,
            funding_rate: 0.0001,
            next_funding_time: Utc::now().timestamp() + 3600,
            open_interest: 15000000.0,
            volume_24h: 250000000.0,
            max_leverage: 50,
            min_size: 10.0,
            tick_size: 0.1,
        },
        Market {
            symbol: "ETH-PERP".to_string(),
            index: 1,
            base_asset: "ETH".to_string(),
            quote_asset: "USD".to_string(),
            price: 2750.0,
            index_price: 2752.0,
            mark_price: 2751.0,
            funding_rate: 0.00008,
            next_funding_time: Utc::now().timestamp() + 3600,
            open_interest: 8000000.0,
            volume_24h: 120000000.0,
            max_leverage: 50,
            min_size: 10.0,
            tick_size: 0.01,
        },
        Market {
            symbol: "SOL-PERP".to_string(),
            index: 2,
            base_asset: "SOL".to_string(),
            quote_asset: "USD".to_string(),
            price: 195.0,
            index_price: 195.5,
            mark_price: 195.2,
            funding_rate: 0.00012,
            next_funding_time: Utc::now().timestamp() + 3600,
            open_interest: 3000000.0,
            volume_24h: 45000000.0,
            max_leverage: 30,
            min_size: 10.0,
            tick_size: 0.001,
        },
    ]))
}

pub async fn get_price(
    State(_state): State<Arc<AppState>>,
    Path(market): Path<String>,
) -> Result<Json<PriceResponse>, StatusCode> {
    let price = match market.as_str() {
        "BTC-PERP" => 97500.0,
        "ETH-PERP" => 2750.0,
        "SOL-PERP" => 195.0,
        _ => return Err(StatusCode::NOT_FOUND),
    };
    
    Ok(Json(PriceResponse {
        market,
        price,
        index_price: price * 1.0002,
        mark_price: price * 1.0001,
        timestamp: Utc::now().timestamp_millis(),
    }))
}

pub async fn get_orderbook(
    State(_state): State<Arc<AppState>>,
    Path(market): Path<String>,
) -> Result<Json<Orderbook>, StatusCode> {
    // TODO: Get from matching engine
    Ok(Json(Orderbook {
        market,
        bids: vec![
            OrderbookLevel { price: 97490.0, size: 1.5 },
            OrderbookLevel { price: 97480.0, size: 2.3 },
            OrderbookLevel { price: 97470.0, size: 3.1 },
        ],
        asks: vec![
            OrderbookLevel { price: 97510.0, size: 1.2 },
            OrderbookLevel { price: 97520.0, size: 2.0 },
            OrderbookLevel { price: 97530.0, size: 2.8 },
        ],
        timestamp: Utc::now().timestamp_millis(),
    }))
}

pub async fn get_trades(
    State(_state): State<Arc<AppState>>,
    Path(market): Path<String>,
) -> Result<Json<Vec<Trade>>, StatusCode> {
    // TODO: Get from database
    Ok(Json(vec![]))
}

// ==================== Account ====================

pub async fn get_account(
    State(_state): State<Arc<AppState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Account>, StatusCode> {
    let pubkey = params.get("pubkey").ok_or(StatusCode::BAD_REQUEST)?;
    
    // TODO: Get from database
    Ok(Json(Account {
        agent_id: format!("agent_{}", &pubkey[..8]),
        pubkey: pubkey.clone(),
        collateral: 10000.0,
        available_margin: 8500.0,
        used_margin: 1500.0,
        total_position_value: 15000.0,
        unrealized_pnl: 250.0,
        realized_pnl: 1200.0,
        total_volume: 500000.0,
        total_trades: 150,
    }))
}

#[derive(Debug, Deserialize)]
pub struct DepositRequest {
    pub amount: f64,
    pub tx_signature: String,
}

pub async fn deposit(
    State(_state): State<Arc<AppState>>,
    Json(req): Json<DepositRequest>,
) -> Result<Json<ApiResponse>, StatusCode> {
    // TODO: Verify tx and credit account
    Ok(Json(ApiResponse {
        success: true,
        message: format!("Deposited ${}", req.amount),
    }))
}

#[derive(Debug, Deserialize)]
pub struct WithdrawRequest {
    pub amount: f64,
    pub destination: String,
}

pub async fn withdraw(
    State(_state): State<Arc<AppState>>,
    Json(req): Json<WithdrawRequest>,
) -> Result<Json<WithdrawResponse>, StatusCode> {
    // TODO: Check available margin and process withdrawal
    Ok(Json(WithdrawResponse {
        success: true,
        tx_signature: Some("mock_tx_sig".to_string()),
        message: format!("Withdrew ${} to {}", req.amount, req.destination),
    }))
}

pub async fn get_history(
    State(_state): State<Arc<AppState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<TradeHistory>>, StatusCode> {
    // TODO: Get from database
    Ok(Json(vec![]))
}
