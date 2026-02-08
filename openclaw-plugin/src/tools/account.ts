import type { RiverbitClient } from "../client";
import type { ToolDefinition } from "../types";

export function createAccountTools(client: RiverbitClient): ToolDefinition[] {
  return [
    {
      name: "riverbit_get_positions",
      description:
        "Get your current open positions on Riverbit. Optionally include closed positions.",
      parameters: {
        type: "object",
        properties: {
          include_closed: {
            type: "boolean",
            default: false,
            description: "Include closed positions in the result",
          },
        },
      },
      execute: async (params) =>
        client.getPositions((params.include_closed as boolean) ?? false),
    },
  ];
}
