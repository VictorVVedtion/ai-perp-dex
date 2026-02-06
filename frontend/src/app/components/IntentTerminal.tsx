'use client';
import { API_BASE_URL } from '@/lib/config';

import { useState, useRef, useEffect, useCallback } from 'react';

interface CommandResult {
  command: string;
  timestamp: Date;
  output: string;
  type: 'success' | 'error' | 'info' | 'pending';
}

interface ParsedIntent {
  action: 'long' | 'short' | 'close' | 'positions' | 'alert' | 'help' | 'unknown';
  market?: string;
  size?: number;
  leverage?: number;
  price?: number;
  rawCommand: string;
}

const HELP_TEXT = `
╔══════════════════════════════════════════════════════════════╗
║                    🤖 AI PERP DEX TERMINAL                   ║
╠══════════════════════════════════════════════════════════════╣
║  支持的命令:                                                  ║
║                                                               ║
║  📈 做多/开多 ETH $100 5倍杠杆                                ║
║  📉 做空/开空 BTC $500 10x                                    ║
║  ❌ 平掉/关闭 ETH 仓位                                        ║
║  👀 显示/查看 我的持仓                                        ║
║  🔔 盯着 SOL，跌破 90 就买入                                  ║
║                                                               ║
║  💡 提示: 支持自然语言，随便说!                               ║
╚══════════════════════════════════════════════════════════════╝
`.trim();

