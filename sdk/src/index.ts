// Main client
export { AiPerpDexClient } from "./client";

// Types
export {
  // Account types
  Agent,
  Exchange,
  Market,
  Position,
  // Info types (parsed)
  AgentInfo,
  ExchangeInfo,
  MarketInfo,
  PositionInfo,
  // Enums
  MarketIndex,
  Side,
  AiPerpDexError,
  ErrorMessages,
  // Options
  TxOptions,
  OpenPositionParams,
  ClosePositionParams,
} from "./types";

// PDAs
export {
  PROGRAM_ID,
  getExchangePDA,
  getVaultPDA,
  getAgentPDA,
  getPositionPDA,
  getMarketPDA,
  getAgentPDAs,
  getCorePDAs,
} from "./pdas";

// Re-export useful Solana/Anchor types
export { PublicKey, Keypair, Connection } from "@solana/web3.js";
export { BN, Wallet } from "@coral-xyz/anchor";
