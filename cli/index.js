#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import inquirer from 'inquirer';
import fs from 'fs';
import path from 'path';
import os from 'os';

const API_URL = process.env.PERP_DEX_API || 'http://localhost:8082';
const CONFIG_DIR = path.join(os.homedir(), '.perp-dex');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

// ASCII Art
const LOGO = `
${chalk.hex('#FF6B35')('🦞')} ${chalk.bold.hex('#00D4AA')('AI PERP DEX')} ${chalk.gray('- Trading Exchange for Autonomous Agents')}
`;

const program = new Command();

// Load config
function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    }
  } catch (e) {}
  return {};
}

// Save config
function saveConfig(config) {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
}

// API helper
async function api(endpoint, options = {}) {
  const config = loadConfig();
  const headers = {
    'Content-Type': 'application/json',
    ...(config.apiKey && { 'X-API-Key': config.apiKey }),
    ...options.headers,
  };
  
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error);
  }
  
  return res.json();
}

program
  .name('perp-dex')
  .description('CLI for AI Perp DEX')
  .version('0.1.0');

// Register command
program
  .command('register')
  .description('Register as an agent and get your API key')
  .action(async () => {
    console.log(LOGO);
    console.log(chalk.cyan('\\n🤖 Agent Registration\\n'));
    
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'name',
        message: 'Agent display name:',
        validate: (v) => v.length > 0 || 'Name is required',
      },
      {
        type: 'input',
        name: 'wallet',
        message: 'Wallet address (for settlements):',
        default: '0x' + Math.random().toString(16).slice(2, 42),
      },
      {
        type: 'input',
        name: 'bio',
        message: 'Agent bio (optional):',
      },
    ]);
    
    const spinner = ora('Registering agent...').start();
    
    try {
      const result = await api('/agents/register', {
        method: 'POST',
        body: JSON.stringify({
          wallet_address: answers.wallet,
          display_name: answers.name,
          bio: answers.bio || undefined,
        }),
      });
      
      spinner.succeed('Agent registered successfully!');
      
      // Save config
      saveConfig({
        agentId: result.agent.agent_id,
        apiKey: result.api_key,
        name: result.agent.display_name,
      });
      
      console.log('\\n' + chalk.green('═'.repeat(50)));
      console.log(chalk.bold('\\n📋 Your Agent Details:\\n'));
      console.log(chalk.gray('Agent ID:    ') + chalk.white(result.agent.agent_id));
      console.log(chalk.gray('Name:        ') + chalk.white(result.agent.display_name));
      console.log(chalk.gray('API Key:     ') + chalk.yellow(result.api_key));
      console.log(chalk.green('\\n═'.repeat(50)));
      
      console.log(chalk.cyan('\\n🔑 Your API key has been saved to ~/.perp-dex/config.json'));
      console.log(chalk.gray('\\nNext steps:'));
      console.log(chalk.white('  1. ') + chalk.gray('Deposit funds:  ') + chalk.cyan('perp-dex deposit 1000'));
      console.log(chalk.white('  2. ') + chalk.gray('Open position:  ') + chalk.cyan('perp-dex long BTC 100 --leverage 5'));
      console.log(chalk.white('  3. ') + chalk.gray('Check balance:  ') + chalk.cyan('perp-dex balance'));
      
    } catch (e) {
      spinner.fail('Registration failed');
      console.error(chalk.red(e.message));
    }
  });

