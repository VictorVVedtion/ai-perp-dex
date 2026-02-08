import type { RiverbitClient } from "../client";
import type { ToolDefinition } from "../types";

export function createMarketTools(client: RiverbitClient): ToolDefinition[] {
  return [
    {
      name: "riverbit_get_price",
      description:
        "Get the current price for a trading pair on Riverbit.",
      parameters: {
        type: "object",
        required: ["asset"],
        properties: {
          asset: {
            type: "string",
            description: "Asset name (e.g. BTC-PERP, ETH, SOL)",
          },
        },
      },
      execute: async (params) =>
        client.getPrice(params.asset as string),
    },
    {
      name: "riverbit_get_candles",
      description:
        "Get OHLCV candlestick data for a trading pair on Riverbit. Useful for technical analysis.",
      parameters: {
        type: "object",
        required: ["asset"],
        properties: {
          asset: {
            type: "string",
            description: "Asset name (e.g. BTC-PERP)",
          },
          interval: {
            type: "string",
            enum: ["1m", "5m", "15m", "1h", "4h", "1d"],
            default: "1h",
            description: "Candle interval",
          },
          limit: {
            type: "integer",
            minimum: 1,
            maximum: 500,
            default: 100,
            description: "Number of candles to return",
          },
        },
      },
      execute: async (params) =>
        client.getCandles(
          params.asset as string,
          (params.interval as string) ?? "1h",
          (params.limit as number) ?? 100,
        ),
    },
  ];
}
