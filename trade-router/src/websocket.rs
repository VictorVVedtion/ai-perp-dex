use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::Response,
};
use futures::{SinkExt, StreamExt};
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{info, warn};

use crate::state::AppState;
use crate::types::WsMessage;

/// WebSocket 升级处理
pub async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<Arc<AppState>>,
) -> Response {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

/// 处理 WebSocket 连接
async fn handle_socket(socket: WebSocket, state: Arc<AppState>) {
    let (mut sender, mut receiver) = socket.split();
    
    // 订阅广播频道
    let mut broadcast_rx = state.broadcast_tx.subscribe();
    
    info!("New WebSocket connection established");
    
    // 发送欢迎消息
    let welcome = serde_json::json!({
        "type": "connected",
        "message": "Welcome to AI Perp DEX P2P Trading"
    });
    if sender.send(Message::Text(welcome.to_string().into())).await.is_err() {
        return;
    }
    
    // 发送当前活跃请求
    for req in state.get_active_requests() {
        let msg = WsMessage::TradeRequest(req);
        if let Ok(json) = serde_json::to_string(&msg) {
            if sender.send(Message::Text(json.into())).await.is_err() {
                return;
            }
        }
    }
    
    // 并发处理: 接收客户端消息 + 转发广播
    loop {
        tokio::select! {
            // 接收客户端消息
            msg = receiver.next() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        // 解析并处理客户端消息
                        if let Ok(ws_msg) = serde_json::from_str::<WsMessage>(&text) {
                            match ws_msg {
                                WsMessage::Subscribe { markets } => {
                                    info!("Client subscribed to markets: {:?}", markets);
                                    // TODO: 实现市场过滤
                                }
                                WsMessage::Unsubscribe { markets } => {
                                    info!("Client unsubscribed from markets: {:?}", markets);
                                }
                                _ => {}
                            }
                        }
                    }
                    Some(Ok(Message::Close(_))) => {
                        info!("WebSocket client disconnected");
                        break;
                    }
                    Some(Err(e)) => {
                        warn!("WebSocket error: {}", e);
                        break;
                    }
                    None => break,
                    _ => {}
                }
            }
            
            // 转发广播消息
            broadcast_msg = broadcast_rx.recv() => {
                match broadcast_msg {
                    Ok(ws_msg) => {
                        if let Ok(json) = serde_json::to_string(&ws_msg) {
                            if sender.send(Message::Text(json.into())).await.is_err() {
                                break;
                            }
                        }
                    }
                    Err(broadcast::error::RecvError::Lagged(n)) => {
                        warn!("WebSocket client lagged {} messages", n);
                    }
                    Err(_) => break,
                }
            }
        }
    }
    
    info!("WebSocket connection closed");
}
