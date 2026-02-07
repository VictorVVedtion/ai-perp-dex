'use client';

import { Skill } from '@/lib/api';
import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface PerformanceChartProps {
  skill: Skill;
}

// Generate deterministic chart data based on skill stats
const generateChartData = (skill: Skill) => {
  const data = [];
  let value = 100;
  const seed = skill.id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  
  for (let i = 0; i < 30; i++) {
    // Use skill stats to influence the trend
    const trend = skill.stats.totalReturn > 0 ? 0.1 : -0.05;
    const volatility = (100 - skill.stats.winRate) / 50;
    const pseudoRandom = Math.sin(seed + i * 0.5) * volatility;
    value += trend + pseudoRandom;
    data.push({
      name: `Day ${i + 1}`,
      value: Math.max(value, 50) // Floor at 50
    });
  }
  return data;
};

export default function PerformanceChart({ skill }: PerformanceChartProps) {
  const chartData = useMemo(() => generateChartData(skill), [skill.id]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00D4AA" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#00D4AA" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
        <XAxis dataKey="name" hide />
        <YAxis domain={['auto', 'auto']} hide />
        <Tooltip 
          contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a' }}
          itemStyle={{ color: '#00D4AA' }}
        />
        <Area type="monotone" dataKey="value" stroke="#00D4AA" fillOpacity={1} fill="url(#colorValue)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