// Status command
program
  .command('status')
  .description('Check your agent status')
  .action(async () => {
    const config = loadConfig();
    if (!config.agentId) {
      console.log(chalk.yellow('Not registered. Run: perp-dex register'));
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
      
      console.log(chalk.bold('\\n📊 Agent Status\\n'));
      console.log(chalk.gray('Agent:     ') + chalk.white(config.name || config.agentId));
      console.log(chalk.gray('Balance:   ') + chalk.green('$' + balance.available.toFixed(2)));
      console.log(chalk.gray('Locked:    ') + chalk.yellow('$' + balance.locked.toFixed(2)));
      console.log(chalk.gray('PnL:       ') + (agent.pnl >= 0 ? chalk.green : chalk.red)('$' + agent.pnl.toFixed(2)));
      console.log(chalk.gray('Positions: ') + chalk.white(positions.positions.length));
      
      if (positions.positions.length > 0) {
        console.log(chalk.bold('\\n📈 Open Positions:\\n'));
        for (const pos of positions.positions) {
          const pnlColor = pos.unrealized_pnl >= 0 ? chalk.green : chalk.red;
          console.log(
            chalk.gray('  • ') +
            chalk.white(pos.asset) + ' ' +
            (pos.side === 'long' ? chalk.green('LONG') : chalk.red('SHORT')) + ' ' +
            chalk.gray('$') + chalk.white(pos.size_usdc) + ' ' +
            chalk.gray('@') + chalk.white(pos.entry_price.toFixed(2)) + ' ' +
            pnlColor('(' + (pos.unrealized_pnl >= 0 ? '+' : '') + pos.unrealized_pnl.toFixed(2) + ')')
          );
        }
      }
      
    } catch (e) {
      spinner.fail('Failed to fetch status');
      console.error(chalk.red(e.message));
    }
  });

// Balance command
program
  .command('balance')
  .description('Check your balance')
  .action(async () => {
    const config = loadConfig();
    if (!config.agentId) {
      console.log(chalk.yellow('Not registered. Run: perp-dex register'));
      return;
    }
    
    try {
      const balance = await api(`/balance/${config.agentId}`);
      console.log(LOGO);
      console.log(chalk.bold('\\n💰 Balance\\n'));
      console.log(chalk.gray('Total:     ') + chalk.white('$' + balance.balance.toFixed(2)));
      console.log(chalk.gray('Available: ') + chalk.green('$' + balance.available.toFixed(2)));
      console.log(chalk.gray('Locked:    ') + chalk.yellow('$' + balance.locked.toFixed(2)));
    } catch (e) {
      console.error(chalk.red(e.message));
    }
  });

// Deposit command
program
  .command('deposit <amount>')
  .description('Deposit USDC to your account')
  .action(async (amount) => {
    const config = loadConfig();
    if (!config.apiKey) {
      console.log(chalk.yellow('Not registered. Run: perp-dex register'));
      return;
    }
    
    const spinner = ora('Processing deposit...').start();
    
    try {
      const result = await api('/deposit', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: config.agentId,
          amount: parseFloat(amount),
        }),
      });
      
      spinner.succeed('Deposit successful!');
      console.log(chalk.green('\\nNew balance: $' + result.new_balance.toFixed(2)));
    } catch (e) {
      spinner.fail('Deposit failed');
      console.error(chalk.red(e.message));
    }
  });

// Long command
program
  .command('long <asset> <size>')
  .description('Open a long position')
  .option('-l, --leverage <number>', 'Leverage (1-50)', '5')
  .action(async (asset, size, options) => {
    const config = loadConfig();
    if (!config.apiKey) {
      console.log(chalk.yellow('Not registered. Run: perp-dex register'));
      return;
    }
    
    const assetSymbol = asset.toUpperCase() + (asset.includes('-') ? '' : '-PERP');
    const spinner = ora(`Opening long ${assetSymbol}...`).start();
    
    try {
      const result = await api('/intents', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: config.agentId,
          intent_type: 'long',
          asset: assetSymbol,
          size_usdc: parseFloat(size),
          leverage: parseInt(options.leverage),
        }),
      });
      
      spinner.succeed('Position opened!');
      
      if (result.position) {
        console.log('\\n' + chalk.green('═'.repeat(50)));
        console.log(chalk.bold('\\n📈 Position Details:\\n'));
        console.log(chalk.gray('Asset:       ') + chalk.white(result.position.asset));
        console.log(chalk.gray('Side:        ') + chalk.green('LONG'));
        console.log(chalk.gray('Size:        ') + chalk.white('$' + result.position.size_usdc));
        console.log(chalk.gray('Entry:       ') + chalk.white('$' + result.position.entry_price.toFixed(2)));
        console.log(chalk.gray('Leverage:    ') + chalk.yellow(result.position.leverage + 'x'));
        console.log(chalk.gray('Liquidation: ') + chalk.red('$' + result.position.liquidation_price.toFixed(2)));
        console.log(chalk.green('\\n═'.repeat(50)));
      }
      
      if (result.fees) {
        console.log(chalk.gray('\\nFee: $' + result.fees.protocol_fee.toFixed(4)));
      }
      
    } catch (e) {
      spinner.fail('Failed to open position');
      console.error(chalk.red(e.message));
    }
  });

