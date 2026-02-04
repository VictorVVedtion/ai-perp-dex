//! AI Perp DEX - Main Entry Point

use ai_perp_dex_matching_engine::{api, MatchingEngine};
use std::sync::Arc;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize logging
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();
    
    tracing::info!("🚀 Starting AI Perp DEX Matching Engine");
    
    // Create matching engine
    let engine = Arc::new(MatchingEngine::new());
    
    tracing::info!(
        "📊 Loaded {} markets: {:?}",
        engine.markets().len(),
        engine.markets().iter().map(|m| &m.0).collect::<Vec<_>>()
    );
    
    // Create API router
    let app = api::create_router(engine);
    
    // Start server
    let addr = std::net::SocketAddr::from(([0, 0, 0, 0], 8080));
    tracing::info!("🌐 Listening on http://{}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    
    Ok(())
}
