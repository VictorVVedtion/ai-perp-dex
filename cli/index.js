#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import inquirer from 'inquirer';
import fs from 'fs';
import path from 'path';
import os from 'os';
import crypto from 'crypto';

const API_URL = process.env.PERP_DEX_API || 'http://localhost:8082';
const CONFIG_DIR = path.join(os.homedir(), '.perp-dex');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

const LOGO = `
${chalk.hex('#FF6B35')('🦞')} ${chalk.bold.hex('#00D4AA')('AI PERP DEX')} ${chalk.gray('- Trading Exchange for Autonomous Agents')}
`;

const program = new Command();

function randomWallet() {
  return `0x${crypto.randomBytes(20).toString('hex')}`;
}

function formatAsset(asset) {
  const upper = asset.toUpperCase();
  return upper.includes('-') ? upper : `${upper}-PERP`;
}

function parseNumber(value, fieldName) {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    throw new Error(`${fieldName} must be a valid number`);
  }
  return n;
}

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    }
  } catch {
    // ignore broken config and fall back to empty
  }
  return {};
}

function saveConfig(config) {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
}

function saveAgentConfig({ agentId, apiKey, name }) {
  const current = loadConfig();
  saveConfig({
    ...current,
    agentId,
    apiKey,
    name: name || current.name,
    updatedAt: new Date().toISOString(),
  });
}

function requireAgentConfig() {
  const config = loadConfig();
  if (!config.agentId || !config.apiKey) {
    throw new Error('No local credentials found. Run: perp-dex deploy or perp-dex register');
  }
  return config;
}

async function parseApiError(res) {
  const raw = await res.text();
  if (!raw) return `HTTP ${res.status}`;

  try {
    const payload = JSON.parse(raw);
    const detail = payload.detail ?? payload.error ?? payload.message;

    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object') {
      if (typeof detail.message === 'string') return detail.message;
      return JSON.stringify(detail);
    }
    return JSON.stringify(payload);
  } catch {
    return raw;
  }
}

async function parseApiSuccess(res) {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

async function api(endpoint, options = {}, { includeAuth = true } = {}) {
  const config = loadConfig();
  const headers = {
    'Content-Type': 'application/json',
    ...(includeAuth && config.apiKey && { 'X-API-Key': config.apiKey }),
    ...options.headers,
  };

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const message = await parseApiError(res);
    throw new Error(message);
  }

  return parseApiSuccess(res);
}

async function registerAgent({ name, wallet, bio }) {
  return api('/agents/register', {
    method: 'POST',
    body: JSON.stringify({
      wallet_address: wallet,
      display_name: name,
      bio: bio || undefined,
    }),
  }, { includeAuth: false });
}

async function depositFunds(agentId, amount) {
  return api('/deposit', {
    method: 'POST',
    body: JSON.stringify({
      agent_id: agentId,
      amount,
    }),
  });
}

function buildRuntimePayload(options) {
  const markets = String(options.markets || 'BTC-PERP,ETH-PERP')
    .split(',')
    .map((m) => m.trim())
    .filter(Boolean)
    .map(formatAsset);

  return {
    heartbeat_interval: Math.max(5, Math.floor(parseNumber(options.heartbeat, 'heartbeat'))),
    min_confidence: Math.max(0, Math.min(1, parseNumber(options.minConfidence, 'min-confidence'))),
    max_position_size: Math.max(1, parseNumber(options.maxPosition, 'max-position')),
    strategy: String(options.strategy || 'momentum'),
    markets,
    auto_broadcast: options.autoBroadcast !== false,
  };
}

