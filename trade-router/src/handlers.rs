use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use chrono::{Duration, Utc};
use std::sync::Arc;
use uuid::Uuid;

use crate::state::AppState;
use crate::types::{
    AcceptQuote, AgentInfo, AgentPublicInfo, AgentStats, ApiResponse, ClosePosition, CreateQuote,
    CreateTradeRequest, Market, MarketInfo, PaginatedResponse, PaginationParams, Position,
    PositionWithPnl, Quote, RegisterAgent, RiskLimits, SetRiskLimits, TradeRequest,
};

/// POST /trade/request - 发起交易请求
pub async fn create_trade_request(
    State(state): State<Arc<AppState>>,
    Json(input): Json<CreateTradeRequest>,
) -> Result<Json<ApiResponse<TradeRequest>>, (StatusCode, Json<ApiResponse<()>>)> {
    // 检查风险限额
    if let Err(e) = state.check_risk_limits(&input.agent_id, input.size_usdc, input.leverage) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::err(format!("Risk limit exceeded: {}", e))),
        ));
    }
    
    let request = TradeRequest {
        id: Uuid::new_v4(),
        agent_id: input.agent_id,
        market: input.market,
        side: input.side,
        size_usdc: input.size_usdc,
        leverage: input.leverage,
        max_funding_rate: input.max_funding_rate,
        expires_at: Utc::now() + Duration::seconds(input.expires_in as i64),
        created_at: Utc::now(),
    };
    
    state.add_request(request.clone());
    
    Ok(Json(ApiResponse::ok(request)))
}

/// POST /trade/quote - 提交报价
pub async fn create_quote(
    State(state): State<Arc<AppState>>,
    Json(input): Json<CreateQuote>,
) -> Result<Json<ApiResponse<Quote>>, (StatusCode, Json<ApiResponse<()>>)> {
    // 验证请求是否存在
    if !state.requests.contains_key(&input.request_id) {
        return Err((
            StatusCode::NOT_FOUND,
            Json(ApiResponse::err("Trade request not found")),
        ));
    }
    
    let quote = Quote {
        id: Uuid::new_v4(),
        request_id: input.request_id,
        agent_id: input.agent_id,
        funding_rate: input.funding_rate,
        collateral_usdc: input.collateral_usdc,
        valid_until: Utc::now() + Duration::seconds(input.valid_for as i64),
        created_at: Utc::now(),
    };
    
    if let Err(e) = state.add_quote(quote.clone()) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::err(e)),
        ));
    }
    
    Ok(Json(ApiResponse::ok(quote)))
}

/// POST /trade/accept - 接受报价
pub async fn accept_quote(
    State(state): State<Arc<AppState>>,
    Json(input): Json<AcceptQuote>,
) -> Result<Json<ApiResponse<Position>>, (StatusCode, Json<ApiResponse<()>>)> {
    match state.accept_quote(input.request_id, input.quote_id) {
        Ok(position) => {
            // 链上结算 (异步，不阻塞响应)
            let settlement = state.settlement.clone();
            let market = format!("{:?}", position.market);
            let trader = position.trader_agent.clone();
            let size = (position.size_usdc * 1000.0) as i64; // Convert to contract units
            let price = position.entry_price;
            
            tokio::spawn(async move {
                match settlement.settle_open_position(&trader, &market, size, price).await {
                    Ok(resp) => {
                        if resp.success {
                            tracing::info!("Position settled on-chain: {:?}", resp.signature);
                        } else {
                            tracing::warn!("On-chain settlement failed: {:?}", resp.error);
                        }
                    }
                    Err(e) => {
                        tracing::warn!("Settlement service error: {}", e);
                    }
                }
            });
            
            Ok(Json(ApiResponse::ok(position)))
        }
        Err(e) => Err((
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::err(e)),
        )),
    }
}

