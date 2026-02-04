use anchor_lang::prelude::*;
use crate::state::{Agent, Exchange, Position, Market};
use crate::errors::PerpError;

#[derive(Accounts)]
#[instruction(market_index: u8)]
pub struct OpenPosition<'info> {
    /// Matching engine authority (signs this tx)
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
        bump = agent.bump,
        constraint = agent.is_active @ PerpError::AgentNotActive
    )]
    pub agent: Account<'info, Agent>,
    
    #[account(
        init_if_needed,
        payer = payer,
        space = Position::SIZE,
        seeds = [b"position", agent.key().as_ref(), &[market_index]],
        bump
    )]
    pub position: Account<'info, Position>,
    
    #[account(
        seeds = [b"market", &[market_index]],
        bump = market.bump,
        constraint = market.is_active @ PerpError::MarketNotActive
    )]
    pub market: Account<'info, Market>,
    
    #[account(mut)]
    pub payer: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<OpenPosition>,
    market_index: u8,
    size: i64,
    entry_price: u64,
) -> Result<()> {
    require!(size != 0, PerpError::InvalidSize);
    require!(entry_price > 0, PerpError::InvalidPrice);
    
    let agent = &mut ctx.accounts.agent;
    let position = &mut ctx.accounts.position;
    let market = &ctx.accounts.market;
    let clock = Clock::get()?;
    
    // Calculate required margin
    let notional = (size.abs() as u64)
        .checked_mul(entry_price)
        .ok_or(PerpError::MathOverflow)?
        / 1_000_000; // Adjust for price decimals
    
    let required_margin = notional
        .checked_mul(market.initial_margin_rate as u64)
        .ok_or(PerpError::MathOverflow)?
        / 10_000;
    
    require!(
        agent.collateral >= required_margin,
        PerpError::InsufficientCollateral
    );
    
    // Update or create position
    if position.size == 0 {
        // New position
        position.agent = agent.key();
        position.market_index = market_index;
        position.size = size;
        position.entry_price = entry_price;
        position.margin = required_margin;
        position.opened_at = clock.unix_timestamp;
        position.bump = ctx.bumps.position;
    } else {
        // Add to existing position
        // Calculate new average entry price
        let old_notional = (position.size.abs() as u64) * position.entry_price;
        let new_notional = (size.abs() as u64) * entry_price;
        let total_size = position.size + size;
        
        if total_size != 0 {
            position.entry_price = (old_notional + new_notional) / (total_size.abs() as u64);
        }
        position.size = total_size;
        position.margin += required_margin;
    }
    
    // Calculate liquidation price
    position.liquidation_price = calculate_liquidation_price(
        position.entry_price,
        position.size > 0,
        market.maintenance_margin_rate,
    );
    
    position.updated_at = clock.unix_timestamp;
    
    // Lock margin
    agent.collateral -= required_margin;
    
    msg!(
        "Opened position: size={}, price={}, margin={}",
        size,
        entry_price,
        required_margin
    );
    
    Ok(())
}

fn calculate_liquidation_price(entry_price: u64, is_long: bool, margin_rate: u16) -> u64 {
    let margin_factor = margin_rate as u64;
    
    if is_long {
        // Liq price = entry * (1 - margin_rate)
        entry_price * (10_000 - margin_factor) / 10_000
    } else {
        // Liq price = entry * (1 + margin_rate)
        entry_price * (10_000 + margin_factor) / 10_000
    }
}
