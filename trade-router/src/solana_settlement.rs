//! Solana 链上结算模块
//! 
//! 调用 AI Perp DEX 合约进行链上结算

use anyhow::{Result, anyhow};
use solana_client::rpc_client::RpcClient;
use solana_sdk::{
    commitment_config::CommitmentConfig,
    instruction::{AccountMeta, Instruction},
    pubkey::Pubkey,
    signature::{Keypair, Signer},
    transaction::Transaction,
    system_program,
};
use std::str::FromStr;
use tracing::{info, error};

/// Devnet Program ID
pub const PROGRAM_ID: &str = "AHjGBth6uAKVipLGnooZ9GYn7vwSKPJLX4Lq7Hio3CjT";

/// Token Program ID
pub const TOKEN_PROGRAM: &str = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";

/// 链上结算配置
#[derive(Clone)]
pub struct SettlementConfig {
    pub rpc_url: String,
    pub program_id: Pubkey,
    pub authority_keypair: Option<Keypair>,
}

impl Default for SettlementConfig {
    fn default() -> Self {
        Self {
            rpc_url: "https://api.devnet.solana.com".to_string(),
            program_id: Pubkey::from_str(PROGRAM_ID).unwrap(),
            authority_keypair: None,
        }
    }
}

/// 链上结算客户端
pub struct SettlementClient {
    rpc: RpcClient,
    config: SettlementConfig,
}

impl SettlementClient {
    pub fn new(config: SettlementConfig) -> Self {
        let rpc = RpcClient::new_with_commitment(
            config.rpc_url.clone(),
            CommitmentConfig::confirmed(),
        );
        Self { rpc, config }
    }

    /// 查找 PDA
    fn find_pda(&self, seeds: &[&[u8]]) -> (Pubkey, u8) {
        Pubkey::find_program_address(seeds, &self.config.program_id)
    }

    /// 获取 Exchange PDA
    pub fn get_exchange_pda(&self) -> Pubkey {
        self.find_pda(&[b"exchange"]).0
    }

    /// 获取 Agent PDA
    pub fn get_agent_pda(&self, owner: &Pubkey) -> Pubkey {
        self.find_pda(&[b"agent", owner.as_ref()]).0
    }

    /// 获取 Market PDA
    pub fn get_market_pda(&self, market_index: u8) -> Pubkey {
        self.find_pda(&[b"market", &[market_index]]).0
    }

    /// 获取 Position PDA
    pub fn get_position_pda(&self, agent: &Pubkey, market_index: u8) -> Pubkey {
        self.find_pda(&[b"position", agent.as_ref(), &[market_index]]).0
    }

    /// 查询 Agent 抵押金余额
    pub async fn get_agent_collateral(&self, owner: &Pubkey) -> Result<u64> {
        let agent_pda = self.get_agent_pda(owner);
        let account = self.rpc.get_account(&agent_pda)?;
        
        if account.data.len() >= 80 {
            let collateral = u64::from_le_bytes(
                account.data[72..80].try_into()?
            );
            Ok(collateral)
        } else {
            Err(anyhow!("Invalid agent account data"))
        }
    }

    /// 查询链上仓位
    pub async fn get_position(&self, owner: &Pubkey, market_index: u8) -> Result<OnChainPosition> {
        let agent_pda = self.get_agent_pda(owner);
        let position_pda = self.get_position_pda(&agent_pda, market_index);
        
        let account = self.rpc.get_account(&position_pda)?;
        
        if account.data.len() >= 90 {
            let size = i64::from_le_bytes(account.data[41..49].try_into()?);
            let entry_price = u64::from_le_bytes(account.data[49..57].try_into()?);
            let liquidation_price = u64::from_le_bytes(account.data[57..65].try_into()?);
            let margin = u64::from_le_bytes(account.data[65..73].try_into()?);
            
            Ok(OnChainPosition {
                size,
                entry_price,
                liquidation_price,
                margin,
            })
        } else {
            Err(anyhow!("Invalid position account data"))
        }
    }

