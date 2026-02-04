"use client";

import React, { useState, useMemo } from 'react';

const TradingDashboard = () => {
  const [leverage, setLeverage] = useState(10);
  const [side, setSide] = useState<'long' | 'short'>('long');
  const [amount, setAmount] = useState('');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');

  // Mock data for display
  const ticker = {
    symbol: "BTC-PERP",
    price: 43250.40,
    change24h: 2.45,
    high24h: 44100.00,
    low24h: 41800.00,
    volume24h: "1.2B"
  };

  const position = {
    size: 0.25,
    entryPrice: 41200.00,
    liqPrice: 37500.00,
    margin: 1030.00,
    pnl: 512.60,
    pnlPercent: 12.4
  };

  const notionalValue = useMemo(() => {
    const val = parseFloat(amount) || 0;
    return val * ticker.price;
  }, [amount, ticker.price]);

  const requiredMargin = useMemo(() => {
    return notionalValue / leverage;
  }, [notionalValue, leverage]);

  return (
    <div className="min-h-screen bg-[#0a0b0d] text-slate-300 p-4 font-sans">
      {/* Top Navigation / Stats Bar */}
      <div className="flex flex-wrap items-center gap-8 mb-6 bg-[#121418] p-4 rounded-xl border border-slate-800 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center text-white font-bold italic">₿</div>
          <div>
            <h1 className="text-white font-bold text-lg leading-none">{ticker.symbol}</h1>
            <span className="text-xs text-slate-500">Bitcoin Perpetual</span>
          </div>
        </div>

        <div className="flex flex-col">
          <span className="text-2xl font-mono font-bold text-emerald-400">
            ${ticker.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
          <span className={`text-xs ${ticker.change24h >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
            {ticker.change24h >= 0 ? '▲' : '▼'} {ticker.change24h}%
          </span>
        </div>

        <div className="hidden md:flex gap-8">
          <Stat label="24h High" value={`$${ticker.high24h.toLocaleString()}`} />
          <Stat label="24h Low" value={`$${ticker.low24h.toLocaleString()}`} />
          <Stat label="24h Volume" value={`$${ticker.volume24h}`} />
          <Stat label="Funding Rate" value="0.0100%" valueClass="text-indigo-400" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Chart Area Placeholder */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="bg-[#121418] rounded-2xl border border-slate-800 h-[500px] relative overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center">
              <div className="flex gap-2">
                {['1m', '5m', '15m', '1h', '4h', '1D'].map(tf => (
                  <button key={tf} className={`px-3 py-1 text-xs rounded-md transition-all ${tf === '1h' ? 'bg-slate-700 text-white' : 'hover:bg-slate-800'}`}>
                    {tf}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> Buy</span>
                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-rose-500"></div> Sell</span>
              </div>
            </div>
            {/* Chart Graphic Placeholder */}
            <div className="flex-1 bg-center opacity-20 flex items-center justify-center">
              <div className="text-slate-600 text-sm italic">TradingView Chart Integration</div>
            </div>
          </div>

          {/* Active Positions */}
          <div className="bg-[#121418] rounded-2xl border border-slate-800 overflow-hidden">
            <div className="p-4 border-b border-slate-800">
              <h2 className="text-white font-semibold">Open Positions (1)</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-800/50">
                    <th className="p-4 font-medium">Market</th>
                    <th className="p-4 font-medium">Size</th>
                    <th className="p-4 font-medium">Entry Price</th>
                    <th className="p-4 font-medium">Liq. Price</th>
                    <th className="p-4 font-medium text-right">Unrealized PnL</th>
                    <th className="p-4"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-4 bg-emerald-500 rounded-sm"></span>
                        <span className="text-white font-medium">BTC-PERP</span>
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20">Long 10x</span>
                      </div>
                    </td>
                    <td className="p-4 text-white">{position.size} BTC</td>
                    <td className="p-4">${position.entryPrice.toLocaleString()}</td>
                    <td className="p-4 text-rose-400">${position.liqPrice.toLocaleString()}</td>
                    <td className="p-4 text-right">
                      <div className="text-emerald-400 font-mono">+${position.pnl.toFixed(2)}</div>
                      <div className="text-[10px] text-emerald-500">+{position.pnlPercent}%</div>
                    </td>
                    <td className="p-4 text-right">
                      <button className="text-slate-400 hover:text-white transition-colors">Close</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Trade Panel */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="bg-[#121418] rounded-2xl border border-slate-800 p-6 shadow-xl sticky top-4">
            <div className="flex gap-1 mb-6 bg-black/40 p-1 rounded-xl border border-slate-800/50">
              <button 
                onClick={() => setSide('long')}
                className={`flex-1 py-3 rounded-lg font-bold transition-all ${side === 'long' ? 'bg-emerald-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)]' : 'text-slate-500 hover:text-slate-300'}`}
              >
                Long
              </button>
              <button 
                onClick={() => setSide('short')}
                className={`flex-1 py-3 rounded-lg font-bold transition-all ${side === 'short' ? 'bg-rose-500 text-white shadow-[0_0_20px_rgba(244,63,94,0.3)]' : 'text-slate-500 hover:text-slate-300'}`}
              >
                Short
              </button>
            </div>

            <div className="space-y-6">
              {/* Order Type Selector */}
              <div className="flex justify-between p-1 bg-slate-900 rounded-lg text-xs font-medium">
                {['Market', 'Limit', 'Stop'].map(type => (
                  <button 
                    key={type}
                    onClick={() => setOrderType(type.toLowerCase() as 'market' | 'limit')}
                    className={`flex-1 py-1.5 rounded transition-all ${orderType === type.toLowerCase() ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                  >
                    {type}
                  </button>
                ))}
              </div>

              {/* Amount Input */}
              <div>
                <div className="flex justify-between text-xs mb-2">
                  <label className="text-slate-400">Order Size</label>
                  <span className="text-slate-500">Available: 1.24 BTC</span>
                </div>
                <div className="relative">
                  <input 
                    type="number" 
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-indigo-500 transition-all font-mono"
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 flex gap-2">
                    <span className="text-slate-500 text-sm font-bold">BTC</span>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2 mt-3">
                  {['25%', '50%', '75%', 'Max'].map(p => (
                    <button key={p} className="bg-slate-900 hover:bg-slate-800 text-[10px] py-1 rounded transition-colors">{p}</button>
                  ))}
                </div>
              </div>

              {/* Leverage Slider */}
              <div className="space-y-3">
                <div className="flex justify-between text-xs">
                  <label className="text-slate-400 font-medium">Leverage</label>
                  <span className="text-indigo-400 font-bold">{leverage}x</span>
                </div>
                <div className="relative pt-1">
                  <input 
                    type="range" 
                    min="1" 
                    max="50" 
                    value={leverage}
                    onChange={(e) => setLeverage(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                  <div className="flex justify-between mt-2 px-1 text-[10px] text-slate-600 font-mono">
                    <span>1x</span>
                    <span>10x</span>
                    <span>25x</span>
                    <span>50x</span>
                  </div>
                </div>
              </div>

              {/* Order Info */}
              <div className="bg-black/20 rounded-xl p-4 space-y-3 border border-slate-800/30">
                <InfoRow label="Price" value={`$${ticker.price.toLocaleString()}`} />
                <InfoRow label="Notional Value" value={`$${notionalValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
                <InfoRow label="Required Margin" value={`$${requiredMargin.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
                <InfoRow label="Execution Fee" value="0.05%" />
              </div>

              {/* Action Button */}
              <button className={`w-full py-4 rounded-xl font-bold text-lg transition-all transform active:scale-[0.98] ${
                side === 'long' 
                  ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-[0_8px_30px_rgb(16,185,129,0.2)]' 
                  : 'bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white shadow-[0_8px_30px_rgb(244,63,94,0.2)]'
              }`}>
                {side === 'long' ? 'Open Long Position' : 'Open Short Position'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper Components
const Stat = ({ label, value, valueClass = "text-white" }: { label: string, value: string, valueClass?: string }) => (
  <div className="flex flex-col">
    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">{label}</span>
    <span className={`text-sm font-mono font-medium ${valueClass}`}>{value}</span>
  </div>
);

const InfoRow = ({ label, value }: { label: string, value: string }) => (
  <div className="flex justify-between text-xs">
    <span className="text-slate-500">{label}</span>
    <span className="text-slate-300 font-mono">{value}</span>
  </div>
);

export default TradingDashboard;