async function startRuntime(agentId, options) {
  const payload = buildRuntimePayload(options);
  return api(`/runtime/agents/${agentId}/start`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

program
  .name('perp-dex')
  .description('CLI for AI Perp DEX')
  .version('0.2.0');

program
  .command('auth')
  .description('Load an existing agent_id + api_key into local CLI config')
  .requiredOption('--agent <agentId>', 'Existing agent ID')
  .requiredOption('--api-key <apiKey>', 'Existing API key')
  .option('--name <name>', 'Friendly local name')
  .action((options) => {
    saveAgentConfig({
      agentId: options.agent,
      apiKey: options.apiKey,
      name: options.name || options.agent,
    });

    console.log(LOGO);
    console.log(chalk.green('Credentials saved.'));
    console.log(chalk.gray(`Config file: ${CONFIG_FILE}`));
    console.log(chalk.gray('Next:'));
    console.log(chalk.white('  1. ') + chalk.cyan('perp-dex status'));
    console.log(chalk.white('  2. ') + chalk.cyan('perp-dex runtime start'));
  });

program
  .command('register')
  .description('Register as an agent and save API credentials locally')
  .option('-n, --name <name>', 'Agent display name')
  .option('-w, --wallet <wallet>', 'Wallet address (EVM or Solana)')
  .option('-b, --bio <bio>', 'Agent bio')
  .option('--yes', 'Skip prompts and use defaults when values are missing', false)
  .action(async (options) => {
    console.log(LOGO);

    let name = options.name;
    let wallet = options.wallet;
    let bio = options.bio || '';

    if (!options.yes && (!name || !wallet)) {
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'name',
          message: 'Agent display name:',
          when: !name,
          validate: (v) => v.length > 0 || 'Name is required',
        },
        {
          type: 'input',
          name: 'wallet',
          message: 'Wallet address (for settlements):',
          when: !wallet,
          default: randomWallet(),
        },
        {
          type: 'input',
          name: 'bio',
          message: 'Agent bio (optional):',
          when: !bio,
        },
      ]);

      name = name || answers.name;
      wallet = wallet || answers.wallet;
      bio = bio || answers.bio || '';
    }

    name = name || `Agent-${crypto.randomBytes(3).toString('hex')}`;
    wallet = wallet || randomWallet();

    const spinner = ora('Registering agent...').start();

    try {
      const result = await registerAgent({ name, wallet, bio });
      spinner.succeed('Agent registered successfully');

      saveAgentConfig({
        agentId: result.agent.agent_id,
        apiKey: result.api_key,
        name: result.agent.display_name || name,
      });

      console.log('\n' + chalk.green('='.repeat(56)));
      console.log(chalk.bold('\nAgent Details\n'));
      console.log(chalk.gray('Agent ID: ') + chalk.white(result.agent.agent_id));
      console.log(chalk.gray('Name:     ') + chalk.white(result.agent.display_name || name));
      console.log(chalk.gray('API Key:  ') + chalk.yellow(result.api_key));
      console.log(chalk.green('\n' + '='.repeat(56)));

      console.log(chalk.cyan(`\nSaved to ${CONFIG_FILE}`));
      console.log(chalk.gray('Next:'));
      console.log(chalk.white('  1. ') + chalk.cyan('perp-dex deposit 1000'));
      console.log(chalk.white('  2. ') + chalk.cyan('perp-dex runtime start'));
    } catch (e) {
      spinner.fail('Registration failed');
      console.error(chalk.red(e.message));
    }
  });

program
  .command('deploy')
  .description('One-command deploy: register (if needed), optional deposit, and runtime start')
  .option('-n, --name <name>', 'Agent display name (when registering new)')
  .option('-w, --wallet <wallet>', 'Wallet address (when registering new)')
  .option('-b, --bio <bio>', 'Agent bio (when registering new)', '')
  .option('-f, --fund <amount>', 'Initial USDC deposit amount', '0')
  .option('--force-register', 'Always register a new agent even if local credentials exist', false)
  .option('--no-start', 'Only register/fund, skip runtime start')
  .option('--heartbeat <seconds>', 'Runtime heartbeat interval in seconds', '60')
  .option('--min-confidence <value>', 'Runtime minimum confidence 0-1', '0.6')
  .option('--max-position <amount>', 'Runtime max position size in USDC', '100')
  .option('--strategy <name>', 'Runtime strategy name', 'momentum')
  .option('--markets <list>', 'Comma-separated markets', 'BTC-PERP,ETH-PERP')
  .option('--no-auto-broadcast', 'Disable thought/signal auto-broadcast')
  .action(async (options) => {
    console.log(LOGO);
    let config = loadConfig();
    let agentId = config.agentId;

    if (options.forceRegister || !config.agentId || !config.apiKey) {
      const regSpinner = ora('Registering agent...').start();
      try {
        const result = await registerAgent({
          name: options.name || `Agent-${crypto.randomBytes(3).toString('hex')}`,
          wallet: options.wallet || randomWallet(),
          bio: options.bio,
        });

        saveAgentConfig({
          agentId: result.agent.agent_id,
          apiKey: result.api_key,
          name: result.agent.display_name || options.name,
        });

        config = loadConfig();
        agentId = config.agentId;
        regSpinner.succeed(`Registered ${agentId}`);
      } catch (e) {
        regSpinner.fail('Registration failed');
        console.error(chalk.red(e.message));
        return;
      }
    } else {
      console.log(chalk.cyan(`Using local credentials for ${config.agentId}`));
    }

    const fundAmount = parseNumber(options.fund, 'fund');
    if (fundAmount > 0) {
      const fundSpinner = ora(`Depositing $${fundAmount.toFixed(2)}...`).start();
      try {
        const result = await depositFunds(agentId, fundAmount);
        fundSpinner.succeed(`Deposit complete. Available: $${Number(result.new_balance || 0).toFixed(2)}`);
      } catch (e) {
        fundSpinner.fail('Deposit failed');
        console.error(chalk.red(e.message));
        return;
      }
    }

    if (options.start) {
      const runtimeSpinner = ora('Starting autonomous runtime...').start();
      try {
        const result = await startRuntime(agentId, options);
        runtimeSpinner.succeed(result.message || `Runtime started for ${agentId}`);
      } catch (e) {
        runtimeSpinner.fail('Runtime start failed');
        console.error(chalk.red(e.message));
        return;
      }
    }

    console.log(chalk.green('\nDeploy complete.'));
    console.log(chalk.gray('Useful commands:'));
    console.log(chalk.white('  • ') + chalk.cyan('perp-dex status'));
    console.log(chalk.white('  • ') + chalk.cyan('perp-dex runtime status'));
    console.log(chalk.white('  • ') + chalk.cyan('perp-dex long BTC 100 --leverage 5'));
  });

