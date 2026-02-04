//! REST API for AI Agents
//! 
//! Agents connect to this API to submit orders and query positions.

use axum::{
    routing::{get, post},
    Router, Json,
    extract::{State, Path, Query},
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::engine::MatchingEngine;
use crate::types::{Price, Quantity};
use crate::order::{Order, OrderSide, OrderType};

/// API State
pub struct ApiState {
    pub engine: Arc<RwLock<MatchingEngine>>,
}

/// 创建 REST API Router
pub fn create_router(state: Arc<ApiState>) -> Router {
    Router::new()
        // Agent 管理
        .route("/agent/register", post(register_agent))
        
        // 订单接口
        .route("/order/submit", post(submit_order))
        .route("/order/close", post(close_position))
        .route("/orders", get(get_orders))
        .route("/order/:order_id", get(get_order))
        .route("/order/:order_id/cancel", post(cancel_order))
        
        // 持仓接口
        .route("/positions", get(get_positions))
        .route("/position/:market", get(get_position))
        .route("/position/modify", post(modify_position))
        
        // 市场数据
        .route("/markets", get(get_markets))
        .route("/price/:market", get(get_price))
        .route("/orderbook/:market", get(get_orderbook))
        .route("/trades/:market", get(get_trades))
        
        // 账户
        .route("/account", get(get_account))
        
        .with_state(state)
}

// ==================== Request/Response Types ====================

#[derive(Debug, Deserialize)]
pub struct RegisterAgentRequest {
    pub pubkey: String,
    pub name: String,
}

#[derive(Debug, Serialize)]
pub struct RegisterAgentResponse {
    pub success: bool,
    pub agent_id: String,
    pub message: String,
}

#[derive(Debug, Deserialize)]
pub struct SubmitOrderRequest {
    pub agent_pubkey: String,
    pub market: String,
    pub side: String,        // "long" or "short"
    pub size_usd: f64,
    pub leverage: u8,
    pub order_type: String,  // "market", "limit", "stop"
    pub price: Option<f64>,
    pub signature: String,   // Agent 签名
}

#[derive(Debug, Serialize)]
pub struct SubmitOrderResponse {
    pub success: bool,
    pub order_id: Option<String>,
    pub tx_signature: Option<String>,
    pub message: String,
}

#[derive(Debug, Deserialize)]
pub struct ClosePositionRequest {
    pub agent_pubkey: String,
    pub market: String,
    pub size_percent: f64,
}

#[derive(Debug, Serialize)]
pub struct MarketInfo {
    pub symbol: String,
    pub index: u8,
    pub base_asset: String,
    pub price: f64,
    pub index_price: f64,
    pub funding_rate: f64,
    pub open_interest: f64,
    pub volume_24h: f64,
    pub bid: f64,
    pub ask: f64,
}

#[derive(Debug, Serialize)]
pub struct PriceResponse {
    pub market: String,
    pub price: f64,
    pub timestamp: i64,
}

#[derive(Debug, Serialize)]
pub struct PositionResponse {
    pub market: String,
    pub side: String,
    pub size: f64,
    pub size_usd: f64,
    pub entry_price: f64,
    pub mark_price: f64,
    pub liquidation_price: f64,
    pub margin: f64,
    pub leverage: u8,
    pub unrealized_pnl: f64,
    pub unrealized_pnl_percent: f64,
}

#[derive(Debug, Serialize)]
pub struct OrderResponse {
    pub order_id: String,
    pub market: String,
    pub side: String,
    pub order_type: String,
    pub size: f64,
    pub price: Option<f64>,
    pub status: String,
    pub filled_size: f64,
    pub created_at: i64,
}

#[derive(Debug, Serialize)]
pub struct OrderbookEntry {
    pub price: f64,
    pub size: f64,
}

#[derive(Debug, Serialize)]
pub struct OrderbookResponse {
    pub market: String,
    pub bids: Vec<OrderbookEntry>,
    pub asks: Vec<OrderbookEntry>,
    pub timestamp: i64,
}

#[derive(Debug, Serialize)]
pub struct AccountResponse {
    pub agent_id: String,
    pub pubkey: String,
    pub collateral: f64,
    pub available_margin: f64,
    pub total_position_value: f64,
    pub total_unrealized_pnl: f64,
}

// ==================== Handler Functions ====================

/// 注册 Agent
async fn register_agent(
    State(state): State<Arc<ApiState>>,
    Json(req): Json<RegisterAgentRequest>,
) -> Result<Json<RegisterAgentResponse>, StatusCode> {
    let engine = state.engine.write().await;
    
    // TODO: 实际注册逻辑，调用 Solana 程序
    
    Ok(Json(RegisterAgentResponse {
        success: true,
        agent_id: format!("agent_{}", &req.pubkey[..8]),
        message: format!("Agent '{}' registered successfully", req.name),
    }))
}

/// 提交订单
async fn submit_order(
    State(state): State<Arc<ApiState>>,
    Json(req): Json<SubmitOrderRequest>,
) -> Result<Json<SubmitOrderResponse>, StatusCode> {
    let mut engine = state.engine.write().await;
    
    // 验证签名
    // TODO: 实际签名验证
    
    // 解析市场
    let market_index = match req.market.as_str() {
        "BTC-PERP" => 0u8,
        "ETH-PERP" => 1u8,
        "SOL-PERP" => 2u8,
        _ => return Err(StatusCode::BAD_REQUEST),
    };
    
    // 解析订单方向
    let side = match req.side.as_str() {
        "long" => OrderSide::Buy,
        "short" => OrderSide::Sell,
        _ => return Err(StatusCode::BAD_REQUEST),
    };
    
    // 解析订单类型
    let order_type = match req.order_type.as_str() {
        "market" => OrderType::Market,
        "limit" => OrderType::Limit,
        _ => OrderType::Market,
    };
    
    // 计算数量 (size_usd / price)
    let current_price = engine.get_market_price(market_index);
    let quantity = (req.size_usd / current_price as f64 * 1_000_000.0) as Quantity;
    let price = req.price.map(|p| (p * 1_000_000.0) as Price).unwrap_or(current_price);
    
    // 创建订单
    let order = Order::new(
        market_index,
        req.agent_pubkey.clone(),
        side,
        order_type,
        price,
        quantity,
    );
    
    let order_id = order.id;
    
    // 提交到撮合引擎
    match engine.submit_order(order) {
        Ok(trades) => {
            Ok(Json(SubmitOrderResponse {
                success: true,
                order_id: Some(format!("{:016x}", order_id)),
                tx_signature: None, // 链上交易签名
                message: format!("Order submitted, {} trades executed", trades.len()),
            }))
        }
        Err(e) => {
            Ok(Json(SubmitOrderResponse {
                success: false,
                order_id: None,
                tx_signature: None,
                message: format!("Order rejected: {:?}", e),
            }))
        }
    }
}

/// 平仓
async fn close_position(
    State(state): State<Arc<ApiState>>,
    Json(req): Json<ClosePositionRequest>,
) -> Result<Json<SubmitOrderResponse>, StatusCode> {
    // TODO: 获取当前持仓，提交反向订单
    
    Ok(Json(SubmitOrderResponse {
        success: true,
        order_id: Some("close_order_123".to_string()),
        tx_signature: None,
        message: format!("Close order submitted for {} {}%", req.market, req.size_percent),
    }))
}

/// 获取订单列表
async fn get_orders(
    State(state): State<Arc<ApiState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<OrderResponse>>, StatusCode> {
    let engine = state.engine.read().await;
    
    // TODO: 根据 agent_pubkey 过滤订单
    
    Ok(Json(vec![]))
}

/// 获取订单详情
async fn get_order(
    State(state): State<Arc<ApiState>>,
    Path(order_id): Path<String>,
) -> Result<Json<OrderResponse>, StatusCode> {
    Err(StatusCode::NOT_FOUND)
}

/// 取消订单
async fn cancel_order(
    State(state): State<Arc<ApiState>>,
    Path(order_id): Path<String>,
) -> Result<Json<SubmitOrderResponse>, StatusCode> {
    let mut engine = state.engine.write().await;
    
    // TODO: 取消订单
    
    Ok(Json(SubmitOrderResponse {
        success: true,
        order_id: Some(order_id),
        tx_signature: None,
        message: "Order cancelled".to_string(),
    }))
}

/// 获取持仓列表
async fn get_positions(
    State(state): State<Arc<ApiState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<PositionResponse>>, StatusCode> {
    Ok(Json(vec![]))
}

/// 获取特定市场持仓
async fn get_position(
    State(state): State<Arc<ApiState>>,
    Path(market): Path<String>,
) -> Result<Json<PositionResponse>, StatusCode> {
    Err(StatusCode::NOT_FOUND)
}

/// 修改持仓
async fn modify_position(
    State(state): State<Arc<ApiState>>,
    Json(req): Json<serde_json::Value>,
) -> Result<Json<SubmitOrderResponse>, StatusCode> {
    Ok(Json(SubmitOrderResponse {
        success: true,
        order_id: None,
        tx_signature: None,
        message: "Position modified".to_string(),
    }))
}

/// 获取市场列表
async fn get_markets(
    State(state): State<Arc<ApiState>>,
) -> Result<Json<Vec<MarketInfo>>, StatusCode> {
    let engine = state.engine.read().await;
    
    let markets = vec![
        MarketInfo {
            symbol: "BTC-PERP".to_string(),
            index: 0,
            base_asset: "BTC".to_string(),
            price: engine.get_market_price(0) as f64 / 1_000_000.0,
            index_price: engine.get_market_price(0) as f64 / 1_000_000.0,
            funding_rate: 0.0001,
            open_interest: 0.0,
            volume_24h: 0.0,
            bid: 0.0,
            ask: 0.0,
        },
        MarketInfo {
            symbol: "ETH-PERP".to_string(),
            index: 1,
            base_asset: "ETH".to_string(),
            price: engine.get_market_price(1) as f64 / 1_000_000.0,
            index_price: engine.get_market_price(1) as f64 / 1_000_000.0,
            funding_rate: 0.0001,
            open_interest: 0.0,
            volume_24h: 0.0,
            bid: 0.0,
            ask: 0.0,
        },
        MarketInfo {
            symbol: "SOL-PERP".to_string(),
            index: 2,
            base_asset: "SOL".to_string(),
            price: engine.get_market_price(2) as f64 / 1_000_000.0,
            index_price: engine.get_market_price(2) as f64 / 1_000_000.0,
            funding_rate: 0.0001,
            open_interest: 0.0,
            volume_24h: 0.0,
            bid: 0.0,
            ask: 0.0,
        },
    ];
    
    Ok(Json(markets))
}

/// 获取市场价格
async fn get_price(
    State(state): State<Arc<ApiState>>,
    Path(market): Path<String>,
) -> Result<Json<PriceResponse>, StatusCode> {
    let engine = state.engine.read().await;
    
    let index = match market.as_str() {
        "BTC-PERP" => 0u8,
        "ETH-PERP" => 1u8,
        "SOL-PERP" => 2u8,
        _ => return Err(StatusCode::NOT_FOUND),
    };
    
    Ok(Json(PriceResponse {
        market,
        price: engine.get_market_price(index) as f64 / 1_000_000.0,
        timestamp: chrono::Utc::now().timestamp(),
    }))
}

/// 获取订单簿
async fn get_orderbook(
    State(state): State<Arc<ApiState>>,
    Path(market): Path<String>,
) -> Result<Json<OrderbookResponse>, StatusCode> {
    let engine = state.engine.read().await;
    
    let index = match market.as_str() {
        "BTC-PERP" => 0u8,
        "ETH-PERP" => 1u8,
        "SOL-PERP" => 2u8,
        _ => return Err(StatusCode::NOT_FOUND),
    };
    
    // TODO: 从引擎获取订单簿
    
    Ok(Json(OrderbookResponse {
        market,
        bids: vec![],
        asks: vec![],
        timestamp: chrono::Utc::now().timestamp(),
    }))
}

/// 获取成交记录
async fn get_trades(
    State(state): State<Arc<ApiState>>,
    Path(market): Path<String>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    Ok(Json(vec![]))
}

/// 获取账户信息
async fn get_account(
    State(state): State<Arc<ApiState>>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<AccountResponse>, StatusCode> {
    let pubkey = params.get("pubkey").ok_or(StatusCode::BAD_REQUEST)?;
    
    Ok(Json(AccountResponse {
        agent_id: format!("agent_{}", &pubkey[..8]),
        pubkey: pubkey.clone(),
        collateral: 0.0,
        available_margin: 0.0,
        total_position_value: 0.0,
        total_unrealized_pnl: 0.0,
    }))
}
