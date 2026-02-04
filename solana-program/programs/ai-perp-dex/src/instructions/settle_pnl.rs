use anchor_lang::prelude::*;
use crate::state::{Agent, Position};
use crate::errors::PerpError;

#[derive(Accounts)]
#[instruction(market_index: u8)]
pub struct SettlePnl<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [b"agent", owner.key().as_ref()],
        bump = agent.bump,
        constraint = agent.owner == owner.key() @ PerpError::Unauthorized
    )]
    pub agent: Account<'info, Agent>,
    
    #[account(
        mut,
        seeds = [b"position", agent.key().as_ref(), &[market_index]],
        bump = position.bump
    )]
    pub position: Account<'info, Position>,
    
    // TODO: Add oracle account for current price
}

pub fn handler(ctx: Context<SettlePnl>, _market_index: u8) -> Result<()> {
    let agent = &mut ctx.accounts.agent;
    let position = &mut ctx.accounts.position;
    let clock = Clock::get()?;
    
    // TODO: Get current price from oracle
    let current_price: u64 = position.entry_price; // Placeholder
    
    // Calculate unrealized PnL
    let unrealized_pnl = if position.size != 0 {
        calculate_unrealized_pnl(position.size, position.entry_price, current_price)?
    } else {
        0
    };
    
    // Update position unrealized PnL
    position.unrealized_pnl = unrealized_pnl;
    position.updated_at = clock.unix_timestamp;
    
    // Update agent unrealized PnL
    // Note: This is a simplified version. In production, you'd sum across all positions
    agent.unrealized_pnl = unrealized_pnl;
    
    msg!(
        "Settled PnL: current_price={}, unrealized_pnl={}",
        current_price,
        unrealized_pnl
    );
    
    Ok(())
}

fn calculate_unrealized_pnl(size: i64, entry_price: u64, current_price: u64) -> Result<i64> {
    let price_diff = current_price as i64 - entry_price as i64;
    
    let pnl = size
        .checked_mul(price_diff)
        .ok_or(PerpError::MathOverflow)?
        / 1_000_000;
    
    Ok(pnl)
}
