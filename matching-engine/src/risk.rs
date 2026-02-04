//! Risk management for AI Perp DEX
//!
//! Handles:
//! - Position limits
//! - Leverage limits
//! - Liquidation logic
//! - Daily loss limits

use crate::agent::AgentRiskLimits;
use crate::types::Market;
use rust_decimal::Decimal;
use rust_decimal::prelude::Signed;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum RiskError {
    #[error("Position limit exceeded: max {max}, requested {requested}")]
    PositionLimitExceeded { max: f64, requested: f64 },
    
    #[error("Leverage limit exceeded: max {max}x, requested {requested}x")]
    LeverageLimitExceeded { max: f64, requested: f64 },
    
    #[error("Daily loss limit exceeded: limit ${limit}, current loss ${current}")]
    DailyLossLimitExceeded { limit: f64, current: f64 },
    
    #[error("Insufficient margin: required ${required}, available ${available}")]
    InsufficientMargin { required: f64, available: f64 },
    
    #[error("Max open orders exceeded: limit {limit}")]
    MaxOpenOrdersExceeded { limit: u32 },
}

/// A position in a market
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub market: Market,
    pub agent_id: String,
    /// Positive = long, negative = short
    pub size: Decimal,
    /// Average entry price
    pub entry_price: Decimal,
    /// Unrealized PnL
    pub unrealized_pnl: Decimal,
    /// Margin used
    pub margin: Decimal,
    /// Liquidation price
    pub liquidation_price: Decimal,
}

impl Position {
    pub fn new(market: Market, agent_id: String) -> Self {
        Self {
            market,
            agent_id,
            size: Decimal::ZERO,
            entry_price: Decimal::ZERO,
            unrealized_pnl: Decimal::ZERO,
            margin: Decimal::ZERO,
            liquidation_price: Decimal::ZERO,
        }
    }
    
    pub fn is_long(&self) -> bool {
        self.size > Decimal::ZERO
    }
    
    pub fn is_short(&self) -> bool {
        self.size < Decimal::ZERO
    }
    
    pub fn is_flat(&self) -> bool {
        self.size == Decimal::ZERO
    }
    
    pub fn notional_value(&self, current_price: Decimal) -> Decimal {
        self.size.abs() * current_price
    }
    
    pub fn leverage(&self) -> Decimal {
        if self.margin == Decimal::ZERO {
            Decimal::ZERO
        } else {
            self.notional_value(self.entry_price) / self.margin
        }
    }
    
    /// Calculate unrealized PnL
    pub fn calculate_pnl(&self, current_price: Decimal) -> Decimal {
        let price_diff = current_price - self.entry_price;
        self.size * price_diff
    }
    
    /// Update position after a fill
    pub fn update_after_fill(&mut self, fill_size: Decimal, fill_price: Decimal) {
        let old_size = self.size;
        let new_size = old_size + fill_size;
        
        if new_size == Decimal::ZERO {
            // Position closed
            self.size = Decimal::ZERO;
            self.entry_price = Decimal::ZERO;
        } else if old_size.signum() == new_size.signum() || old_size == Decimal::ZERO {
            // Position increased or new position
            let old_notional = old_size.abs() * self.entry_price;
            let fill_notional = fill_size.abs() * fill_price;
            self.size = new_size;
            self.entry_price = (old_notional + fill_notional) / new_size.abs();
        } else {
            // Position reduced or flipped
            self.size = new_size;
            if new_size.signum() != old_size.signum() {
                // Flipped - new entry price is fill price
                self.entry_price = fill_price;
            }
        }
    }
}

/// Risk engine for an agent
pub struct RiskEngine {
    /// Position by market
    positions: HashMap<(String, Market), Position>,
    /// Account balance
    balances: HashMap<String, Decimal>,
    /// Daily PnL tracking
    daily_pnl: HashMap<String, Decimal>,
}

impl RiskEngine {
    pub fn new() -> Self {
        Self {
            positions: HashMap::new(),
            balances: HashMap::new(),
            daily_pnl: HashMap::new(),
        }
    }
    
    /// Get or create position
    pub fn get_position(&mut self, agent_id: &str, market: &Market) -> &mut Position {
        let key = (agent_id.to_string(), market.clone());
        self.positions.entry(key).or_insert_with(|| {
            Position::new(market.clone(), agent_id.to_string())
        })
    }
    
    /// Get agent balance
    pub fn get_balance(&self, agent_id: &str) -> Decimal {
        self.balances.get(agent_id).cloned().unwrap_or(Decimal::ZERO)
    }
    
