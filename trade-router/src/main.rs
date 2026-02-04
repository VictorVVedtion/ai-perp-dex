mod db;
mod funding;
mod handlers;
mod liquidation;
mod price_feed;
mod demo_mm;
mod incentives;
mod margin;
mod middleware;
mod state;
mod types;
mod websocket;

use axum::{
    routing::{get, post},
    Router,
    middleware as axum_middleware,
};
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use crate::state::AppState;
use crate::middleware::{auth_middleware, rate_limit_middleware, RateLimiter};

#[tokio::main]
async fn main() {
    // 初始化日志
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .init();

    // 创建共享状态
    let state = Arc::new(AppState::new());

    // 启动价格更新 (每30秒)
    let price_state = state.clone();
    tokio::spawn(async move {
        price_feed::start_price_feed(price_state, 30).await;
    });

    // 启动强平引擎 (后台任务)
    let liq_state = state.clone();
    tokio::spawn(async move {
        liquidation::start_liquidation_engine(
            liq_state,
            liquidation::LiquidationConfig::default(),
        ).await;
    });

    // 启动 Funding 结算引擎 (每8小时)
    let funding_state = state.clone();
    tokio::spawn(async move {
        funding::start_funding_engine(
            funding_state,
            funding::FundingConfig::default(),
        ).await;
    });

    // 启动 Demo MM (自动报价，方便测试)
    let demo_state = state.clone();
    tokio::spawn(async move {
        demo_mm::start_demo_mm(
            demo_state,
            demo_mm::DemoMmConfig::default(),
        ).await;
    });

    // CORS 配置
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    // 限流器: 100 请求/分钟/IP
    let rate_limiter = Arc::new(RateLimiter::default());

    // 构建路由
    let app = Router::new()
        // 健康检查
        .route("/health", get(handlers::health))
        // Agent API
        .route("/agents/register", post(handlers::register_agent))
        .route("/agents/:agent_id", get(handlers::get_agent))
        .route("/agents/:agent_id/stats", get(handlers::get_agent_stats))
        .route("/mm/leaderboard", get(handlers::get_mm_leaderboard))
        .route("/agents/:agent_id/limits", get(handlers::get_agent_limits).post(handlers::set_agent_limits))
        // 交易 API
        .route("/trade/request", post(handlers::create_trade_request))
        .route("/trade/quote", post(handlers::create_quote))
        .route("/trade/accept", post(handlers::accept_quote))
        .route("/trade/close", post(handlers::close_position))
        // 查询 API
        .route("/positions/:agent_id", get(handlers::get_positions))
        .route("/positions/:agent_id/margin", get(handlers::get_positions_margin))
        .route("/positions/:agent_id/history", get(handlers::get_position_history))
        .route("/requests", get(handlers::get_requests))
        .route("/quotes/:request_id", get(handlers::get_quotes))
        .route("/markets", get(handlers::get_markets))
        // WebSocket
        .route("/ws", get(websocket::ws_handler))
        // 中间件 (顺序: cors -> rate_limit -> auth)
        .layer(axum_middleware::from_fn_with_state(state.clone(), auth_middleware))
        .layer(axum_middleware::from_fn_with_state(rate_limiter.clone(), rate_limit_middleware))
        .layer(cors)
        .with_state(state);

    let addr = "0.0.0.0:8080";
    info!("🚀 Trade Router starting on {}", addr);
    info!("📡 WebSocket endpoint: ws://{}/ws", addr);
    info!("📋 REST API: http://{}/", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