/// POST /trade/close - 平仓
pub async fn close_position(
    State(state): State<Arc<AppState>>,
    Json(input): Json<ClosePosition>,
) -> Result<Json<ApiResponse<serde_json::Value>>, (StatusCode, Json<ApiResponse<()>>)> {
    // 先获取仓位信息用于结算
    let position_info = state.positions.get(&input.position_id)
        .map(|p| (p.trader_agent.clone(), format!("{:?}", p.market)));
    
    match state.close_position(input.position_id, &input.agent_id) {
        Ok((pnl_trader, pnl_mm)) => {
            // 链上平仓结算 (异步)
            if let Some((trader, market)) = position_info {
                let settlement = state.settlement.clone();
                let current_price = state.prices.get(&crate::types::Market::BtcPerp)
                    .map(|p| *p)
                    .unwrap_or(97000.0);
                
                tokio::spawn(async move {
                    match settlement.settle_close_position(&trader, &market, current_price).await {
                        Ok(resp) => {
                            if resp.success {
                                tracing::info!("Close settled on-chain: {:?}", resp.signature);
                            } else {
                                tracing::warn!("On-chain close settlement failed: {:?}", resp.error);
                            }
                        }
                        Err(e) => {
                            tracing::warn!("Settlement service error: {}", e);
                        }
                    }
                });
            }
            
            let data = serde_json::json!({
                "position_id": input.position_id,
                "pnl_trader": pnl_trader,
                "pnl_mm": pnl_mm,
                "status": "closed"
            });
            Ok(Json(ApiResponse::ok(data)))
        }
        Err(e) => Err((
            StatusCode::BAD_REQUEST,
            Json(ApiResponse::err(e)),
        )),
    }
}

/// GET /positions/:agent_id - 获取 Agent 的仓位
pub async fn get_positions(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Json<ApiResponse<Vec<Position>>> {
    let positions = state.get_agent_positions(&agent_id);
    Json(ApiResponse::ok(positions))
}

/// GET /positions/:agent_id/history - 获取 Agent 的历史仓位
pub async fn get_position_history(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
    Query(params): Query<PaginationParams>,
) -> Result<Json<ApiResponse<PaginatedResponse<PositionWithPnl>>>, StatusCode> {
    match state.get_closed_positions(&agent_id, params.limit, params.offset) {
        Ok((positions, total)) => {
            let response = PaginatedResponse {
                items: positions,
                total,
                limit: params.limit,
                offset: params.offset,
            };
            Ok(Json(ApiResponse::ok(response)))
        }
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

/// GET /requests - 获取所有活跃请求
pub async fn get_requests(
    State(state): State<Arc<AppState>>,
) -> Json<ApiResponse<Vec<TradeRequest>>> {
    let requests = state.get_active_requests();
    Json(ApiResponse::ok(requests))
}

/// GET /quotes/:request_id - 获取请求的报价
pub async fn get_quotes(
    State(state): State<Arc<AppState>>,
    Path(request_id): Path<Uuid>,
) -> Json<ApiResponse<Vec<Quote>>> {
    let quotes = state.get_quotes(request_id);
    Json(ApiResponse::ok(quotes))
}

/// GET /markets - 获取市场信息
pub async fn get_markets(
    State(state): State<Arc<AppState>>,
) -> Json<ApiResponse<Vec<MarketInfo>>> {
    let markets = vec![
        MarketInfo {
            market: Market::BtcPerp,
            current_price: state.prices.get(&Market::BtcPerp).map(|p| *p).unwrap_or(84000.0),
            funding_rate_24h: 0.01,
            open_interest: 1000000.0,
            volume_24h: 5000000.0,
        },
        MarketInfo {
            market: Market::EthPerp,
            current_price: state.prices.get(&Market::EthPerp).map(|p| *p).unwrap_or(2200.0),
            funding_rate_24h: 0.008,
            open_interest: 500000.0,
            volume_24h: 2000000.0,
        },
        MarketInfo {
            market: Market::SolPerp,
            current_price: state.prices.get(&Market::SolPerp).map(|p| *p).unwrap_or(130.0),
            funding_rate_24h: 0.012,
            open_interest: 200000.0,
            volume_24h: 800000.0,
        },
        MarketInfo {
            market: Market::DogePerp,
            current_price: state.prices.get(&Market::DogePerp).map(|p| *p).unwrap_or(0.18),
            funding_rate_24h: 0.015,
            open_interest: 100000.0,
            volume_24h: 400000.0,
        },
        MarketInfo {
            market: Market::AvaxPerp,
            current_price: state.prices.get(&Market::AvaxPerp).map(|p| *p).unwrap_or(22.0),
            funding_rate_24h: 0.011,
            open_interest: 150000.0,
            volume_24h: 600000.0,
        },
        MarketInfo {
            market: Market::LinkPerp,
            current_price: state.prices.get(&Market::LinkPerp).map(|p| *p).unwrap_or(14.0),
            funding_rate_24h: 0.009,
            open_interest: 120000.0,
            volume_24h: 500000.0,
        },
    ];
    Json(ApiResponse::ok(markets))
}

/// GET /health - 健康检查
pub async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "trade-router",
        "version": "0.1.0"
    }))
}

