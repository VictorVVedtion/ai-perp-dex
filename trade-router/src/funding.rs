//! Funding rate settlement engine
//!
//! Runs every 8 hours to settle funding payments between traders and market makers.
//! Trader pays funding to MM based on position size and funding rate.

use std::sync::Arc;
use std::time::Duration;
use tokio::time::interval;
use tracing::{info, warn};
use chrono::{DateTime, Utc};
use uuid::Uuid;
use serde::{Deserialize, Serialize};

use crate::state::AppState;
use crate::types::PositionStatus;

/// Funding settlement configuration
#[derive(Debug, Clone)]
pub struct FundingConfig {
    /// Settlement interval in hours (default: 8)
    pub interval_hours: u64,
    /// Whether to skip actual settlement (for testing)
    pub dry_run: bool,
}

impl Default for FundingConfig {
    fn default() -> Self {
        Self {
            interval_hours: 8,
            dry_run: false,
        }
    }
}

/// Funding payment record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FundingPayment {
    pub id: Uuid,
    pub position_id: Uuid,
    pub trader_agent: String,
    pub mm_agent: String,
    pub funding_rate: f64,
    pub position_size: f64,
    pub payment_amount: f64,  // positive = trader pays MM
    pub settled_at: DateTime<Utc>,
}

/// Start the funding settlement engine as a background task
pub async fn start_funding_engine(state: Arc<AppState>, config: FundingConfig) {
    info!(
        "💰 Funding engine starting (interval: {}h, dry_run: {})",
        config.interval_hours, config.dry_run
    );

    let interval_duration = Duration::from_secs(config.interval_hours * 3600);
    let mut ticker = interval(interval_duration);

    // Skip the first immediate tick - we want to wait for the full interval first
    ticker.tick().await;

    loop {
        ticker.tick().await;
        
        info!("💰 Running funding settlement...");
        
        if let Err(e) = settle_funding(&state, &config).await {
            warn!("Funding settlement failed: {}", e);
        }
    }
}

/// Settle funding for all active positions
async fn settle_funding(state: &AppState, config: &FundingConfig) -> Result<u32, String> {
    // Get all active positions
    let positions: Vec<_> = state
        .positions
        .iter()
        .filter(|p| p.status == PositionStatus::Active)
        .map(|p| p.clone())
        .collect();

    if positions.is_empty() {
        info!("💰 No active positions to settle");
        return Ok(0);
    }

    let mut settled_count = 0;
    let now = Utc::now();

    for position in positions {
        // Calculate funding payment
        // funding_rate is annual rate, we pay every 8 hours = 3 times per day = 1095 times per year
        // payment = position_size * funding_rate / 1095
        let periods_per_year = 365.0 * 24.0 / config.interval_hours as f64;
        let payment_amount = position.size_usdc * position.funding_rate / periods_per_year;

        let payment = FundingPayment {
            id: Uuid::new_v4(),
            position_id: position.id,
            trader_agent: position.trader_agent.clone(),
            mm_agent: position.mm_agent.clone(),
            funding_rate: position.funding_rate,
            position_size: position.size_usdc,
            payment_amount,
            settled_at: now,
        };

        info!(
            "💰 Funding: {} pays {} ${:.4} (rate: {:.4}%, size: ${:.2})",
            payment.trader_agent,
            payment.mm_agent,
            payment_amount,
            position.funding_rate * 100.0,
            position.size_usdc
        );

        if !config.dry_run {
            // Record to database
            if let Err(e) = state.db.save_funding_payment(&payment) {
                warn!("Failed to save funding payment: {}", e);
                continue;
            }
        }

        settled_count += 1;
    }

    info!(
        "💰 Funding settlement complete: {} positions processed",
        settled_count
    );
    Ok(settled_count)
}

/// Get funding payment history for an agent
pub fn get_funding_history(
    state: &AppState,
    agent_id: &str,
    limit: u32,
) -> Result<Vec<FundingPayment>, String> {
    state
        .db
        .get_funding_payments(agent_id, limit)
        .map_err(|e| format!("Database error: {}", e))
}

/// Calculate total funding paid/received by an agent
pub fn get_funding_summary(
    state: &AppState,
    agent_id: &str,
) -> Result<FundingSummary, String> {
    state
        .db
        .get_funding_summary(agent_id)
        .map_err(|e| format!("Database error: {}", e))
}

/// Funding summary for an agent
#[derive(Debug, Clone, Serialize)]
pub struct FundingSummary {
    pub agent_id: String,
    pub total_paid: f64,      // As trader
    pub total_received: f64,  // As MM
    pub net: f64,             // received - paid
    pub payment_count: u32,
}
