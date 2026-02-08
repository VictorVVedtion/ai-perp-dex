import type { RiverbitClient } from "../client";
import type { ToolDefinition } from "../types";
import { SUPPORTED_ASSETS } from "../types";

export function createSignalTools(client: RiverbitClient): ToolDefinition[] {
  return [
    {
      name: "riverbit_create_signal",
      description:
        "Create a price prediction signal on Riverbit. Other agents can fade (counter) your signal.",
      parameters: {
        type: "object",
        required: ["asset", "signal_type", "target_value", "stake_amount"],
        properties: {
          asset: {
            type: "string",
            enum: [...SUPPORTED_ASSETS],
            description: "Trading pair",
          },
          signal_type: {
            type: "string",
            enum: ["price_above", "price_below", "price_change"],
            description: "Type of price prediction",
          },
          target_value: {
            type: "number",
            minimum: 0,
            description: "Target price or change percentage",
          },
          stake_amount: {
            type: "number",
            minimum: 1,
            maximum: 1000,
            description: "USDC to wager on this prediction",
          },
          duration_hours: {
            type: "number",
            minimum: 1,
            maximum: 168,
            default: 24,
            description: "Prediction window in hours (default 24h)",
          },
        },
      },
      execute: async (params) => client.createSignal(params as any),
    },
    {
      name: "riverbit_fade_signal",
      description:
        "Fade (counter-bet) an existing signal on Riverbit. You bet the signal creator is wrong.",
      parameters: {
        type: "object",
        required: ["signal_id", "stake_amount"],
        properties: {
          signal_id: {
            type: "string",
            description: "Signal ID to fade (e.g. sig_xxxx)",
          },
          stake_amount: {
            type: "number",
            minimum: 1,
            maximum: 1000,
            description: "USDC to wager against the signal",
          },
        },
      },
      execute: async (params) =>
        client.fadeSignal(
          params.signal_id as string,
          params.stake_amount as number,
        ),
    },
  ];
}
