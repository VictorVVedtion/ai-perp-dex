//! Margin and liquidation system
//!
//! Key concepts:
//! - Initial Margin: Required to open position (size / leverage)
//! - Maintenance Margin: Minimum to keep position (typically 50% of initial)
//! - Liquidation: When equity falls below maintenance margin

use crate::types::{Position, Side, Market};

/// Margin configuration
#[derive(Debug, Clone)]
pub struct MarginConfig {
    /// Maintenance margin ratio (0.5 = 50% of initial)
    pub maintenance_ratio: f64,
    /// Liquidation fee (goes to insurance fund)
    pub liquidation_fee: f64,
    /// Maximum leverage allowed
    pub max_leverage: u8,
}

impl Default for MarginConfig {
    fn default() -> Self {
        Self {
            maintenance_ratio: 0.5,
            liquidation_fee: 0.01,  // 1%
            max_leverage: 20,
        }
    }
}

/// Calculate required initial margin
pub fn initial_margin(size_usdc: f64, leverage: u8) -> f64 {
    size_usdc / leverage as f64
}

/// Calculate maintenance margin
pub fn maintenance_margin(initial: f64, config: &MarginConfig) -> f64 {
    initial * config.maintenance_ratio
}

/// Calculate unrealized PnL for a position
pub fn unrealized_pnl(position: &Position, current_price: f64) -> f64 {
    let price_change = (current_price - position.entry_price) / position.entry_price;
    let leveraged_change = price_change * position.leverage as f64;
    
    match position.side {
        Side::Long => position.size_usdc * leveraged_change,
        Side::Short => position.size_usdc * (-leveraged_change),
    }
}

/// Calculate current equity (collateral + unrealized PnL)
pub fn equity(position: &Position, current_price: f64) -> f64 {
    position.trader_collateral + unrealized_pnl(position, current_price)
}

/// Check if position should be liquidated
pub fn should_liquidate(position: &Position, current_price: f64, config: &MarginConfig) -> bool {
    let current_equity = equity(position, current_price);
    let maint_margin = maintenance_margin(position.trader_collateral, config);
    
    current_equity < maint_margin
}

/// Calculate liquidation price
pub fn liquidation_price(position: &Position, config: &MarginConfig) -> f64 {
    let maint_margin = maintenance_margin(position.trader_collateral, config);
    // Equity = collateral + pnl = maint_margin (at liquidation)
    // pnl = maint_margin - collateral
    let pnl_at_liq = maint_margin - position.trader_collateral;
    
    // For long: pnl = size * leverage * (price - entry) / entry
    // price = entry * (1 + pnl / (size * leverage))
    let factor = pnl_at_liq / (position.size_usdc * position.leverage as f64 / position.entry_price);
    
    match position.side {
        Side::Long => position.entry_price * (1.0 + factor),
        Side::Short => position.entry_price * (1.0 - factor),
    }
}

/// Margin health as percentage (100% = healthy, 0% = liquidation)
pub fn margin_health(position: &Position, current_price: f64, config: &MarginConfig) -> f64 {
    let current_equity = equity(position, current_price);
    let maint_margin = maintenance_margin(position.trader_collateral, config);
    let initial = position.trader_collateral;
    
    if current_equity <= maint_margin {
        return 0.0;
    }
    
    // Health = (equity - maint) / (initial - maint) * 100
    let buffer = initial - maint_margin;
    if buffer <= 0.0 {
        return 100.0;
    }
    
    ((current_equity - maint_margin) / buffer * 100.0).min(100.0)
}

/// Position summary with margin info
#[derive(Debug, Clone, serde::Serialize)]
pub struct PositionMarginInfo {
    pub position_id: String,
    pub market: String,
    pub side: String,
    pub size_usdc: f64,
    pub leverage: u8,
    pub entry_price: f64,
    pub current_price: f64,
    pub unrealized_pnl: f64,
    pub collateral: f64,
    pub equity: f64,
    pub initial_margin: f64,
    pub maintenance_margin: f64,
    pub liquidation_price: f64,
    pub margin_health: f64,  // 0-100%
    pub is_liquidatable: bool,
}

impl PositionMarginInfo {
    pub fn from_position(position: &Position, current_price: f64, config: &MarginConfig) -> Self {
        let pnl = unrealized_pnl(position, current_price);
        let eq = equity(position, current_price);
        let initial = position.trader_collateral;
        let maint = maintenance_margin(initial, config);
        let liq_price = liquidation_price(position, config);
        let health = margin_health(position, current_price, config);
        let liquidatable = should_liquidate(position, current_price, config);
        
        Self {
            position_id: position.id.to_string(),
            market: format!("{:?}", position.market),
            side: format!("{:?}", position.side),
            size_usdc: position.size_usdc,
            leverage: position.leverage,
            entry_price: position.entry_price,
            current_price,
            unrealized_pnl: pnl,
            collateral: position.trader_collateral,
            equity: eq,
            initial_margin: initial,
            maintenance_margin: maint,
            liquidation_price: liq_price,
            margin_health: health,
            is_liquidatable: liquidatable,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;
    use chrono::Utc;
    use crate::types::PositionStatus;
    
    fn make_position(side: Side, entry: f64, size: f64, leverage: u8) -> Position {
        Position {
            id: Uuid::new_v4(),
            request_id: Uuid::new_v4(),
            quote_id: Uuid::new_v4(),
            trader_agent: "test".to_string(),
            mm_agent: "mm".to_string(),
            market: Market::BtcPerp,
            side,
            size_usdc: size,
            leverage,
            entry_price: entry,
            funding_rate: 0.01,
            trader_collateral: size / leverage as f64,
            mm_collateral: size / leverage as f64,
            status: PositionStatus::Active,
            created_at: Utc::now(),
            closed_at: None,
        }
    }
    
    #[test]
    fn test_pnl_long() {
        let pos = make_position(Side::Long, 100.0, 1000.0, 10);
        // Price up 10% = 110
        // Leveraged change = 10% * 10 = 100%
        // PnL = 1000 * 1.0 = 1000
        assert!((unrealized_pnl(&pos, 110.0) - 1000.0).abs() < 0.01);
        
        // Price down 5%
        assert!((unrealized_pnl(&pos, 95.0) - (-500.0)).abs() < 0.01);
    }
    
    #[test]
    fn test_pnl_short() {
        let pos = make_position(Side::Short, 100.0, 1000.0, 10);
        // Price down 10% = good for short
        assert!((unrealized_pnl(&pos, 90.0) - 1000.0).abs() < 0.01);
    }
    
    #[test]
    fn test_liquidation() {
        let config = MarginConfig::default();
        let pos = make_position(Side::Long, 100.0, 1000.0, 10);
        // Initial collateral = 100, maint = 50
        
        // At entry price, should not liquidate
        assert!(!should_liquidate(&pos, 100.0, &config));
        
        // Price drops enough to wipe equity below maint
        // Need equity < 50, so pnl < -50
        // pnl = 1000 * 10 * (p - 100) / 100 < -50
        // p < 100 - 50 / 100 = 99.5 ... wait let me recalc
        // Actually: pnl = size * lev * change = 1000 * 10 * (p/100 - 1)
        // For pnl = -50: (p/100 - 1) = -0.005, p = 99.5
        assert!(should_liquidate(&pos, 95.0, &config));  // Should liquidate
    }
}