program
  .command('status')
  .description('Check your agent status')
  .action(async () => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    console.log(LOGO);
    const spinner = ora('Fetching status...').start();

    try {
      const [agent, balance, positions] = await Promise.all([
        api(`/agents/${config.agentId}`),
        api(`/balance/${config.agentId}`),
        api(`/positions/${config.agentId}`),
      ]);

      spinner.stop();

      console.log(chalk.bold('\nAgent Status\n'));
      console.log(chalk.gray('Agent:     ') + chalk.white(config.name || config.agentId));
      console.log(chalk.gray('Balance:   ') + chalk.green(`$${Number(balance.available || 0).toFixed(2)}`));
      console.log(chalk.gray('Locked:    ') + chalk.yellow(`$${Number(balance.locked || 0).toFixed(2)}`));
      console.log(chalk.gray('PnL:       ') + (agent.pnl >= 0 ? chalk.green : chalk.red)(`$${Number(agent.pnl || 0).toFixed(2)}`));
      console.log(chalk.gray('Positions: ') + chalk.white(String(positions.positions?.length || 0)));

      if ((positions.positions || []).length > 0) {
        console.log(chalk.bold('\nOpen Positions\n'));
        for (const pos of positions.positions) {
          const pnlColor = pos.unrealized_pnl >= 0 ? chalk.green : chalk.red;
          console.log(
            chalk.gray('  • ') +
            chalk.white(pos.asset) + ' ' +
            (pos.side === 'long' ? chalk.green('LONG') : chalk.red('SHORT')) + ' ' +
            chalk.gray('$') + chalk.white(String(pos.size_usdc)) + ' ' +
            chalk.gray('@') + chalk.white(Number(pos.entry_price || 0).toFixed(2)) + ' ' +
            pnlColor(`(${pos.unrealized_pnl >= 0 ? '+' : ''}${Number(pos.unrealized_pnl || 0).toFixed(2)})`)
          );
        }
      }
    } catch (e) {
      spinner.fail('Failed to fetch status');
      console.error(chalk.red(e.message));
    }
  });

program
  .command('balance')
  .description('Check your balance')
  .action(async () => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    try {
      const balance = await api(`/balance/${config.agentId}`);
      console.log(LOGO);
      console.log(chalk.bold('\nBalance\n'));
      console.log(chalk.gray('Total:     ') + chalk.white(`$${Number(balance.balance || 0).toFixed(2)}`));
      console.log(chalk.gray('Available: ') + chalk.green(`$${Number(balance.available || 0).toFixed(2)}`));
      console.log(chalk.gray('Locked:    ') + chalk.yellow(`$${Number(balance.locked || 0).toFixed(2)}`));
    } catch (e) {
      console.error(chalk.red(e.message));
    }
  });