// Short command  
program
  .command('short <asset> <size>')
  .description('Open a short position')
  .option('-l, --leverage <number>', 'Leverage (1-50)', '5')
  .action(async (asset, size, options) => {
    const config = loadConfig();
    if (!config.apiKey) {
      console.log(chalk.yellow('Not registered. Run: perp-dex register'));
      return;
    }
    
    const assetSymbol = asset.toUpperCase() + (asset.includes('-') ? '' : '-PERP');
    const spinner = ora(`Opening short ${assetSymbol}...`).start();
    
    try {
      const result = await api('/intents', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: config.agentId,
          intent_type: 'short',
          asset: assetSymbol,
          size_usdc: parseFloat(size),
          leverage: parseInt(options.leverage),
        }),
      });
      
      spinner.succeed('Position opened!');
      
      if (result.position) {
        console.log('\\n' + chalk.red('═'.repeat(50)));
        console.log(chalk.bold('\\n📉 Position Details:\\n'));
        console.log(chalk.gray('Asset:       ') + chalk.white(result.position.asset));
        console.log(chalk.gray('Side:        ') + chalk.red('SHORT'));
        console.log(chalk.gray('Size:        ') + chalk.white('$' + result.position.size_usdc));
        console.log(chalk.gray('Entry:       ') + chalk.white('$' + result.position.entry_price.toFixed(2)));
        console.log(chalk.gray('Leverage:    ') + chalk.yellow(result.position.leverage + 'x'));
        console.log(chalk.gray('Liquidation: ') + chalk.red('$' + result.position.liquidation_price.toFixed(2)));
        console.log(chalk.red('\\n═'.repeat(50)));
      }
      
    } catch (e) {
      spinner.fail('Failed to open position');
      console.error(chalk.red(e.message));
    }
  });

// Prices command
program
  .command('prices')
  .description('Get current prices')
  .action(async () => {
    try {
      const result = await api('/prices');
      console.log(LOGO);
      console.log(chalk.bold('\\n📊 Current Prices\\n'));
      
      for (const [asset, data] of Object.entries(result.prices)) {
        const change = data.change_24h || 0;
        const changeStr = change >= 0 ? chalk.green('+' + change.toFixed(2) + '%') : chalk.red(change.toFixed(2) + '%');
        console.log(
          chalk.gray('  ') +
          chalk.white(asset.padEnd(5)) +
          chalk.gray(' $') +
          chalk.white(data.price.toLocaleString().padStart(10)) +
          '  ' + changeStr
        );
      }
    } catch (e) {
      console.error(chalk.red(e.message));
    }
  });

// Positions command
program
  .command('positions')
  .description('List your open positions')
  .action(async () => {
    const config = loadConfig();
    if (!config.agentId) {
      console.log(chalk.yellow('Not registered. Run: perp-dex register'));
      return;
    }
    
    try {
      const result = await api(`/positions/${config.agentId}`);
      console.log(LOGO);
      
      if (result.positions.length === 0) {
        console.log(chalk.gray('\\nNo open positions.'));
        return;
      }
      
      console.log(chalk.bold('\\n📈 Open Positions\\n'));
      
      for (const pos of result.positions) {
        const pnlColor = pos.unrealized_pnl >= 0 ? chalk.green : chalk.red;
        const sideColor = pos.side === 'long' ? chalk.green : chalk.red;
        
        console.log(chalk.white(pos.asset) + ' ' + sideColor(pos.side.toUpperCase()));
        console.log(chalk.gray('  Size:   $') + chalk.white(pos.size_usdc) + chalk.gray(' @ ') + chalk.white(pos.entry_price.toFixed(2)));
        console.log(chalk.gray('  PnL:    ') + pnlColor('$' + pos.unrealized_pnl.toFixed(2) + ' (' + pos.unrealized_pnl_pct.toFixed(2) + '%)'));
        console.log(chalk.gray('  Liq:    $') + chalk.red(pos.liquidation_price.toFixed(2)));
        console.log('');
      }
    } catch (e) {
      console.error(chalk.red(e.message));
    }
  });

program.parse();
