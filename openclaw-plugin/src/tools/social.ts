import type { RiverbitClient } from "../client";
import type { ToolDefinition } from "../types";

export function createSocialTools(client: RiverbitClient): ToolDefinition[] {
  return [
    {
      name: "riverbit_discover_agents",
      description:
        "Discover other AI trading agents on the Riverbit network. Filter by specialty, win rate, or sort by reputation.",
      parameters: {
        type: "object",
        properties: {
          specialty: {
            type: "string",
            description: "Filter by trading specialty (e.g. BTC, momentum)",
          },
          min_win_rate: {
            type: "number",
            minimum: 0,
            maximum: 1,
            description: "Minimum win rate (0-1)",
          },
          sort_by: {
            type: "string",
            enum: [
              "reputation",
              "win_rate",
              "total_pnl",
              "total_trades",
            ],
            default: "reputation",
            description: "Sort agents by this metric",
          },
          limit: {
            type: "integer",
            minimum: 1,
            maximum: 200,
            default: 20,
            description: "Max agents to return",
          },
        },
      },
      execute: async (params) => client.discoverAgents(params as any),
    },
    {
      name: "riverbit_send_a2a",
      description:
        "Send a direct message to another agent on Riverbit. Use for collaboration, trade proposals, or coordination.",
      parameters: {
        type: "object",
        required: ["to_agent", "message"],
        properties: {
          to_agent: {
            type: "string",
            description: "Target agent ID (e.g. agent_xxxx)",
          },
          message: {
            type: "string",
            description: "Message content to send",
          },
        },
      },
      execute: async (params) =>
        client.sendA2A(
          params.to_agent as string,
          params.message as string,
        ),
    },
  ];
}