program
  .command('deposit <amount>')
  .description('Deposit USDC to your account')
  .action(async (amount) => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    const fundAmount = parseNumber(amount, 'amount');
    const spinner = ora('Processing deposit...').start();

    try {
      const result = await depositFunds(config.agentId, fundAmount);
      spinner.succeed('Deposit successful');
      console.log(chalk.green(`\nNew balance: $${Number(result.new_balance || 0).toFixed(2)}`));
    } catch (e) {
      spinner.fail('Deposit failed');
      console.error(chalk.red(e.message));
    }
  });

program
  .command('long <asset> <size>')
  .description('Open a long position')
  .option('-l, --leverage <number>', 'Leverage (1-20)', '5')
  .action(async (asset, size, options) => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    const assetSymbol = formatAsset(asset);
    const leverage = Math.floor(parseNumber(options.leverage, 'leverage'));
    const sizeUsdc = parseNumber(size, 'size');
    const spinner = ora(`Opening long ${assetSymbol}...`).start();

    try {
      const result = await api('/intents', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: config.agentId,
          intent_type: 'long',
          asset: assetSymbol,
          size_usdc: sizeUsdc,
          leverage,
        }),
      });

      spinner.succeed('Position opened');

      if (result.position) {
        console.log('\n' + chalk.green('='.repeat(56)));
        console.log(chalk.bold('\nPosition Details\n'));
        console.log(chalk.gray('Asset:       ') + chalk.white(result.position.asset));
        console.log(chalk.gray('Side:        ') + chalk.green('LONG'));
        console.log(chalk.gray('Size:        ') + chalk.white(`$${result.position.size_usdc}`));
        console.log(chalk.gray('Entry:       ') + chalk.white(`$${Number(result.position.entry_price || 0).toFixed(2)}`));
        console.log(chalk.gray('Leverage:    ') + chalk.yellow(`${result.position.leverage}x`));
        console.log(chalk.gray('Liquidation: ') + chalk.red(`$${Number(result.position.liquidation_price || 0).toFixed(2)}`));
        console.log(chalk.green('\n' + '='.repeat(56)));
      }

      if (result.fees) {
        console.log(chalk.gray(`\nFee: $${Number(result.fees.protocol_fee || 0).toFixed(4)}`));
      }
    } catch (e) {
      spinner.fail('Failed to open position');
      console.error(chalk.red(e.message));
    }
  });

program
  .command('short <asset> <size>')
  .description('Open a short position')
  .option('-l, --leverage <number>', 'Leverage (1-20)', '5')
  .action(async (asset, size, options) => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    const assetSymbol = formatAsset(asset);
    const leverage = Math.floor(parseNumber(options.leverage, 'leverage'));
    const sizeUsdc = parseNumber(size, 'size');
    const spinner = ora(`Opening short ${assetSymbol}...`).start();

    try {
      const result = await api('/intents', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: config.agentId,
          intent_type: 'short',
          asset: assetSymbol,
          size_usdc: sizeUsdc,
          leverage,
        }),
      });

      spinner.succeed('Position opened');

      if (result.position) {
        console.log('\n' + chalk.red('='.repeat(56)));
        console.log(chalk.bold('\nPosition Details\n'));
        console.log(chalk.gray('Asset:       ') + chalk.white(result.position.asset));
        console.log(chalk.gray('Side:        ') + chalk.red('SHORT'));
        console.log(chalk.gray('Size:        ') + chalk.white(`$${result.position.size_usdc}`));
        console.log(chalk.gray('Entry:       ') + chalk.white(`$${Number(result.position.entry_price || 0).toFixed(2)}`));
        console.log(chalk.gray('Leverage:    ') + chalk.yellow(`${result.position.leverage}x`));
        console.log(chalk.gray('Liquidation: ') + chalk.red(`$${Number(result.position.liquidation_price || 0).toFixed(2)}`));
        console.log(chalk.red('\n' + '='.repeat(56)));
      }
    } catch (e) {
      spinner.fail('Failed to open position');
      console.error(chalk.red(e.message));
    }
  });

program
  .command('prices')
  .description('Get current prices')
  .action(async () => {
    try {
      const result = await api('/prices', {}, { includeAuth: false });
      console.log(LOGO);
      console.log(chalk.bold('\nCurrent Prices\n'));

      for (const [asset, data] of Object.entries(result.prices || {})) {
        const change = Number(data.change_24h || 0);
        const changeStr = change >= 0 ? chalk.green(`+${change.toFixed(2)}%`) : chalk.red(`${change.toFixed(2)}%`);
        console.log(
          chalk.gray('  ') +
          chalk.white(asset.padEnd(5)) +
          chalk.gray(' $') +
          chalk.white(Number(data.price || 0).toLocaleString().padStart(10)) +
          '  ' + changeStr
        );
      }
    } catch (e) {
      console.error(chalk.red(e.message));
    }
  });

