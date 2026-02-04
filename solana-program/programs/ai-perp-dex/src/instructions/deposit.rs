use anchor_lang::prelude::*;
use anchor_spl::token_interface::{self, TokenAccount, TokenInterface, TransferChecked};
use crate::state::{Agent, Exchange};
use crate::errors::PerpError;

#[derive(Accounts)]
pub struct Deposit<'info> {
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
        constraint = agent.is_active @ PerpError::AgentNotActive
    )]
    pub agent: Account<'info, Agent>,
    
    #[account(
        mut,
        constraint = owner_token_account.owner == owner.key()
    )]
    pub owner_token_account: InterfaceAccount<'info, TokenAccount>,
    
    #[account(
        mut,
        constraint = vault.key() == exchange.vault @ PerpError::Unauthorized
    )]
    pub vault: InterfaceAccount<'info, TokenAccount>,
    
    /// CHECK: Mint account for transfer_checked
    pub mint: UncheckedAccount<'info>,
    
    pub token_program: Interface<'info, TokenInterface>,
}

pub fn handler(ctx: Context<Deposit>, amount: u64) -> Result<()> {
    // Transfer tokens from user to vault
    let transfer_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        TransferChecked {
            from: ctx.accounts.owner_token_account.to_account_info(),
            to: ctx.accounts.vault.to_account_info(),
            authority: ctx.accounts.owner.to_account_info(),
            mint: ctx.accounts.mint.to_account_info(),
        },
    );
    token_interface::transfer_checked(transfer_ctx, amount, 6)?;  // 6 decimals
    
    // Update agent collateral
    ctx.accounts.agent.collateral += amount;
    ctx.accounts.exchange.total_deposits += amount;
    
    msg!("Deposited {} USDC", amount);
    
    Ok(())
}
