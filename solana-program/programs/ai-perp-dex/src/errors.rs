use anchor_lang::prelude::*;

#[error_code]
pub enum PerpError {
    #[msg("Insufficient collateral for this operation")]
    InsufficientCollateral,
    
    #[msg("Position size exceeds maximum allowed")]
    PositionTooLarge,
    
    #[msg("Leverage exceeds maximum allowed")]
    LeverageTooHigh,
    
    #[msg("Position is not liquidatable")]
    NotLiquidatable,
    
    #[msg("Market is not active")]
    MarketNotActive,
    
    #[msg("Agent is not active")]
    AgentNotActive,
    
    #[msg("Invalid price")]
    InvalidPrice,
    
    #[msg("Invalid size")]
    InvalidSize,
    
    #[msg("No position to close")]
    NoPosition,
    
    #[msg("Unauthorized")]
    Unauthorized,
    
    #[msg("Math overflow")]
    MathOverflow,
    
    #[msg("Invalid market index")]
    InvalidMarketIndex,
    
    #[msg("Agent name too long")]
    NameTooLong,
    
    #[msg("Withdrawal would leave insufficient margin")]
    InsufficientMargin,
}
