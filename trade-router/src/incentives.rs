//! MM Incentives - 激励做市商提供流动性

use std::sync::Arc;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

use crate::state::AppState;

/// MM 统计数据
#[derive(Clone, Serialize, Deserialize, Default)]
pub struct MmStats {
    pub agent_id: String,
    pub total_volume: f64,
    pub total_quotes: u64,
    pub filled_quotes: u64,
    pub total_points: f64,
    pub fees_earned: f64,
    pub rank: u32,
}

impl MmStats {
    pub fn fill_rate(&self) -> f64 {
        if self.total_quotes == 0 {
            0.0
        } else {
            self.filled_quotes as f64 / self.total_quotes as f64
        }
    }
}

/// 获取 MM 排行榜
pub async fn get_mm_leaderboard(state: Arc<AppState>) -> Vec<MmStats> {
    let mut stats: HashMap<String, MmStats> = HashMap::new();
    
    // 统计成交量 (从 positions)
    for entry in state.positions.iter() {
        let pos = entry.value();
        let mm_stats = stats.entry(pos.mm_agent.clone())
            .or_insert_with(|| MmStats {
                agent_id: pos.mm_agent.clone(),
                ..Default::default()
            });
        
        mm_stats.total_volume += pos.size_usdc;
        mm_stats.filled_quotes += 1;
        mm_stats.total_points += pos.size_usdc / 1000.0 * 10.0;  // 10 points per $1k
    }
    
    // 统计报价数 (从 quotes)
    for entry in state.quotes.iter() {
        for quote in entry.value().iter() {
            let mm_stats = stats.entry(quote.agent_id.clone())
                .or_insert_with(|| MmStats {
                    agent_id: quote.agent_id.clone(),
                    ..Default::default()
                });
            mm_stats.total_quotes += 1;
            mm_stats.total_points += 1.0;  // 1 point per quote
        }
    }
    
    // 排序
    let mut result: Vec<_> = stats.into_values().collect();
    result.sort_by(|a, b| b.total_points.partial_cmp(&a.total_points).unwrap());
    
    // 设置排名
    for (i, s) in result.iter_mut().enumerate() {
        s.rank = (i + 1) as u32;
    }
    
    result
}
