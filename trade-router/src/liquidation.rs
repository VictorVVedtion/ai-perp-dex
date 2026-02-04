//! Liquidation engine - monitors positions and triggers liquidations
//!
//! Runs as a background task, checking all active positions periodically.

use std::sync::Arc;
use std::time::Duration;
use tokio::time::interval;
use tracing::{info, warn};

use crate::margin::{should_liquidate, MarginConfig, PositionMarginInfo};
use crate::state::AppState;
use crate::types::{PositionStatus, WsMessage};

/// Liquidation engine configuration
#[derive(Debug, Clone)]
pub struct LiquidationConfig {
    /// How often to check positions (milliseconds)
    pub check_interval_ms: u64,
    /// Margin configuration
    pub margin_config: MarginConfig,
    /// Whether to actually liquidate or just warn
    pub dry_run: bool,
}

impl Default for LiquidationConfig {
    fn default() -> Self {
        Self {
            check_interval_ms: 1000,  // Check every second
            margin_config: MarginConfig::default(),
            dry_run: false,
        }
    }
}

/// Result of a liquidation check
#[derive(Debug, Clone, serde::Serialize)]
pub struct LiquidationEvent {
    pub position_id: String,
    pub agent_id: String,
    pub market: String,
    pub side: String,
    pub size_usdc: f64,
    pub entry_price: f64,
    pub liquidation_price: f64,
    pub current_price: f64,
    pub pnl: f64,
}

/// Start the liquidation engine as a background task
pub async fn start_liquidation_engine(state: Arc<AppState>, config: LiquidationConfig) {
    info!("🔥 Liquidation engine starting (interval: {}ms, dry_run: {})", 
          config.check_interval_ms, config.dry_run);
    
    let mut ticker = interval(Duration::from_millis(config.check_interval_ms));
    
    loop {
        ticker.tick().await;
        
        // Get all active positions
        let positions: Vec<_> = state.positions.iter()
            .filter(|p| p.status == PositionStatus::Active)
            .map(|p| p.clone())
            .collect();
        
        if positions.is_empty() {
            continue;
        }
        
        // Check each position
        for position in positions {
            let current_price = state.prices.get(&position.market)
                .map(|p| *p)
                .unwrap_or(position.entry_price);
            
            if should_liquidate(&position, current_price, &config.margin_config) {
                let event = LiquidationEvent {
                    position_id: position.id.to_string(),
                    agent_id: position.trader_agent.clone(),
                    market: format!("{:?}", position.market),
                    side: format!("{:?}", position.side),
                    size_usdc: position.size_usdc,
                    entry_price: position.entry_price,
                    liquidation_price: crate::margin::liquidation_price(&position, &config.margin_config),
                    current_price,
                    pnl: crate::margin::unrealized_pnl(&position, current_price),
                };
                
                warn!("🔥 LIQUIDATION: {} {} {} @ ${:.2} (entry: ${:.2}, liq: ${:.2})",
                      event.agent_id, event.market, event.side,
                      current_price, event.entry_price, event.liquidation_price);
                
                if !config.dry_run {
                    // Execute liquidation
                    if let Err(e) = execute_liquidation(&state, &position, current_price).await {
                        warn!("Liquidation failed for {}: {}", position.id, e);
                    }
                }
                
                // Broadcast liquidation event
                let _ = state.broadcast_tx.send(WsMessage::Liquidation(event.clone()));
            }
        }
    }
}

/// Execute a liquidation
async fn execute_liquidation(
    state: &AppState, 
    position: &crate::types::Position,
    _current_price: f64,
) -> Result<(), String> {
    // Mark position as liquidated
    if let Some(mut pos) = state.positions.get_mut(&position.id) {
        pos.status = PositionStatus::Liquidated;
        pos.closed_at = Some(chrono::Utc::now());
    }
    
    // Update database
    if let Err(e) = state.db.close_position(&position.id, 
        -position.trader_collateral,  // Trader loses collateral
        position.trader_collateral * 0.99,  // MM gets most (minus fee)
    ) {
        return Err(format!("DB error: {}", e));
    }
    
    info!("✅ Liquidated position {}", position.id);
    Ok(())
}

/// Check if a specific position should be liquidated (for API use)
pub fn check_position(
    state: &AppState,
    position_id: &str,
    config: &MarginConfig,
) -> Option<PositionMarginInfo> {
    let uuid = uuid::Uuid::parse_str(position_id).ok()?;
    let position = state.positions.get(&uuid)?;
    
    let current_price = state.prices.get(&position.market)
        .map(|p| *p)
        .unwrap_or(position.entry_price);
    
    Some(PositionMarginInfo::from_position(&position, current_price, config))
}