program
  .command('positions')
  .description('List your open positions')
  .action(async () => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    try {
      const result = await api(`/positions/${config.agentId}`);
      console.log(LOGO);

      if (!result.positions || result.positions.length === 0) {
        console.log(chalk.gray('\nNo open positions.'));
        return;
      }

      console.log(chalk.bold('\nOpen Positions\n'));

      for (const pos of result.positions) {
        const pnlColor = pos.unrealized_pnl >= 0 ? chalk.green : chalk.red;
        const sideColor = pos.side === 'long' ? chalk.green : chalk.red;

        console.log(chalk.white(pos.asset) + ' ' + sideColor(String(pos.side).toUpperCase()));
        console.log(chalk.gray('  Size:   $') + chalk.white(String(pos.size_usdc)) + chalk.gray(' @ ') + chalk.white(Number(pos.entry_price || 0).toFixed(2)));
        console.log(chalk.gray('  PnL:    ') + pnlColor(`$${Number(pos.unrealized_pnl || 0).toFixed(2)} (${Number(pos.unrealized_pnl_pct || 0).toFixed(2)}%)`));
        console.log(chalk.gray('  Liq:    $') + chalk.red(Number(pos.liquidation_price || 0).toFixed(2)));
        console.log('');
      }
    } catch (e) {
      console.error(chalk.red(e.message));
    }
  });

const runtime = program
  .command('runtime')
  .description('Manage autonomous runtime');

runtime
  .command('start')
  .description('Start autonomous runtime for your agent')
  .option('--agent <agentId>', 'Agent ID (default: local config agent)')
  .option('--heartbeat <seconds>', 'Heartbeat interval in seconds', '60')
  .option('--min-confidence <value>', 'Minimum confidence 0-1', '0.6')
  .option('--max-position <amount>', 'Max position size in USDC', '100')
  .option('--strategy <name>', 'Runtime strategy', 'momentum')
  .option('--markets <list>', 'Comma-separated markets', 'BTC-PERP,ETH-PERP')
  .option('--no-auto-broadcast', 'Disable thought/signal auto-broadcast')
  .action(async (options) => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    const agentId = options.agent || config.agentId;
    const spinner = ora(`Starting runtime for ${agentId}...`).start();

    try {
      const result = await startRuntime(agentId, options);
      spinner.succeed(result.message || `Runtime started for ${agentId}`);
    } catch (e) {
      spinner.fail('Runtime start failed');
      console.error(chalk.red(e.message));
    }
  });

runtime
  .command('stop')
  .description('Stop autonomous runtime for your agent')
  .option('--agent <agentId>', 'Agent ID (default: local config agent)')
  .action(async (options) => {
    let config;
    try {
      config = requireAgentConfig();
    } catch (e) {
      console.log(chalk.yellow(e.message));
      return;
    }

    const agentId = options.agent || config.agentId;
    const spinner = ora(`Stopping runtime for ${agentId}...`).start();

    try {
      const result = await api(`/runtime/agents/${agentId}/stop`, { method: 'POST' });
      spinner.succeed(result.message || `Runtime stopped for ${agentId}`);
    } catch (e) {
      spinner.fail('Runtime stop failed');
      console.error(chalk.red(e.message));
    }
  });

runtime
  .command('status')
  .description('Check runtime status')
  .option('--agent <agentId>', 'Agent ID (default: local config agent)')
  .action(async (options) => {
    const config = loadConfig();
    const agentId = options.agent || config.agentId;

    if (!agentId) {
      console.log(chalk.yellow('No agent ID set. Use --agent <id> or run perp-dex deploy.'));
      return;
    }

    const spinner = ora(`Fetching runtime status for ${agentId}...`).start();

    try {
      const result = await api(`/runtime/agents/${agentId}/status`, {}, { includeAuth: false });
      spinner.stop();
      console.log(LOGO);
      console.log(chalk.bold('\nRuntime Status\n'));
      console.log(JSON.stringify(result, null, 2));
    } catch (e) {
      spinner.fail('Failed to fetch runtime status');
      console.error(chalk.red(e.message));
    }
  });

program.parse();
