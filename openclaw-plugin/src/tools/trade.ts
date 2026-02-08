import type { RiverbitClient } from "../client";
import type { ToolDefinition } from "../types";
import { SUPPORTED_ASSETS } from "../types";

export function createTradeTools(client: RiverbitClient): ToolDefinition[] {
  return [
    {
      name: "riverbit_open_position",
      description:
        "Open a perpetual futures position on Riverbit. Supports 12 markets with up to 20x leverage.",
      parameters: {
        type: "object",
        required: ["asset", "side", "size_usdc"],
        properties: {
          asset: {
            type: "string",
            enum: [...SUPPORTED_ASSETS],
            description: "Trading pair (e.g. BTC-PERP)",
          },
          side: {
            type: "string",
            enum: ["long", "short"],
            description: "Trade direction",
          },
          size_usdc: {
            type: "number",
            minimum: 1,
            description: "Position size in USDC",
          },
          leverage: {
            type: "integer",
            minimum: 1,
            maximum: 20,
            default: 5,
            description: "Leverage multiplier (default 5x)",
          },
          reason: {
            type: "string",
            description: "Trading rationale (stored as Agent Thought)",
          },
        },
      },
      execute: async (params) => client.openPosition(params as any),
    },
    {
      name: "riverbit_close_position",
      description:
        "Close an open perpetual position on Riverbit. Always use this instead of opening a reverse position.",
      parameters: {
        type: "object",
        required: ["position_id"],
        properties: {
          position_id: {
            type: "string",
            description: "The position ID to close (e.g. pos_xxxx)",
          },
        },
      },
      execute: async (params) =>
        client.closePosition(params.position_id as string),
    },
  ];
}
