use anchor_lang::prelude::*;
use crate::state::{Agent, Exchange, Position};
use crate::errors::PerpError;

#[derive(Accounts)]
#[instruction(market_index: u8)]
pub struct ClosePosition<'info> {
    pub authority: Signer<'info>,
    
    #[account(
        seeds = [b"exchange"],
        bump = exchange.bump,
        constraint = exchange.authority == authority.key() @ PerpError::Unauthorized
    )]
    pub exchange: Account<'info, Exchange>,
    
    #[account(
        mut,
        seeds = [b"agent", agent.owner.as_ref()],
        bump = agent.bump
    )]
    pub agent: Account<'info, Agent>,
    
    #[account(
        mut,
        seeds = [b"position", agent.key().as_ref(), &[market_index]],
        bump = position.bump,
        constraint = position.size != 0 @ PerpError::NoPosition
    )]
    pub position: Account<'info, Position>,
}

pub fn handler(ctx: Context<ClosePosition>, _market_index: u8, exit_price: u64) -> Result<()> {
    require!(exit_price > 0, PerpError::InvalidPrice);
    
    let agent = &mut ctx.accounts.agent;
    let position = &mut ctx.accounts.position;
    let clock = Clock::get()?;
    
    // Calculate PnL
    let pnl = calculate_pnl(position.size, position.entry_price, exit_price)?;
    
    // Return margin + PnL
    let margin_return = position.margin;
    let total_return = if pnl >= 0 {
        margin_return.checked_add(pnl as u64).ok_or(PerpError::MathOverflow)?
    } else {
        margin_return.saturating_sub((-pnl) as u64)
    };
    
    // Update agent
    agent.collateral += total_return;
    agent.realized_pnl += pnl;
    agent.total_trades += 1;
    if pnl > 0 {
        agent.win_count += 1;
    }
    
    // Reset position
    position.size = 0;
    position.entry_price = 0;
    position.margin = 0;
    position.liquidation_price = 0;
    position.unrealized_pnl = 0;
    position.updated_at = clock.unix_timestamp;
    
    msg!(
        "Closed position: exit_price={}, pnl={}, returned={}",
        exit_price,
        pnl,
        total_return
    );
    
    Ok(())
}

fn calculate_pnl(size: i64, entry_price: u64, exit_price: u64) -> Result<i64> {
    let price_diff = exit_price as i64 - entry_price as i64;
    
    // PnL = size * price_diff / price_decimals
    let pnl = size
        .checked_mul(price_diff)
        .ok_or(PerpError::MathOverflow)?
        / 1_000_000; // Adjust for price decimals
    
    Ok(pnl)
}
