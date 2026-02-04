//! Risk Engine Module
//! 
//! Per-agent risk management with circuit breakers.

use crate::types::RiskParams;

/// Risk check result
#[derive(Debug)]
pub enum RiskCheckResult {
    Allowed,
    Rejected(RiskRejection),
    CircuitBreakerTriggered(String),
}

#[derive(Debug)]
pub enum RiskRejection {
    ExceedsMaxLeverage { requested: u8, max: u8 },
    ExceedsMaxPositionSize { requested: f64, max: f64 },
    ExceedsMaxPositions { current: u8, max: u8 },
    ExceedsDailyLossLimit { current_loss: f64, max: f64 },
    InsufficientMargin { required: f64, available: f64 },
    MarketClosed,
    AgentSuspended,
}

/// Check if an order passes risk limits
pub fn check_order_risk(
    params: &RiskParams,
    leverage: u8,
    size_usd: f64,
    current_positions: u8,
    daily_pnl: f64,
    available_margin: f64,
) -> RiskCheckResult {
    // Check leverage
    if leverage > params.max_leverage {
        return RiskCheckResult::Rejected(RiskRejection::ExceedsMaxLeverage {
            requested: leverage,
            max: params.max_leverage,
        });
    }
    
    // Check position size
    if size_usd > params.max_position_size_usd {
        return RiskCheckResult::Rejected(RiskRejection::ExceedsMaxPositionSize {
            requested: size_usd,
            max: params.max_position_size_usd,
        });
    }
    
    // Check position count
    if current_positions >= params.max_positions {
        return RiskCheckResult::Rejected(RiskRejection::ExceedsMaxPositions {
            current: current_positions,
            max: params.max_positions,
        });
    }
    
    // Check daily loss limit
    if daily_pnl < 0.0 && daily_pnl.abs() > params.max_daily_loss_usd {
        return RiskCheckResult::Rejected(RiskRejection::ExceedsDailyLossLimit {
            current_loss: daily_pnl.abs(),
            max: params.max_daily_loss_usd,
        });
    }
    
    // Check margin
    let required_margin = size_usd / leverage as f64;
    if required_margin > available_margin {
        return RiskCheckResult::Rejected(RiskRejection::InsufficientMargin {
            required: required_margin,
            available: available_margin,
        });
    }
    
    // Check circuit breaker
    if params.circuit_breaker_enabled {
        // If single position loss > circuit_breaker_loss_pct, trigger
        // This would need position-level tracking
    }
    
    RiskCheckResult::Allowed
}

/// Circuit breaker state for an agent
pub struct CircuitBreaker {
    pub agent_id: String,
    pub triggered: bool,
    pub triggered_at: Option<i64>,
    pub cooldown_until: Option<i64>,
    pub reason: Option<String>,
}

impl CircuitBreaker {
    pub fn new(agent_id: String) -> Self {
        Self {
            agent_id,
            triggered: false,
            triggered_at: None,
            cooldown_until: None,
            reason: None,
        }
    }
    
    pub fn trigger(&mut self, reason: &str, cooldown_seconds: i64) {
        let now = chrono::Utc::now().timestamp();
        self.triggered = true;
        self.triggered_at = Some(now);
        self.cooldown_until = Some(now + cooldown_seconds);
        self.reason = Some(reason.to_string());
    }
    
    pub fn is_active(&self) -> bool {
        if !self.triggered {
            return false;
        }
        
        if let Some(cooldown_until) = self.cooldown_until {
            let now = chrono::Utc::now().timestamp();
            if now > cooldown_until {
                return false;
            }
        }
        
        true
    }
    
    pub fn reset(&mut self) {
        self.triggered = false;
        self.triggered_at = None;
        self.cooldown_until = None;
        self.reason = None;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_risk_check_leverage() {
        let params = RiskParams {
            max_leverage: 10,
            ..Default::default()
        };
        
        // Should pass
        let result = check_order_risk(&params, 5, 1000.0, 0, 0.0, 10000.0);
        assert!(matches!(result, RiskCheckResult::Allowed));
        
        // Should fail - too much leverage
        let result = check_order_risk(&params, 20, 1000.0, 0, 0.0, 10000.0);
        assert!(matches!(result, RiskCheckResult::Rejected(RiskRejection::ExceedsMaxLeverage { .. })));
    }
    
    #[test]
    fn test_circuit_breaker() {
        let mut cb = CircuitBreaker::new("agent_123".to_string());
        assert!(!cb.is_active());
        
        cb.trigger("50% loss on single position", 3600);
        assert!(cb.is_active());
        
        cb.reset();
        assert!(!cb.is_active());
    }
}
