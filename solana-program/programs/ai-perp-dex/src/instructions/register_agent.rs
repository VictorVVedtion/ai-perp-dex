use anchor_lang::prelude::*;
use crate::state::{Agent, Exchange};
use crate::errors::PerpError;

#[derive(Accounts)]
pub struct RegisterAgent<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [b"exchange"],
        bump = exchange.bump
    )]
    pub exchange: Account<'info, Exchange>,
    
    #[account(
        init,
        payer = owner,
        space = Agent::SIZE,
        seeds = [b"agent", owner.key().as_ref()],
        bump
    )]
    pub agent: Account<'info, Agent>,
    
    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<RegisterAgent>, name: String) -> Result<()> {
    require!(name.len() <= 32, PerpError::NameTooLong);
    
    let agent = &mut ctx.accounts.agent;
    let exchange = &mut ctx.accounts.exchange;
    let clock = Clock::get()?;
    
    agent.owner = ctx.accounts.owner.key();
    
    // Copy name into fixed array
    let name_bytes = name.as_bytes();
    let mut name_array = [0u8; 32];
    name_array[..name_bytes.len()].copy_from_slice(name_bytes);
    agent.name = name_array;
    
    agent.collateral = 0;
    agent.unrealized_pnl = 0;
    agent.realized_pnl = 0;
    agent.total_trades = 0;
    agent.win_count = 0;
    agent.registered_at = clock.unix_timestamp;
    agent.is_active = true;
    agent.bump = ctx.bumps.agent;
    
    exchange.total_agents += 1;
    
    msg!("Agent registered: {}", name);
    
    Ok(())
}
