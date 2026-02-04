import { PublicKey } from "@solana/web3.js";
import BN from "bn.js";

// ============================================================================
// Account Types
// ============================================================================

export interface Exchange {
  authority: PublicKey;
  collateralMint: PublicKey;
  vault: PublicKey;
  feeRateBps: number;
  totalAgents: BN;
  totalDeposits: BN;
  totalOpenInterest: BN;
  bump: number;
}

export interface Agent {
  owner: PublicKey;
  name: number[];
  collateral: BN;
  unrealizedPnl: BN;
  realizedPnl: BN;
  totalTrades: BN;
  winCount: BN;
  registeredAt: BN;
  isActive: boolean;
  bump: number;
}

export interface Position {
  agent: PublicKey;
  marketIndex: number;
  size: BN;
  entryPrice: BN;
  liquidationPrice: BN;
  margin: BN;
  unrealizedPnl: BN;
  openedAt: BN;
  updatedAt: BN;
  bump: number;
}

export interface Market {
  index: number;
  symbol: number[];
  oracle: PublicKey;
  initialMarginRate: number;
  maintenanceMarginRate: number;
  maxLeverage: number;
  longOpenInterest: BN;
  shortOpenInterest: BN;
  isActive: boolean;
  bump: number;
}

// ============================================================================
// Enum Types
// ============================================================================

export enum MarketIndex {
  BTC = 0,
  ETH = 1,
  SOL = 2,
}

export enum Side {
  Long = "long",
  Short = "short",
}

// ============================================================================
// Helper Types
// ============================================================================

export interface AgentInfo {
  address: PublicKey;
  owner: PublicKey;
  name: string;
  collateral: number; // USDC with decimals applied
  unrealizedPnl: number;
  realizedPnl: number;
  totalTrades: number;
  winCount: number;
  winRate: number;
  registeredAt: Date;
  isActive: boolean;
}

export interface PositionInfo {
  address: PublicKey;
  agent: PublicKey;
  market: MarketIndex;
  marketSymbol: string;
  side: Side;
  size: number;
  entryPrice: number;
  liquidationPrice: number;
  margin: number;
  unrealizedPnl: number;
  pnlPercent: number;
  openedAt: Date;
}

export interface MarketInfo {
  address: PublicKey;
  index: MarketIndex;
  symbol: string;
  oracle: PublicKey;
  initialMarginRate: number;
  maintenanceMarginRate: number;
  maxLeverage: number;
  longOpenInterest: number;
  shortOpenInterest: number;
  totalOpenInterest: number;
  isActive: boolean;
}

export interface ExchangeInfo {
  address: PublicKey;
  authority: PublicKey;
  collateralMint: PublicKey;
  vault: PublicKey;
  feeRateBps: number;
  feeRatePercent: number;
  totalAgents: number;
  totalDeposits: number;
  totalOpenInterest: number;
}

// ============================================================================
// Transaction Options
// ============================================================================

export interface TxOptions {
  skipPreflight?: boolean;
  maxRetries?: number;
  commitment?: "processed" | "confirmed" | "finalized";
}

export interface OpenPositionParams {
  marketIndex: MarketIndex;
  side: Side;
  size: number; // In base units (e.g., 0.1 BTC)
  price: number; // Entry price (6 decimals)
  leverage?: number;
}

export interface ClosePositionParams {
  marketIndex: MarketIndex;
  price: number; // Exit price
}

// ============================================================================
// Error Types
// ============================================================================

export enum AiPerpDexError {
  InsufficientCollateral = 6000,
  PositionTooLarge = 6001,
  LeverageTooHigh = 6002,
  NotLiquidatable = 6003,
  MarketNotActive = 6004,
  AgentNotActive = 6005,
  InvalidPrice = 6006,
  InvalidSize = 6007,
  NoPosition = 6008,
  Unauthorized = 6009,
  MathOverflow = 6010,
  InvalidMarketIndex = 6011,
  NameTooLong = 6012,
  InsufficientMargin = 6013,
}

export const ErrorMessages: Record<AiPerpDexError, string> = {
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
