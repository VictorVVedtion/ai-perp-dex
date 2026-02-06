"""
Asset Configuration - Single Source of Truth

所有资产白名单的唯一来源。
server.py / position_manager.py / external_router.py 都从这里引用。
新增/删除资产只需修改此文件。
"""

# 支持的永续合约资产
SUPPORTED_ASSETS = {
    # 主流
    "BTC-PERP",
    "ETH-PERP",
    "SOL-PERP",
    # Meme
    "DOGE-PERP",
    "PEPE-PERP",
    "WIF-PERP",
    # L2
    "ARB-PERP",
    "OP-PERP",
    "SUI-PERP",
    # DeFi
    "AVAX-PERP",
    "LINK-PERP",
    "AAVE-PERP",
}

# Hyperliquid 资产映射 (asset -> HL symbol)
HYPERLIQUID_ASSET_MAP = {
    "BTC-PERP": "BTC",
    "ETH-PERP": "ETH",
    "SOL-PERP": "SOL",
    "DOGE-PERP": "DOGE",
    "PEPE-PERP": "PEPE",
    "WIF-PERP": "WIF",
    "ARB-PERP": "ARB",
    "OP-PERP": "OP",
    "SUI-PERP": "SUI",
    "AVAX-PERP": "AVAX",
    "LINK-PERP": "LINK",
    "AAVE-PERP": "AAVE",
}


def validate_asset(asset: str) -> bool:
    """验证资产是否支持"""
    return asset in SUPPORTED_ASSETS


def get_hl_symbol(asset: str) -> str:
    """获取 Hyperliquid 交易对符号"""
    return HYPERLIQUID_ASSET_MAP.get(asset, "")