    /// 链上开仓结算
    pub async fn settle_open_position(
        &self,
        owner: &Pubkey,
        market_index: u8,
        size: i64,
        entry_price: u64,
    ) -> Result<String> {
        let authority = self.config.authority_keypair.as_ref()
            .ok_or_else(|| anyhow!("No authority keypair configured"))?;
        
        // PDAs
        let exchange_pda = self.get_exchange_pda();
        let agent_pda = self.get_agent_pda(owner);
        let market_pda = self.get_market_pda(market_index);
        let position_pda = self.get_position_pda(&agent_pda, market_index);
        
        // 构建指令数据
        // discriminator (8) + market_index (1) + size (8) + entry_price (8)
        let mut data = vec![135, 128, 47, 77, 15, 152, 240, 49]; // open_position discriminator
        data.push(market_index);
        data.extend_from_slice(&size.to_le_bytes());
        data.extend_from_slice(&entry_price.to_le_bytes());
        
        let ix = Instruction {
            program_id: self.config.program_id,
            accounts: vec![
                AccountMeta::new_readonly(authority.pubkey(), true),
                AccountMeta::new_readonly(exchange_pda, false),
                AccountMeta::new(agent_pda, false),
                AccountMeta::new(position_pda, false),
                AccountMeta::new(market_pda, false),
                AccountMeta::new(authority.pubkey(), true),
                AccountMeta::new_readonly(system_program::id(), false),
            ],
            data,
        };
        
        let recent_blockhash = self.rpc.get_latest_blockhash()?;
        let tx = Transaction::new_signed_with_payer(
            &[ix],
            Some(&authority.pubkey()),
            &[authority],
            recent_blockhash,
        );
        
        let signature = self.rpc.send_and_confirm_transaction(&tx)?;
        info!("Open position settled on-chain: {}", signature);
        
        Ok(signature.to_string())
    }

    /// 链上平仓结算
    pub async fn settle_close_position(
        &self,
        owner: &Pubkey,
        market_index: u8,
        exit_price: u64,
    ) -> Result<String> {
        let authority = self.config.authority_keypair.as_ref()
            .ok_or_else(|| anyhow!("No authority keypair configured"))?;
        
        // PDAs
        let exchange_pda = self.get_exchange_pda();
        let agent_pda = self.get_agent_pda(owner);
        let market_pda = self.get_market_pda(market_index);
        let position_pda = self.get_position_pda(&agent_pda, market_index);
        
        // 构建指令数据
        let mut data = vec![123, 134, 81, 0, 49, 68, 98, 98]; // close_position discriminator
        data.push(market_index);
        data.extend_from_slice(&exit_price.to_le_bytes());
        
        let ix = Instruction {
            program_id: self.config.program_id,
            accounts: vec![
                AccountMeta::new_readonly(authority.pubkey(), true),
                AccountMeta::new(exchange_pda, false),
                AccountMeta::new(agent_pda, false),
                AccountMeta::new(position_pda, false),
                AccountMeta::new(market_pda, false),
            ],
            data,
        };
        
        let recent_blockhash = self.rpc.get_latest_blockhash()?;
        let tx = Transaction::new_signed_with_payer(
            &[ix],
            Some(&authority.pubkey()),
            &[authority],
            recent_blockhash,
        );
        
        let signature = self.rpc.send_and_confirm_transaction(&tx)?;
        info!("Close position settled on-chain: {}", signature);
        
        Ok(signature.to_string())
    }
}

/// 链上仓位数据
#[derive(Debug, Clone)]
pub struct OnChainPosition {
    pub size: i64,
    pub entry_price: u64,
    pub liquidation_price: u64,
    pub margin: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pda_derivation() {
        let config = SettlementConfig::default();
        let client = SettlementClient::new(config);
        
        let exchange = client.get_exchange_pda();
        assert_eq!(
            exchange.to_string(),
            "C857rEivZuX2PeSfv6v8U8vJnjQzgdTJ4UqWR9Qv18sW"
        );
    }
}
