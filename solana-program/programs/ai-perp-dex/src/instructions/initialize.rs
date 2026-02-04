use anchor_lang::prelude::*;
use anchor_spl::token::{Mint, Token, TokenAccount};
use crate::state::Exchange;

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        init,
        payer = authority,
        space = Exchange::SIZE,
        seeds = [b"exchange"],
        bump
    )]
    pub exchange: Account<'info, Exchange>,
    
    /// USDC mint
    pub collateral_mint: Account<'info, Mint>,
    
    #[account(
        init,
        payer = authority,
        token::mint = collateral_mint,
        token::authority = exchange,
        seeds = [b"vault"],
        bump
    )]
    pub vault: Account<'info, TokenAccount>,
    
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn handler(ctx: Context<Initialize>, fee_rate_bps: u16) -> Result<()> {
    let exchange = &mut ctx.accounts.exchange;
    
    exchange.authority = ctx.accounts.authority.key();
    exchange.collateral_mint = ctx.accounts.collateral_mint.key();
    exchange.vault = ctx.accounts.vault.key();
    exchange.fee_rate_bps = fee_rate_bps;
    exchange.total_agents = 0;
    exchange.total_deposits = 0;
    exchange.total_open_interest = 0;
    exchange.bump = ctx.bumps.exchange;
    
    msg!("AI Perp DEX initialized with fee rate: {} bps", fee_rate_bps);
    
    Ok(())
}
