use anchor_lang::prelude::*;

#[error_code]
pub enum EscrowError {
    #[msg("Invalid leverage, must be 1-100")]
    InvalidLeverage,
    
    #[msg("Invalid size, must be greater than 0")]
    InvalidSize,
    
    #[msg("Math overflow")]
    MathOverflow,
    
    #[msg("Position is not active")]
    PositionNotActive,
    
    #[msg("Too early for funding settlement, must wait 8 hours")]
    TooEarlyForFunding,
    
    #[msg("Position is healthy, cannot liquidate")]
    PositionHealthy,
    
    #[msg("Unauthorized")]
    Unauthorized,
}
