use anchor_lang::prelude::*;
use crate::state::{Agent, Position, Market};
use crate::errors::PerpError;
use crate::oracle::{get_price_from_pyth, MAX_PRICE_AGE_SECS};

#[derive(Accounts)]
pub struct UpdatePositionPnl<'info> {
    #[account(
        mut,
        seeds = [b"agent", agent.owner.as_ref()],
        bump = agent.bump
    )]
    pub agent: Account<'info, Agent>,
    
    #[account(
        mut,
        seeds = [b"position", agent.key().as_ref(), &[position.market_index]],
        bump = position.bump,
        constraint = position.agent == agent.key() @ PerpError::Unauthorized
    )]
    pub position: Account<'info, Position>,
    
    #[account(
        seeds = [b"market", &[position.market_index]],
        bump = market.bump,
        constraint = market.oracle == oracle.key() @ PerpError::InvalidPrice
    )]
    pub market: Account<'info, Market>,
    
    /// Pyth price oracle account
    /// CHECK: Validated by Pyth SDK when reading prices
    pub oracle: AccountInfo<'info>,
}

pub fn handler(ctx: Context<UpdatePositionPnl>) -> Result<()> {
    let position = &mut ctx.accounts.position;
    let agent = &mut ctx.accounts.agent;
    let oracle = &ctx.accounts.oracle;
    
    // Skip if no position
    if position.size == 0 {
        return Ok(());
    }
    
    // Get current price from oracle
    let current_price = get_price_from_pyth(oracle, MAX_PRICE_AGE_SECS)?;
    
    // Calculate unrealized PnL
    // PnL = (current_price - entry_price) * size / 10^6
    let price_diff = if position.size > 0 {
        // Long: profit when price goes up
        (current_price as i64) - (position.entry_price as i64)
    } else {
        // Short: profit when price goes down
        (position.entry_price as i64) - (current_price as i64)
    };
    
    let size_abs = position.size.abs() as i64;
    let unrealized_pnl = price_diff
        .checked_mul(size_abs)
        .ok_or(PerpError::MathOverflow)?
        / 1_000_000_000_000; // Adjust for decimals (size 8 + price 6 - result 6)
    
    // Update position
    let old_pnl = position.unrealized_pnl;
    position.unrealized_pnl = unrealized_pnl;
    position.updated_at = Clock::get()?.unix_timestamp;
    
    // Update agent's unrealized PnL
    agent.unrealized_pnl = agent.unrealized_pnl
        .checked_sub(old_pnl)
        .ok_or(PerpError::MathOverflow)?
        .checked_add(unrealized_pnl)
        .ok_or(PerpError::MathOverflow)?;
    
    // Check if position should be flagged for liquidation
    let margin_ratio = if position.margin > 0 {
        ((position.margin as i64 + unrealized_pnl) * 10000) / (position.margin as i64)
    } else {
        0
    };
    
    msg!(
        "Updated PnL: price={}, pnl={}, margin_ratio={}bps",
        current_price,
        unrealized_pnl,
        margin_ratio
    );
    
    Ok(())
}
