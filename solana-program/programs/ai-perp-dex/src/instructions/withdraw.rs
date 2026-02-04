use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use crate::state::{Agent, Exchange};
use crate::errors::PerpError;

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [b"exchange"],
        bump = exchange.bump
    )]
    pub exchange: Account<'info, Exchange>,
    
    #[account(
        mut,
        seeds = [b"agent", owner.key().as_ref()],
        bump = agent.bump,
        constraint = agent.owner == owner.key() @ PerpError::Unauthorized,
        constraint = agent.is_active @ PerpError::AgentNotActive
    )]
    pub agent: Account<'info, Agent>,
    
    #[account(mut)]
    pub owner_token_account: Account<'info, TokenAccount>,
    
    #[account(
        mut,
        seeds = [b"vault"],
        bump
    )]
    pub vault: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

pub fn handler(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
    let agent = &mut ctx.accounts.agent;
    
    // Check sufficient balance
    require!(
        agent.collateral >= amount,
        PerpError::InsufficientCollateral
    );
    
    // TODO: Check margin requirements for open positions
    
    // Transfer tokens from vault to user
    let exchange_seeds = &[b"exchange".as_ref(), &[ctx.accounts.exchange.bump]];
    let signer_seeds = &[&exchange_seeds[..]];
    
    let transfer_ctx = CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from: ctx.accounts.vault.to_account_info(),
            to: ctx.accounts.owner_token_account.to_account_info(),
            authority: ctx.accounts.exchange.to_account_info(),
        },
        signer_seeds,
    );
    token::transfer(transfer_ctx, amount)?;
    
    // Update balances
    agent.collateral -= amount;
    ctx.accounts.exchange.total_deposits -= amount;
    
    msg!("Withdrew {} USDC", amount);
    
    Ok(())
}