/// POST /agents/register - 注册新 Agent
pub async fn register_agent(
    State(state): State<Arc<AppState>>,
    Json(input): Json<RegisterAgent>,
) -> Json<ApiResponse<AgentInfo>> {
    let api_key = format!("ak_{}", Uuid::new_v4().to_string().replace("-", ""));
    
    let agent = AgentInfo {
        id: input.agent_id.clone(),
        api_key: api_key.clone(),
        name: input.name,
        is_mm: input.is_mm.unwrap_or(false),
        created_at: Utc::now(),
    };
    
    // Store in state (add agents map to AppState)
    state.register_agent(agent.clone());
    
    Json(ApiResponse::ok(agent))
}

/// GET /agents/:agent_id - 获取 Agent 信息
pub async fn get_agent(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Result<Json<ApiResponse<AgentPublicInfo>>, StatusCode> {
    if let Some(agent) = state.get_agent(&agent_id) {
        Ok(Json(ApiResponse::ok(AgentPublicInfo {
            id: agent.id,
            name: agent.name,
            is_mm: agent.is_mm,
            created_at: agent.created_at,
        })))
    } else {
        Err(StatusCode::NOT_FOUND)
    }
}

/// GET /agents/:agent_id/stats - 获取 Agent 交易统计
pub async fn get_agent_stats(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Result<Json<ApiResponse<AgentStats>>, StatusCode> {
    match state.get_agent_stats(&agent_id) {
        Ok(stats) => Ok(Json(ApiResponse::ok(stats))),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}

/// GET /positions/:agent_id/margin - 获取仓位保证金信息
pub async fn get_positions_margin(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Json<ApiResponse<Vec<crate::margin::PositionMarginInfo>>> {
    let config = crate::margin::MarginConfig::default();
    let positions = state.get_agent_positions(&agent_id);
    
    let margin_infos: Vec<_> = positions
        .iter()
        .filter(|p| p.status == crate::types::PositionStatus::Active)
        .map(|p| {
            let current_price = state.prices.get(&p.market).map(|pr| *pr).unwrap_or(p.entry_price);
            crate::margin::PositionMarginInfo::from_position(p, current_price, &config)
        })
        .collect();
    
    Json(ApiResponse::ok(margin_infos))
}

/// POST /agents/:agent_id/limits - 设置 Agent 风险限额
pub async fn set_agent_limits(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
    Json(input): Json<SetRiskLimits>,
) -> Result<Json<ApiResponse<RiskLimits>>, StatusCode> {
    // 检查 Agent 是否存在
    if state.get_agent(&agent_id).is_none() {
        return Err(StatusCode::NOT_FOUND);
    }
    
    // 获取当前限额或使用默认值
    let mut limits = state.get_agent_limits(&agent_id);
    
    // 更新提供的字段
    if let Some(v) = input.max_position_size {
        limits.max_position_size = v;
    }
    if let Some(v) = input.max_leverage {
        limits.max_leverage = v;
    }
    if let Some(v) = input.max_total_exposure {
        limits.max_total_exposure = v;
    }
    if let Some(v) = input.daily_loss_limit {
        limits.daily_loss_limit = v;
    }
    
    // 保存
    state.set_agent_limits(&agent_id, limits.clone());
    
    Ok(Json(ApiResponse::ok(limits)))
}

/// GET /agents/:agent_id/limits - 获取 Agent 风险限额
pub async fn get_agent_limits(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Result<Json<ApiResponse<RiskLimits>>, StatusCode> {
    // 检查 Agent 是否存在
    if state.get_agent(&agent_id).is_none() {
        return Err(StatusCode::NOT_FOUND);
    }
    
    let limits = state.get_agent_limits(&agent_id);
    Ok(Json(ApiResponse::ok(limits)))
}

// ========== MM Leaderboard ==========

pub async fn get_mm_leaderboard(
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    let leaderboard = crate::incentives::get_mm_leaderboard(state).await;
    
    Json(ApiResponse {
        success: true,
        data: Some(leaderboard),
        error: None,
    })
}
