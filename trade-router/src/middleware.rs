//! Authentication and rate limiting middleware

use axum::{
    extract::{ConnectInfo, State},
    http::{Request, StatusCode, header, HeaderMap},
    middleware::Next,
    response::{Response, IntoResponse},
    Json,
    body::Body,
};
use dashmap::DashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};

use crate::state::AppState;
use crate::types::{AgentInfo, ApiResponse};

/// Rate limiter state per IP
#[derive(Debug, Clone)]
struct RateLimitEntry {
    count: u32,
    window_start: Instant,
}

/// Global rate limiter store
pub struct RateLimiter {
    entries: DashMap<String, RateLimitEntry>,
    max_requests: u32,
    window_duration: Duration,
}

impl RateLimiter {
    pub fn new(max_requests: u32, window_duration: Duration) -> Self {
        Self {
            entries: DashMap::new(),
            max_requests,
            window_duration,
        }
    }

    /// Check if request is allowed, returns (allowed, remaining, reset_seconds)
    pub fn check(&self, ip: &str) -> (bool, u32, u64) {
        let now = Instant::now();
        
        let mut entry = self.entries.entry(ip.to_string()).or_insert(RateLimitEntry {
            count: 0,
            window_start: now,
        });
        
        // Reset window if expired
        if now.duration_since(entry.window_start) >= self.window_duration {
            entry.count = 0;
            entry.window_start = now;
        }
        
        let reset_secs = self.window_duration
            .saturating_sub(now.duration_since(entry.window_start))
            .as_secs();
        
        if entry.count >= self.max_requests {
            return (false, 0, reset_secs);
        }
        
        entry.count += 1;
        let remaining = self.max_requests.saturating_sub(entry.count);
        
        (true, remaining, reset_secs)
    }
    
    /// Cleanup old entries (call periodically)
    pub fn cleanup(&self) {
        let now = Instant::now();
        self.entries.retain(|_, v| {
            now.duration_since(v.window_start) < self.window_duration * 2
        });
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        // 100 requests per minute per IP
        Self::new(100, Duration::from_secs(60))
    }
}

/// Rate limiting middleware
pub async fn rate_limit_middleware(
    State(limiter): State<Arc<RateLimiter>>,
    request: Request<Body>,
    next: Next,
) -> Response {
    // Extract client IP from connection info or headers
    let ip = extract_client_ip(&request);
    
    let (allowed, remaining, reset_secs) = limiter.check(&ip);
    
    if !allowed {
        return (
            StatusCode::TOO_MANY_REQUESTS,
            [
                ("X-RateLimit-Limit", "100"),
                ("X-RateLimit-Remaining", "0"),
                ("X-RateLimit-Reset", &reset_secs.to_string()),
                ("Retry-After", &reset_secs.to_string()),
            ],
            Json(ApiResponse::<()>::err("Rate limit exceeded. Try again later.")),
        ).into_response();
    }
    
    let mut response = next.run(request).await;
    
    // Add rate limit headers to response
    let headers = response.headers_mut();
    headers.insert("X-RateLimit-Limit", "100".parse().unwrap());
    headers.insert("X-RateLimit-Remaining", remaining.to_string().parse().unwrap());
    headers.insert("X-RateLimit-Reset", reset_secs.to_string().parse().unwrap());
    
    response
}

/// Extract client IP from request (checks X-Forwarded-For, X-Real-IP, then connection)
fn extract_client_ip(request: &Request<Body>) -> String {
    // Check X-Forwarded-For header (for proxies)
    if let Some(forwarded) = request.headers().get("X-Forwarded-For") {
        if let Ok(value) = forwarded.to_str() {
            if let Some(ip) = value.split(',').next() {
                return ip.trim().to_string();
            }
        }
    }
    
    // Check X-Real-IP header
    if let Some(real_ip) = request.headers().get("X-Real-IP") {
        if let Ok(ip) = real_ip.to_str() {
            return ip.to_string();
        }
    }
    
    // Fallback to connection info
    if let Some(connect_info) = request.extensions().get::<ConnectInfo<SocketAddr>>() {
        return connect_info.0.ip().to_string();
    }
    
    // Ultimate fallback
    "unknown".to_string()
}

/// Extract and validate API key from request
pub async fn auth_middleware(
    State(state): State<Arc<AppState>>,
    mut request: Request<Body>,
    next: Next,
) -> Response {
    // Extract API key from headers
    let api_key = request
        .headers()
        .get("X-API-Key")
        .or_else(|| request.headers().get(header::AUTHORIZATION))
        .and_then(|v| v.to_str().ok())
        .map(|s| s.trim_start_matches("Bearer ").to_string());
    
    // Try to validate
    if let Some(key) = api_key {
        if let Some(agent) = state.validate_api_key(&key) {
            // Insert validated agent into request extensions
            request.extensions_mut().insert(agent);
        }
    }
    
    // Continue - handlers decide if auth is required
    next.run(request).await
}

/// Helper to extract API key from headers
pub fn extract_api_key(headers: &HeaderMap) -> Option<String> {
    headers
        .get("X-API-Key")
        .or_else(|| headers.get(header::AUTHORIZATION))
        .and_then(|v| v.to_str().ok())
        .map(|s| s.trim_start_matches("Bearer ").to_string())
}

/// Require authenticated agent - returns error if not authenticated
pub fn require_auth_from_ext<B>(request: &Request<B>) -> Result<AgentInfo, Response> {
    request
        .extensions()
        .get::<AgentInfo>()
        .cloned()
        .ok_or_else(|| {
            (
                StatusCode::UNAUTHORIZED,
                Json(ApiResponse::<()>::err("API key required. Use X-API-Key header.")),
            ).into_response()
        })
}
