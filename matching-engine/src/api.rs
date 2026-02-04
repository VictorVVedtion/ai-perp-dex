//! REST and WebSocket API for the matching engine

use axum::{
    extract::{Path, Query, State, ws::WebSocketUpgrade},
    response::{IntoResponse, Response},
    routing::{get, post, delete},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use crate::engine::MatchingEngine;
use crate::order::{PlaceOrderRequest, CancelOrderRequest};

/// API state
pub struct ApiState {
    pub engine: Arc<MatchingEngine>,
}

/// Create the API router
pub fn create_router(engine: Arc<MatchingEngine>) -> Router {
    let state = Arc::new(ApiState { engine });
    
    Router::new()
        .route("/health", get(health_check))
        .route("/markets", get(list_markets))
        .route("/markets/{market}/orderbook", get(get_orderbook))
        .route("/markets/{market}/bbo", get(get_bbo))
        .route("/orders", post(place_order))
        .route("/orders/{order_id}", delete(cancel_order))
        .route("/ws", get(websocket_handler))
        .with_state(state)
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    version: String,
}

async fn health_check() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    })
}

async fn list_markets(
    State(state): State<Arc<ApiState>>,
) -> Json<Vec<String>> {
    let markets: Vec<String> = state.engine.markets()
        .iter()
        .map(|m| m.0.clone())
        .collect();
    Json(markets)
}

#[derive(Deserialize)]
struct OrderbookParams {
    depth: Option<usize>,
}

async fn get_orderbook(
    State(state): State<Arc<ApiState>>,
    Path(market): Path<String>,
    Query(params): Query<OrderbookParams>,
) -> Response {
    let depth = params.depth.unwrap_or(20);
    match state.engine.get_orderbook(&market, depth) {
        Ok(snapshot) => Json(serde_json::to_value(snapshot).unwrap()).into_response(),
        Err(e) => (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": e.to_string()}))
        ).into_response(),
    }
}

#[derive(Serialize)]
struct BboResponse {
    market: String,
    best_bid: Option<String>,
    best_ask: Option<String>,
    spread: Option<String>,
}

async fn get_bbo(
    State(state): State<Arc<ApiState>>,
    Path(market): Path<String>,
) -> Response {
    match state.engine.get_bbo(&market) {
        Ok((bid, ask)) => {
            let spread = match (bid, ask) {
                (Some(b), Some(a)) => Some(format!("{}", a.as_decimal() - b.as_decimal())),
                _ => None,
            };
            Json(BboResponse {
                market,
                best_bid: bid.map(|p| format!("{}", p.as_decimal())),
                best_ask: ask.map(|p| format!("{}", p.as_decimal())),
                spread,
            }).into_response()
        }
        Err(e) => (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": e.to_string()}))
        ).into_response(),
    }
}

#[derive(Serialize)]
struct PlaceOrderResponse {
    order_id: String,
    status: String,
    trades: Vec<serde_json::Value>,
}

async fn place_order(
    State(state): State<Arc<ApiState>>,
    Json(request): Json<PlaceOrderRequest>,
) -> Response {
    match state.engine.place_order(request) {
        Ok((order, trades)) => {
            let trades_json: Vec<serde_json::Value> = trades
                .iter()
                .map(|t| serde_json::to_value(t).unwrap())
                .collect();
            
            Json(PlaceOrderResponse {
                order_id: format!("{}", order.id),
                status: format!("{:?}", order.status),
                trades: trades_json,
            }).into_response()
        }
        Err(e) => (
            axum::http::StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": e.to_string()}))
        ).into_response(),
    }
}

#[derive(Serialize)]
struct CancelOrderResponse {
    order_id: String,
    status: String,
}

async fn cancel_order(
    State(state): State<Arc<ApiState>>,
    Path(order_id): Path<u64>,
) -> Response {
    let req = CancelOrderRequest {
        agent_id: "".to_string(), // TODO: Get from auth
        order_id,
    };
    
    match state.engine.cancel_order(req) {
        Ok(order) => Json(CancelOrderResponse {
            order_id: format!("{}", order.id),
            status: format!("{:?}", order.status),
        }).into_response(),
        Err(e) => (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({"error": e.to_string()}))
        ).into_response(),
    }
}

async fn websocket_handler(
    ws: WebSocketUpgrade,
) -> Response {
    ws.on_upgrade(|_socket| async move {
        // TODO: Implement WebSocket handling
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_health_check() {
        let response = health_check().await;
        assert_eq!(response.0.status, "healthy");
    }
}
