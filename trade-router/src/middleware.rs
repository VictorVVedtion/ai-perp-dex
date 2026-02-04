//! Authentication middleware

use axum::{
    extract::State,
    http::{Request, StatusCode, header, HeaderMap},
    middleware::Next,
    response::{Response, IntoResponse},
    Json,
    body::Body,
};
use std::sync::Arc;

use crate::state::AppState;
use crate::types::{AgentInfo, ApiResponse};

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