    /// Set agent balance
    pub fn set_balance(&mut self, agent_id: &str, balance: Decimal) {
        self.balances.insert(agent_id.to_string(), balance);
    }
    
    /// Deposit funds
    pub fn deposit(&mut self, agent_id: &str, amount: Decimal) {
        let balance = self.balances.entry(agent_id.to_string()).or_insert(Decimal::ZERO);
        *balance += amount;
    }
    
    /// Withdraw funds
    pub fn withdraw(&mut self, agent_id: &str, amount: Decimal) -> Result<(), RiskError> {
        let balance = self.get_balance(agent_id);
        if balance < amount {
            return Err(RiskError::InsufficientMargin {
                required: amount.to_string().parse().unwrap_or(0.0),
                available: balance.to_string().parse().unwrap_or(0.0),
            });
        }
        self.balances.insert(agent_id.to_string(), balance - amount);
        Ok(())
    }
    
    /// Check if order passes risk checks
    pub fn check_order(
        &self,
        agent_id: &str,
        _market: &Market,
        _size: Decimal,
        _price: Decimal,
        limits: &AgentRiskLimits,
    ) -> Result<(), RiskError> {
        // Check daily loss limit
        let daily_loss = self.daily_pnl.get(agent_id).cloned().unwrap_or(Decimal::ZERO);
        if daily_loss < Decimal::ZERO {
            let loss_f64: f64 = daily_loss.abs().to_string().parse().unwrap_or(0.0);
            if loss_f64 > limits.daily_loss_limit_usd {
                return Err(RiskError::DailyLossLimitExceeded {
                    limit: limits.daily_loss_limit_usd,
                    current: loss_f64,
                });
            }
        }
        
        // TODO: Add more risk checks
        // - Position size limits
        // - Leverage limits
        // - Margin requirements
        
        Ok(())
    }
    
    /// Calculate liquidation price for a position
    pub fn calculate_liquidation_price(
        &self,
        position: &Position,
        maintenance_margin_rate: Decimal,
    ) -> Decimal {
        if position.is_flat() {
            return Decimal::ZERO;
        }
        
        // For long: liq_price = entry_price * (1 - margin_rate / leverage)
        // For short: liq_price = entry_price * (1 + margin_rate / leverage)
        let leverage = position.leverage();
        if leverage == Decimal::ZERO {
            return Decimal::ZERO;
        }
        
        let margin_factor = maintenance_margin_rate / leverage;
        
        if position.is_long() {
            position.entry_price * (Decimal::ONE - margin_factor)
        } else {
            position.entry_price * (Decimal::ONE + margin_factor)
        }
    }
    
    /// Check if position should be liquidated
    pub fn should_liquidate(
        &self,
        position: &Position,
        current_price: Decimal,
    ) -> bool {
        if position.is_flat() {
            return false;
        }
        
        if position.is_long() {
            current_price <= position.liquidation_price
        } else {
            current_price >= position.liquidation_price
        }
    }
}

impl Default for RiskEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;
    
    #[test]
    fn test_position_pnl() {
        let mut pos = Position::new(Market::btc_perp(), "agent-1".to_string());
        pos.size = dec!(1.0);
        pos.entry_price = dec!(50000);
        
        // Price goes up
        let pnl = pos.calculate_pnl(dec!(51000));
        assert_eq!(pnl, dec!(1000));
        
        // Price goes down
        let pnl = pos.calculate_pnl(dec!(49000));
        assert_eq!(pnl, dec!(-1000));
    }
    
    #[test]
    fn test_position_update() {
        let mut pos = Position::new(Market::btc_perp(), "agent-1".to_string());
        
        // Open long
        pos.update_after_fill(dec!(1.0), dec!(50000));
        assert_eq!(pos.size, dec!(1.0));
        assert_eq!(pos.entry_price, dec!(50000));
        
        // Add to long
        pos.update_after_fill(dec!(1.0), dec!(52000));
        assert_eq!(pos.size, dec!(2.0));
        assert_eq!(pos.entry_price, dec!(51000)); // Average
        
        // Close position
        pos.update_after_fill(dec!(-2.0), dec!(53000));
        assert!(pos.is_flat());
    }
    
    #[test]
    fn test_deposit_withdraw() {
        let mut engine = RiskEngine::new();
        
        engine.deposit("agent-1", dec!(10000));
        assert_eq!(engine.get_balance("agent-1"), dec!(10000));
        
        assert!(engine.withdraw("agent-1", dec!(5000)).is_ok());
        assert_eq!(engine.get_balance("agent-1"), dec!(5000));
        
        // Insufficient balance
        assert!(engine.withdraw("agent-1", dec!(10000)).is_err());
    }
}
