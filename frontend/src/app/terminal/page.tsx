import IntentTerminal from '@/app/components/IntentTerminal';

export const metadata = {
  title: 'Intent Terminal | AI Perp DEX',
  description: 'Trade with natural language commands',
};

export default function TerminalPage() {
  return (
    <div className="min-h-screen py-12 px-4">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-3">
          <span className="bg-gradient-to-r from-cyan-400 to-green-400 bg-clip-text text-transparent">
            🖥️ Intent Terminal
          </span>
        </h1>
        <p className="text-zinc-400 max-w-md mx-auto">
          用自然语言交易。告诉 AI 你想做什么，它会帮你执行。
        </p>
      </div>

      {/* Terminal */}
      <IntentTerminal />

      {/* Features */}
      <div className="max-w-3xl mx-auto mt-12 grid md:grid-cols-3 gap-6">
        <div className="glass-card p-5 text-center">
          <div className="text-3xl mb-3">🗣️</div>
          <h3 className="font-semibold mb-2">自然语言</h3>
          <p className="text-sm text-zinc-500">
            用中文或英文描述你的交易意图
          </p>
        </div>
        <div className="glass-card p-5 text-center">
          <div className="text-3xl mb-3">⚡</div>
          <h3 className="font-semibold mb-2">即时执行</h3>
          <p className="text-sm text-zinc-500">
            AI 理解你的命令并立即提交订单
          </p>
        </div>
        <div className="glass-card p-5 text-center">
          <div className="text-3xl mb-3">🔔</div>
          <h3 className="font-semibold mb-2">智能提醒</h3>
          <p className="text-sm text-zinc-500">
            设置价格提醒，让 AI 帮你盯盘
          </p>
        </div>
      </div>
    </div>
  );
}
