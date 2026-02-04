//! Demo Market Maker - 内置自动报价，方便单人测试

use std::sync::Arc;
use std::time::Duration;
use tokio::time::interval;
use tracing::{info, debug};
use uuid::Uuid;

use crate::state::AppState;
use crate::types::{Quote, Side};

/// Demo MM 配置
#[derive(Clone)]
pub struct DemoMmConfig {
    pub agent_id: String,
    pub base_funding_rate: f64,
    pub collateral_ratio: f64,
    pub max_quote_size: f64,
    pub quote_valid_secs: u64,
    pub poll_interval_secs: u64,
    pub enabled: bool,
}

impl Default for DemoMmConfig {
    fn default() -> Self {
        Self {
            agent_id: "demo_mm_bot".to_string(),
            base_funding_rate: 0.008,  // 0.8% 基础，低于默认 1% 上限
            collateral_ratio: 0.15,
            max_quote_size: 10000.0,
            quote_valid_secs: 300,
            poll_interval_secs: 2,
            enabled: true,
        }
    }
}

/// 启动 Demo MM
pub async fn start_demo_mm(state: Arc<AppState>, config: DemoMmConfig) {
    if !config.enabled {
        info!("🤖 Demo MM disabled");
        return;
    }
    
    info!("🤖 Demo MM starting (agent_id: {})", config.agent_id);
    info!("   funding_rate: {}%, collateral: {}%", 
          config.base_funding_rate * 100.0,
          config.collateral_ratio * 100.0);
    
    let mut ticker = interval(Duration::from_secs(config.poll_interval_secs));
    
    loop {
        ticker.tick().await;
        
        // 遍历所有请求
        for entry in state.requests.iter() {
            let request_id = *entry.key();
            let request = entry.value();
            
            // 检查是否已有报价
            let has_demo_quote = state.quotes.get(&request_id)
                .map(|quotes| quotes.iter().any(|q| q.agent_id == config.agent_id))
                .unwrap_or(false);
            
            if has_demo_quote {
                continue;
            }
            
            // 检查大小
            if request.size_usdc > config.max_quote_size {
                debug!("Demo MM: skip {} (too large)", request_id);
                continue;
            }
            
            // 计算 funding rate
            let leverage_mult = 1.0 + (request.leverage as f64 - 1.0) * 0.05;
            let funding_rate = config.base_funding_rate * leverage_mult;
            
            // 检查上限
            if funding_rate > request.max_funding_rate {
                debug!("Demo MM: funding rate {} > max {}", funding_rate, request.max_funding_rate);
                continue;
            }
            
            // 计算抵押
            let collateral = request.size_usdc * config.collateral_ratio / request.leverage as f64;
            
            // 创建报价
            let quote = Quote {
                id: Uuid::new_v4(),
                request_id,
                agent_id: config.agent_id.clone(),
                funding_rate,
                collateral_usdc: collateral,
                valid_until: chrono::Utc::now() + chrono::Duration::seconds(config.quote_valid_secs as i64),
                created_at: chrono::Utc::now(),
            };
            
            info!("🤖 Demo MM quoted: {:?} {} ${} @ {}%",
                  request.market,
                  if request.side == Side::Long { "LONG" } else { "SHORT" },
                  request.size_usdc,
                  funding_rate * 100.0);
            
            // 存储报价
            state.quotes
                .entry(request_id)
                .or_insert_with(Vec::new)
                .push(quote);
        }
    }
}