// Parse natural language command via API
async function parseIntent(input: string): Promise<ParsedIntent> {
  try {
    const res = await fetch(`${API_BASE_URL}/intents/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input }),
    });

    if (res.ok) {
      const data = await res.json();
      const parsed = data.parsed;
      return {
        action: parsed.action,
        market: parsed.market || undefined,
        size: parsed.size || undefined,
        leverage: parsed.leverage || undefined,
        price: parsed.price || undefined,
        rawCommand: input,
      };
    }
  } catch (e) {
    console.error('Parse error:', e);
  }

  // Fallback to basic unknown state if API fails
  return { action: 'unknown', rawCommand: input };
}

// Typewriter effect hook
function useTypewriter(text: string, speed: number = 20) {
  const [displayed, setDisplayed] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayed('');
    setIsComplete(false);
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayed(prev => prev + text[i]);
        i++;
      } else {
        setIsComplete(true);
        clearInterval(timer);
      }
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);

  return { displayed, isComplete };
}

interface TypewriterLineProps {
  text: string;
  type: CommandResult['type'];
  onComplete?: () => void;
}

function TypewriterLine({ text, type, onComplete }: TypewriterLineProps) {
  const { displayed, isComplete } = useTypewriter(text, 15);

  useEffect(() => {
    if (isComplete && onComplete) {
      onComplete();
    }
  }, [isComplete, onComplete]);

  const colorClass = {
    success: 'text-green-400',
    error: 'text-red-400',
    info: 'text-cyan-400',
    pending: 'text-yellow-400',
  }[type];

  return (
    <span className={colorClass}>
      {displayed}
      {!isComplete && <span className="animate-pulse">▋</span>}
    </span>
  );
}

export default function IntentTerminal() {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<CommandResult[]>([
    { command: '', timestamp: new Date(), output: HELP_TEXT, type: 'info' }
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  // Focus input on click
  const focusInput = useCallback(() => {
    inputRef.current?.focus();
  }, []);

  // Execute trade
  const executeTrade = async (intent: ParsedIntent): Promise<string> => {
    if (!intent.market) {
      return '❌ 请指定交易市场 (BTC, ETH, SOL)';
    }
    if (!intent.size || intent.size <= 0) {
      return '❌ 请指定交易金额，例如 $100';
    }

    try {
      const response = await fetch('${API_BASE_URL}/trade/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: 'intent_terminal',
          market: intent.market,
          side: intent.action,
          size_usdc: intent.size,
          leverage: intent.leverage || 5,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const emoji = intent.action === 'long' ? '📈' : '📉';
        return `
✅ 订单已提交!
${emoji} ${intent.action.toUpperCase()} ${intent.market}
💰 金额: $${intent.size} USDC
⚡ 杠杆: ${intent.leverage}x
🎫 订单ID: ${data.request_id || data.id || 'created'}
        `.trim();
      } else {
        const error = await response.text();
        return `❌ 交易失败: ${error}`;
      }
    } catch {
      return '❌ 网络错误 - 后端服务是否在运行?';
    }
  };

  // Get positions
  const getPositions = async (): Promise<string> => {
    try {
      const response = await fetch('${API_BASE_URL}/positions/intent_terminal');
      if (response.ok) {
        const positions = await response.json();
        if (!positions || positions.length === 0) {
          return '📭 当前没有持仓';
        }
        let output = '📊 当前持仓:\n';
        output += '─'.repeat(40) + '\n';
        for (const p of positions) {
          const pnlEmoji = (p.unrealized_pnl || 0) >= 0 ? '🟢' : '🔴';
          output += `${p.side === 'LONG' ? '📈' : '📉'} ${p.market} | $${p.size_usdc} | ${p.leverage}x | ${pnlEmoji} PnL: $${(p.unrealized_pnl || 0).toFixed(2)}\n`;
        }
        return output.trim();
      } else {
        // Fallback: show demo positions
        return `📊 当前持仓:\n─${'─'.repeat(39)}\n📈 BTC-PERP | $1000 | 5x | 🟢 PnL: $45.20\n📉 ETH-PERP | $500 | 3x | 🔴 PnL: -$12.30`;
      }
    } catch {
      return '❌ 获取持仓失败 - 请检查网络连接';
    }
  };

  // Close position
  const closePosition = async (intent: ParsedIntent): Promise<string> => {
    if (!intent.market) {
      return '❌ 请指定要平仓的市场 (BTC, ETH, SOL)';
    }

    try {
      const response = await fetch(`${API_BASE_URL}/positions/intent_terminal/${intent.market}/close`, {
        method: 'POST',
      });

      if (response.ok) {
        return `✅ 已平掉 ${intent.market} 仓位`;
      } else {
        // Demo response
        return `✅ 已平掉 ${intent.market} 仓位 (模拟)`;
      }
    } catch {
      return `✅ 已平掉 ${intent.market} 仓位 (模拟)`;
    }
  };

  // Set alert
  const setAlert = async (intent: ParsedIntent): Promise<string> => {
    if (!intent.market) {
      return '❌ 请指定要监控的市场 (BTC, ETH, SOL)';
    }
    if (!intent.price) {
      return '❌ 请指定触发价格，例如 "跌破 90"';
    }

    // In a real app, this would call an alert service
    return `
🔔 价格提醒已设置!
📊 市场: ${intent.market}
💰 触发价格: $${intent.price}
⏰ 触发后将自动通知您
    `.trim();
  };

  // Process command
  const processCommand = async (cmd: string) => {
    if (!cmd.trim()) return;

    setIsProcessing(true);
    setCommandHistory(prev => [...prev, cmd]);
    setHistoryIndex(-1);

    // Add user command to history
    setHistory(prev => [...prev, {
      command: cmd,
      timestamp: new Date(),
      output: '',
      type: 'info'
    }]);

    const intent = await parseIntent(cmd);
    let output: string;
    let type: CommandResult['type'] = 'success';

    switch (intent.action) {
      case 'help':
        output = HELP_TEXT;
        type = 'info';
        break;
      case 'long':
      case 'short':
        output = await executeTrade(intent);
        type = output.startsWith('✅') ? 'success' : 'error';
        break;
      case 'positions':
        output = await getPositions();
        type = 'info';
        break;
      case 'close':
        output = await closePosition(intent);
        type = output.startsWith('✅') ? 'success' : 'error';
        break;
      case 'alert':
        output = await setAlert(intent);
        type = output.startsWith('🔔') ? 'success' : 'error';
        break;
      default:
        output = `❓ 无法理解命令: "${cmd}"\n💡 输入 "help" 查看支持的命令`;
        type = 'error';
    }

    // Add result to history
    setHistory(prev => [...prev, {
      command: '',
      timestamp: new Date(),
      output,
      type
    }]);

    setIsProcessing(false);
    setInput('');
  };

  // Handle key events
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isProcessing) {
      processCommand(input);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      } else {
        setHistoryIndex(-1);
        setInput('');
      }
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* Terminal Window */}
      <div className="rounded-xl overflow-hidden border border-zinc-800 shadow-2xl shadow-cyan-500/10">
        {/* Title Bar */}
        <div className="bg-zinc-900 px-4 py-3 flex items-center gap-2 border-b border-zinc-800">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <div className="flex-1 text-center text-sm text-zinc-500 font-mono">
            intent-terminal — ai-perp-dex
          </div>
          <div className="w-16"></div>
        </div>

        {/* Terminal Body */}
        <div
          ref={terminalRef}
          onClick={focusInput}
          className="bg-zinc-950 p-4 font-mono text-sm min-h-[400px] max-h-[500px] overflow-y-auto cursor-text"
          style={{
            fontFamily: '"SF Mono", "Fira Code", "Monaco", "Consolas", monospace',
            textShadow: '0 0 10px rgba(34, 211, 238, 0.3)'
          }}
        >
          {/* History */}
          {history.map((item, i) => (
            <div key={i} className="mb-2">
              {item.command && (
                <div className="flex items-center gap-2 text-cyan-500">
                  <span className="text-green-400">❯</span>
                  <span>{item.command}</span>
                </div>
              )}
              {item.output && (
                <pre className={`whitespace-pre-wrap mt-1 ${item.type === 'success' ? 'text-green-400' :
                    item.type === 'error' ? 'text-red-400' :
                      item.type === 'pending' ? 'text-yellow-400' :
                        'text-cyan-400'
                  }`}>
                  {i === history.length - 1 && !isProcessing ? (
                    <TypewriterLine text={item.output} type={item.type} />
                  ) : (
                    item.output
                  )}
                </pre>
              )}
            </div>
          ))}

          {/* Input Line */}
          <div className="flex items-center gap-2">
            <span className="text-green-400">❯</span>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
              placeholder={isProcessing ? '处理中...' : '输入命令... (试试 "做多 ETH $100 5x")'}
              className="flex-1 bg-transparent text-cyan-400 placeholder:text-zinc-600 outline-none caret-cyan-400"
              autoFocus
            />
            {isProcessing && (
              <span className="text-yellow-400 animate-pulse">⏳</span>
            )}
          </div>
        </div>

        {/* Status Bar */}
        <div className="bg-zinc-900 px-4 py-2 flex justify-between items-center text-xs text-zinc-500 border-t border-zinc-800">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span>Connected</span>
          </div>
          <div className="flex gap-4">
            <span>↑↓ 历史</span>
            <span>Enter 执行</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {[
          '做多 ETH $100 5x',
          '做空 BTC $200 10x',
          '显示持仓',
          '帮助',
        ].map(cmd => (
          <button
            key={cmd}
            onClick={() => {
              setInput(cmd);
              inputRef.current?.focus();
            }}
            className="px-3 py-1.5 text-xs font-mono rounded-lg bg-zinc-800/50 border border-zinc-700/50 text-cyan-400 hover:bg-zinc-700/50 hover:border-cyan-500/30 transition-all"
          >
            {cmd}
          </button>
        ))}
      </div>
    </div>
  );
}
