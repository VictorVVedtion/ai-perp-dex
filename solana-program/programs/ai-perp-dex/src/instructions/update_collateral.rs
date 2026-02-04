use anchor_lang::prelude::*;
use anchor_spl::token_interface::{Mint, TokenAccount, TokenInterface};
use crate::state::Exchange;

/// Update collateral mint and create new vault
#[derive(Accounts)]
pub struct UpdateCollateral<'info> {
    /// Authority (must be exchange authority)
    #[account(mut)]
    pub authority: Signer<'info>,
    
    /// Exchange account
    #[account(
        mut,
        seeds = [b"exchange"],
        bump = exchange.bump,
        has_one = authority,
    )]
    pub exchange: Account<'info, Exchange>,
    
    /// New collateral mint
    pub new_collateral_mint: InterfaceAccount<'info, Mint>,
    
    /// New vault (will be initialized)
    #[account(
        init,
        payer = authority,
        token::mint = new_collateral_mint,
        token::authority = exchange,
        seeds = [b"vault", new_collateral_mint.key().as_ref()],
        bump
    )]
    pub new_vault: InterfaceAccount<'info, TokenAccount>,
    
    pub system_program: Program<'info, System>,
    pub token_program: Interface<'info, TokenInterface>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn handler(ctx: Context<UpdateCollateral>) -> Result<()> {
    let exchange = &mut ctx.accounts.exchange;
    
    // Update to new collateral mint and vault
    exchange.collateral_mint = ctx.accounts.new_collateral_mint.key();
    exchange.vault = ctx.accounts.new_vault.key();
    
    msg!("Collateral updated to mint: {}", exchange.collateral_mint);
    msg!("New vault: {}", exchange.vault);
    
    Ok(())
}
