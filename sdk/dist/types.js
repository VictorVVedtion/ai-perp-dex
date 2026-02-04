"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ErrorMessages = exports.AiPerpDexError = exports.Side = exports.MarketIndex = void 0;
// ============================================================================
// Enum Types
// ============================================================================
var MarketIndex;
(function (MarketIndex) {
    MarketIndex[MarketIndex["BTC"] = 0] = "BTC";
    MarketIndex[MarketIndex["ETH"] = 1] = "ETH";
    MarketIndex[MarketIndex["SOL"] = 2] = "SOL";
})(MarketIndex || (exports.MarketIndex = MarketIndex = {}));
var Side;
(function (Side) {
    Side["Long"] = "long";
    Side["Short"] = "short";
})(Side || (exports.Side = Side = {}));
// ============================================================================
// Error Types
// ============================================================================
var AiPerpDexError;
(function (AiPerpDexError) {
    AiPerpDexError[AiPerpDexError["InsufficientCollateral"] = 6000] = "InsufficientCollateral";
    AiPerpDexError[AiPerpDexError["PositionTooLarge"] = 6001] = "PositionTooLarge";
    AiPerpDexError[AiPerpDexError["LeverageTooHigh"] = 6002] = "LeverageTooHigh";
    AiPerpDexError[AiPerpDexError["NotLiquidatable"] = 6003] = "NotLiquidatable";
    AiPerpDexError[AiPerpDexError["MarketNotActive"] = 6004] = "MarketNotActive";
    AiPerpDexError[AiPerpDexError["AgentNotActive"] = 6005] = "AgentNotActive";
    AiPerpDexError[AiPerpDexError["InvalidPrice"] = 6006] = "InvalidPrice";
    AiPerpDexError[AiPerpDexError["InvalidSize"] = 6007] = "InvalidSize";
    AiPerpDexError[AiPerpDexError["NoPosition"] = 6008] = "NoPosition";
    AiPerpDexError[AiPerpDexError["Unauthorized"] = 6009] = "Unauthorized";
    AiPerpDexError[AiPerpDexError["MathOverflow"] = 6010] = "MathOverflow";
    AiPerpDexError[AiPerpDexError["InvalidMarketIndex"] = 6011] = "InvalidMarketIndex";
    AiPerpDexError[AiPerpDexError["NameTooLong"] = 6012] = "NameTooLong";
    AiPerpDexError[AiPerpDexError["InsufficientMargin"] = 6013] = "InsufficientMargin";
})(AiPerpDexError || (exports.AiPerpDexError = AiPerpDexError = {}));
exports.ErrorMessages = {
    [AiPerpDexError.InsufficientCollateral]: "Insufficient collateral for this operation",
    [AiPerpDexError.PositionTooLarge]: "Position size exceeds maximum allowed",
    [AiPerpDexError.LeverageTooHigh]: "Leverage exceeds maximum allowed",
    [AiPerpDexError.NotLiquidatable]: "Position is not liquidatable",
    [AiPerpDexError.MarketNotActive]: "Market is not active",
    [AiPerpDexError.AgentNotActive]: "Agent is not active",
    [AiPerpDexError.InvalidPrice]: "Invalid price",
    [AiPerpDexError.InvalidSize]: "Invalid size",
    [AiPerpDexError.NoPosition]: "No position to close",
    [AiPerpDexError.Unauthorized]: "Unauthorized",
    [AiPerpDexError.MathOverflow]: "Math overflow",
    [AiPerpDexError.InvalidMarketIndex]: "Invalid market index",
    [AiPerpDexError.NameTooLong]: "Agent name too long",
    [AiPerpDexError.InsufficientMargin]: "Withdrawal would leave insufficient margin",
};
//# sourceMappingURL=types.js.map