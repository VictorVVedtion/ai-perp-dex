mod handlers;
mod state;
mod types;
mod websocket;

use axum::{
    routing::{get, post},
    Router,
};
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use crate::state::AppState;

#[tokio::main]
async fn main() {
    // 初始化日志
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .init();

    // 创建共享状态
    let state = Arc::new(AppState::new());

    // CORS 配置
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    // 构建路由
    let app = Router::new()
        // 健康检查
        .route("/health", get(handlers::health))
        // Agent API
        .route("/agents/register", post(handlers::register_agent))
        .route("/agents/:agent_id", get(handlers::get_agent))
        // 交易 API
        .route("/trade/request", post(handlers::create_trade_request))
        .route("/trade/quote", post(handlers::create_quote))
        .route("/trade/accept", post(handlers::accept_quote))
        .route("/trade/close", post(handlers::close_position))
        // 查询 API
        .route("/positions/:agent_id", get(handlers::get_positions))
        .route("/requests", get(handlers::get_requests))
        .route("/quotes/:request_id", get(handlers::get_quotes))
        .route("/markets", get(handlers::get_markets))
        // WebSocket
        .route("/ws", get(websocket::ws_handler))
        // 中间件
        .layer(cors)
        .with_state(state);

    let addr = "0.0.0.0:8080";
    info!("🚀 Trade Router starting on {}", addr);
    info!("📡 WebSocket endpoint: ws://{}/ws", addr);
    info!("📋 REST API: http://{}/", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
