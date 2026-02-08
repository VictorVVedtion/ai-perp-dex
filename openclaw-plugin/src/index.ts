/**
 * Riverbit OpenClaw Plugin
 *
 * Registers 8 trading tools that let any OpenClaw agent
 * interact with the Riverbit perpetual trading network.
 */

import { RiverbitClient } from "./client";
import { createTradeTools } from "./tools/trade";
import { createMarketTools } from "./tools/market";
import { createSignalTools } from "./tools/signal";
import { createAccountTools } from "./tools/account";
import { createSocialTools } from "./tools/social";
import type { OpenClawAPI, PluginConfig } from "./types";

export default function registerRiverbitPlugin(
  api: OpenClawAPI,
  config: PluginConfig,
): void {
  const baseUrl = config.baseUrl ?? process.env.RIVERBIT_BASE_URL ?? "https://api.riverbit.ai";
  const apiKey = config.apiKey ?? process.env.RIVERBIT_API_KEY ?? "";

  if (!apiKey) {
    throw new Error(
      "RIVERBIT_API_KEY is required. Set it in plugin config or environment variable.",
    );
  }

  const client = new RiverbitClient(apiKey, baseUrl);

  // Register all tools
  const tools = [
    ...createTradeTools(client),
    ...createMarketTools(client),
    ...createSignalTools(client),
    ...createAccountTools(client),
    ...createSocialTools(client),
  ];

  for (const tool of tools) {
    api.registerTool(tool);
  }
}

// Re-export for direct usage
export { RiverbitClient } from "./client";
export type { PluginConfig, ToolDefinition, OpenClawAPI } from "./types";
