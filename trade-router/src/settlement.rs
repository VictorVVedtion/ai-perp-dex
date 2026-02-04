//! Settlement Service 客户端
//! 调用 Python Settlement Service 进行链上结算

use serde::{Deserialize, Serialize};
use tracing::{info, warn, error};

const SETTLEMENT_URL: &str = "http://localhost:8081";

#[derive(Debug, Clone)]
pub struct SettlementClient {
    client: reqwest::Client,
    base_url: String,
}

#[derive(Debug, Serialize)]
pub struct OpenPositionRequest {
    pub owner: String,
    pub market_index: u8,
    pub size: i64,
    pub entry_price: u64,
}

#[derive(Debug, Serialize)]
pub struct ClosePositionRequest {
    pub owner: String,
    pub market_index: u8,
    pub exit_price: u64,
}

#[derive(Debug, Deserialize)]
pub struct SettlementResponse {
    pub success: bool,
    pub signature: Option<String>,
    pub error: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CollateralResponse {
    pub agent: String,
    pub owner: String,
    pub collateral: u64,
    pub collateral_usd: f64,
}

impl SettlementClient {
    pub fn new() -> Self {
        Self {
            client: reqwest::Client::new(),
            base_url: SETTLEMENT_URL.to_string(),
        }
    }

    pub fn with_url(url: &str) -> Self {
        Self {
            client: reqwest::Client::new(),
            base_url: url.to_string(),
        }
    }

    /// 检查服务健康状态
    pub async fn health_check(&self) -> bool {
        match self.client.get(format!("{}/health", self.base_url)).send().await {
            Ok(resp) => resp.status().is_success(),
            Err(_) => false,
        }
    }

    /// 查询链上抵押金
    pub async fn get_collateral(&self, owner: &str) -> Result<CollateralResponse, String> {
        let url = format!("{}/collateral/{}", self.base_url, owner);
        
        let resp = self.client.get(&url)
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;
        
        resp.json::<CollateralResponse>()
            .await
            .map_err(|e| format!("Parse failed: {}", e))
    }

    /// 链上开仓结算
    pub async fn settle_open_position(
        &self,
        owner: &str,
        market: &str,
        size: i64,
        entry_price: f64,
    ) -> Result<SettlementResponse, String> {
        let market_index = match market {
            "BTC-PERP" => 0,
            "ETH-PERP" => 1,
            "SOL-PERP" => 2,
            _ => return Err(format!("Unknown market: {}", market)),
        };

        // Convert to on-chain format (6 decimals)
        let price_raw = (entry_price * 1_000_000.0) as u64;

        let req = OpenPositionRequest {
            owner: owner.to_string(),
            market_index,
            size,
            entry_price: price_raw,
        };

        info!("Settling open position on-chain: {:?}", req);

        let resp = self.client
            .post(format!("{}/settle/open", self.base_url))
            .json(&req)
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;

        let result: SettlementResponse = resp.json()
            .await
            .map_err(|e| format!("Parse failed: {}", e))?;

        if result.success {
            info!("Open position settled: {:?}", result.signature);
        } else {
            warn!("Settlement failed: {:?}", result.error);
        }

        Ok(result)
    }

    /// 链上平仓结算
    pub async fn settle_close_position(
        &self,
        owner: &str,
        market: &str,
        exit_price: f64,
    ) -> Result<SettlementResponse, String> {
        let market_index = match market {
            "BTC-PERP" => 0,
            "ETH-PERP" => 1,
            "SOL-PERP" => 2,
            _ => return Err(format!("Unknown market: {}", market)),
        };

        let price_raw = (exit_price * 1_000_000.0) as u64;

        let req = ClosePositionRequest {
            owner: owner.to_string(),
            market_index,
            exit_price: price_raw,
        };

        info!("Settling close position on-chain: {:?}", req);

        let resp = self.client
            .post(format!("{}/settle/close", self.base_url))
            .json(&req)
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;

        let result: SettlementResponse = resp.json()
            .await
            .map_err(|e| format!("Parse failed: {}", e))?;

        if result.success {
            info!("Close position settled: {:?}", result.signature);
        } else {
            warn!("Settlement failed: {:?}", result.error);
        }

        Ok(result)
    }
}

impl Default for SettlementClient {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check() {
        let client = SettlementClient::new();
        // This will fail if settlement service is not running
        let _ = client.health_check().await;
    }
}
