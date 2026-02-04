use anchor_lang::prelude::*;
use crate::state::{Agent, Exchange, Position};
use crate::errors::PerpError;

#[derive(Accounts)]
#[instruction(market_index: u8)]
pub struct Liquidate<'info> {
    /// Liquidator (receives reward)
    #[account(mut)]
    pub liquidator: Signer<'info>,
    
    #[account(
        mut,
        seeds = [b"exchange"],
        bump = exchange.bump
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
    
    /// Liquidator's agent account (to receive reward)
    #[account(
        mut,
        seeds = [b"agent", liquidator.key().as_ref()],
        bump = liquidator_agent.bump
    )]
    pub liquidator_agent: Account<'info, Agent>,
    
    // TODO: Add oracle account for price verification
}

pub fn handler(ctx: Context<Liquidate>, _market_index: u8) -> Result<()> {
    let position = &mut ctx.accounts.position;
    let agent = &mut ctx.accounts.agent;
    let liquidator_agent = &mut ctx.accounts.liquidator_agent;
    let clock = Clock::get()?;
    
    // TODO: Get current price from oracle
    let current_price: u64 = 0; // Placeholder
    
    // Check if position is liquidatable
    let is_liquidatable = if position.size > 0 {
        current_price <= position.liquidation_price
    } else {
        current_price >= position.liquidation_price
    };
    
    require!(is_liquidatable, PerpError::NotLiquidatable);
    
    // Calculate liquidation penalty (e.g., 5% of margin)
    let liquidation_penalty = position.margin * 5 / 100;
    let liquidator_reward = liquidation_penalty / 2;
    let insurance_fund = liquidation_penalty - liquidator_reward;
    
    // Calculate remaining margin after loss
    let remaining_margin = position.margin.saturating_sub(liquidation_penalty);
    
    // Return remaining margin to agent
    agent.collateral += remaining_margin;
    agent.total_trades += 1;
    
    // Reward liquidator
    liquidator_agent.collateral += liquidator_reward;
    
    // TODO: Send insurance fund portion to insurance vault
    
    // Reset position
    position.size = 0;
    position.entry_price = 0;
    position.margin = 0;
    position.liquidation_price = 0;
    position.unrealized_pnl = 0;
    position.updated_at = clock.unix_timestamp;
    
    msg!(
        "Position liquidated: penalty={}, liquidator_reward={}, insurance={}",
        liquidation_penalty,
        liquidator_reward,
        insurance_fund
    );
    
    Ok(())
}
