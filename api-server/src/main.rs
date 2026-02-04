//! AI Perp DEX - API Server
//! 
//! REST/WebSocket API for AI Agents to trade perpetual contracts.

use axum::{
    routing::{get, post, delete, put},
    Router,
    Json,
    extract::{State, Path, Query},
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tower_http::cors::CorsLayer;

mod handlers;
mod types;
mod auth;
mod risk;

use types::*;

/// Application state shared across handlers
pub struct AppState {
    // TODO: Add matching engine, risk engine, etc.
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    
    println!(r#"
    ╔═══════════════════════════════════════════════════════╗
    ║           AI Perp DEX - API Server v0.1.0             ║
    ║                                                       ║
    ║   "Users are programs, not people"                    ║
    ╚═══════════════════════════════════════════════════════╝
    "#);

    let state = Arc::new(AppState {});

    let app = Router::new()
        // Health check
        .route("/health", get(health_check))
        
        // Agent management
        .route("/v1/agent/register", post(handlers::register_agent))
        .route("/v1/agent/info", get(handlers::get_agent_info))
        .route("/v1/agent/risk-params", put(handlers::set_risk_params))
        
        // Trading
        .route("/v1/order", post(handlers::submit_order))
        .route("/v1/order/:id", get(handlers::get_order))
        .route("/v1/order/:id", delete(handlers::cancel_order))
        .route("/v1/orders", get(handlers::get_orders))
        
        // Positions
        .route("/v1/positions", get(handlers::get_positions))
        .route("/v1/position/:market", get(handlers::get_position))
        .route("/v1/position/close", post(handlers::close_position))
        .route("/v1/position/modify", put(handlers::modify_position))
        
        // Market data
        .route("/v1/markets", get(handlers::get_markets))
        .route("/v1/price/:market", get(handlers::get_price))
        .route("/v1/orderbook/:market", get(handlers::get_orderbook))
        .route("/v1/trades/:market", get(handlers::get_trades))
        
        // Account
        .route("/v1/account", get(handlers::get_account))
        .route("/v1/account/deposit", post(handlers::deposit))
        .route("/v1/account/withdraw", post(handlers::withdraw))
        .route("/v1/account/history", get(handlers::get_history))
        
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = "0.0.0.0:8080";
    println!("🚀 API Server listening on {}", addr);
    println!("📖 Docs: http://localhost:8080/docs");
    
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
        "version": "0.1.0",
        "service": "ai-perp-dex"
    }))
}
