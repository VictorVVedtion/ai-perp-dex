"""
AI Perp DEX - 异常类
"""

from typing import Optional, Dict, Any


class TradingHubError(Exception):
    """Base exception for Trading Hub SDK"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(TradingHubError):
    """API Key 无效或已过期"""
    
    def __init__(self, message: str = "Invalid or expired API key"):
        super().__init__(message, status_code=401)


class RateLimitError(TradingHubError):
    """请求频率超限"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class InsufficientBalanceError(TradingHubError):
    """余额不足"""
    
    def __init__(
        self,
        required: float,
        available: float,
        message: Optional[str] = None,
    ):
        msg = message or f"Insufficient balance: required ${required:.2f}, available ${available:.2f}"
        super().__init__(msg, status_code=400)
        self.required = required
        self.available = available


class InsufficientMarginError(TradingHubError):
    """保证金不足"""
    
    def __init__(
        self,
        required: float,
        available: float,
        message: Optional[str] = None,
    ):
        msg = message or f"Insufficient margin: required ${required:.2f}, available ${available:.2f}"
        super().__init__(msg, status_code=400)
        self.required = required
        self.available = available


class PositionNotFoundError(TradingHubError):
    """持仓不存在"""
    
    def __init__(self, position_id: str):
        super().__init__(f"Position not found: {position_id}", status_code=404)
        self.position_id = position_id


class InvalidParameterError(TradingHubError):
    """参数无效"""
    
    def __init__(self, param: str, value: Any, reason: str = ""):
        msg = f"Invalid parameter '{param}': {value}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg, status_code=400)
        self.param = param
        self.value = value


class NetworkError(TradingHubError):
    """网络错误"""
    
    def __init__(self, message: str = "Network error", original: Optional[Exception] = None):
        super().__init__(message, status_code=None)
        self.original = original


class ServerError(TradingHubError):
    """服务器错误"""
    
    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message, status_code=status_code)


class AssetNotFoundError(TradingHubError):
    """资产不支持"""
    
    def __init__(self, asset: str, supported: list = None):
        msg = f"Asset not supported: {asset}"
        if supported:
            msg += f". Supported: {', '.join(supported)}"
        super().__init__(msg, status_code=400)
        self.asset = asset
        self.supported = supported or []


class OrderRejectedError(TradingHubError):
    """订单被拒绝"""
    
    def __init__(self, reason: str, intent_id: Optional[str] = None):
        super().__init__(f"Order rejected: {reason}", status_code=400)
        self.reason = reason
        self.intent_id = intent_id


class RiskLimitError(TradingHubError):
    """风控限制"""
    
    def __init__(self, limit_type: str, current: float, max_allowed: float):
        msg = f"Risk limit exceeded: {limit_type} ({current:.2f} > {max_allowed:.2f})"
        super().__init__(msg, status_code=400)
        self.limit_type = limit_type
        self.current = current
        self.max_allowed = max_allowed


class WebSocketError(TradingHubError):
    """WebSocket 连接错误"""
    
    def __init__(self, message: str = "WebSocket connection error"):
        super().__init__(message, status_code=None)
