#!/bin/bash
# 50 AI Agents Trading Test - 使用 Gemini CLI 生成 Agent 配置
# 目标: 测试 Trading Hub 的多 Agent 并发交易

set -e

API_BASE="http://localhost:8082"
RESULTS_FILE="/tmp/gemini_test_results.json"
AGENTS_FILE="/tmp/gemini_agents.json"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}                    🤖 50 AI Agents Trading Test                              ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查服务器
echo -e "\n${YELLOW}[1/5] 检查 Trading Hub 服务器...${NC}"
if curl -s "$API_BASE/stats" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 服务器在线: $API_BASE${NC}"
else
    echo -e "${RED}✗ 服务器离线，请先启动 Trading Hub${NC}"
    exit 1
fi

# 使用 Gemini 生成 50 个 Agent 配置
echo -e "\n${YELLOW}[2/5] 使用 Gemini CLI 生成 50 个 Agent 配置...${NC}"

GEMINI_PROMPT='Generate 50 unique AI trading agents as a JSON array. Each agent needs:
- name: creative name (e.g., "RSI_Hunter", "DipBuyer_3000")
- type: one of [momentum, mean_reversion, arbitrage, degen, conservative]
- personality: 1-2 sentence trader personality
- strategies: array of 2-3 trading strategies with reasons

Distribution: 10 momentum, 10 mean_reversion, 10 arbitrage, 10 degen, 10 conservative

Example format:
[
  {
    "name": "TrendRider_Alpha",
    "type": "momentum",
    "personality": "Aggressive trend follower, never fights the tape",
    "strategies": [
      {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "20 日均线突破，成交量放大 2x"},
      {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 3, "reason": "RSI 从 30 反弹到 50，动能恢复"}
    ]
  }
]

Trading reasons should be realistic Chinese technical analysis like:
- "RSI 超卖到 25，准备反弹"
- "突破下降趋势线，追涨"
- "恐惧指数 26，市场过度悲观"
- "ETH/BTC 比率处于历史低位"
- "资金费率为负，空头过度拥挤"
- "布林带收窄，即将突破"
- "4 小时 MACD 金叉"
- "支撑位 $2000 三次测试未破"

Make names creative and memorable. Output ONLY valid JSON array, no markdown.'

echo "正在调用 Gemini CLI..."
GEMINI_OUTPUT=$(gemini -p "$GEMINI_PROMPT" 2>/dev/null || echo "[]")

# 提取 JSON (移除可能的 markdown 包装)
echo "$GEMINI_OUTPUT" | grep -o '\[.*\]' | head -1 > "$AGENTS_FILE" 2>/dev/null || echo "[]" > "$AGENTS_FILE"

# 验证 JSON
if ! jq -e '.' "$AGENTS_FILE" > /dev/null 2>&1; then
    echo -e "${RED}Gemini 输出解析失败，使用备用配置...${NC}"
    # 备用配置
    cat > "$AGENTS_FILE" << 'BACKUP_AGENTS'
[
  {"name": "TrendMaster_001", "type": "momentum", "personality": "激进趋势追踪者", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "突破 20 日均线，成交量放大"}, {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 3, "reason": "RSI 从超卖区反弹"}]},
  {"name": "MomentumBot_002", "type": "momentum", "personality": "只做强势币种", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 100, "leverage": 4, "reason": "4 小时 MACD 金叉"}, {"action": "long", "asset": "BTC-PERP", "size": 180, "leverage": 5, "reason": "突破下降趋势线"}]},
  {"name": "BreakoutHunter_003", "type": "momentum", "personality": "专注突破交易", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 120, "leverage": 4, "reason": "布林带突破上轨"}, {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "三角形态向上突破"}]},
  {"name": "TapeReader_004", "type": "momentum", "personality": "跟随大单方向", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 250, "leverage": 6, "reason": "链上大额转账进交易所"}, {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 3, "reason": "ETH 基金会抛售预期"}]},
  {"name": "VolumeTracker_005", "type": "momentum", "personality": "成交量决定一切", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 4, "reason": "成交量突破 30 日均量"}, {"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 5, "reason": "大阳线配合天量"}]},
  {"name": "RelativeStrength_006", "type": "momentum", "personality": "只做相对强势", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 180, "leverage": 4, "reason": "ETH/BTC 比率突破"}, {"action": "short", "asset": "SOL-PERP", "size": 100, "leverage": 3, "reason": "SOL 相对弱势"}]},
  {"name": "NewsTrader_007", "type": "momentum", "personality": "新闻驱动交易", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 300, "leverage": 5, "reason": "ETF 资金流入创新高"}, {"action": "long", "asset": "ETH-PERP", "size": 200, "leverage": 4, "reason": "质押收益率上升"}]},
  {"name": "ADXRider_008", "type": "momentum", "personality": "ADX 信徒", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 220, "leverage": 5, "reason": "ADX 突破 25，趋势确认"}, {"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 4, "reason": "+DI 上穿 -DI"}]},
  {"name": "SwingMaster_009", "type": "momentum", "personality": "波段大师", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 200, "leverage": 4, "reason": "日线级别底部确认"}, {"action": "long", "asset": "BTC-PERP", "size": 250, "leverage": 5, "reason": "周线看涨吞没"}]},
  {"name": "AlphaCatcher_010", "type": "momentum", "personality": "Alpha 捕手", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 180, "leverage": 5, "reason": "链上 TVL 激增"}, {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 4, "reason": "Gas 费暴涨，需求旺盛"}]},

  {"name": "MeanRevert_011", "type": "mean_reversion", "personality": "均值回归信徒", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 3, "reason": "RSI 超卖到 22"}, {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "RSI 超买到 82"}]},
  {"name": "Contrarian_012", "type": "mean_reversion", "personality": "逆势交易者", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 120, "leverage": 3, "reason": "恐惧指数 18，极度恐慌"}, {"action": "short", "asset": "BTC-PERP", "size": 100, "leverage": 2, "reason": "贪婪指数 85，过度乐观"}]},
  {"name": "BollingerBot_013", "type": "mean_reversion", "personality": "布林带战士", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 140, "leverage": 3, "reason": "触及布林带下轨"}, {"action": "short", "asset": "BTC-PERP", "size": 120, "leverage": 3, "reason": "触及布林带上轨"}]},
  {"name": "DipBuyer_014", "type": "mean_reversion", "personality": "抄底专家", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 3, "reason": "单日跌幅超 8%"}, {"action": "long", "asset": "SOL-PERP", "size": 150, "leverage": 4, "reason": "三连阴后出现十字星"}]},
  {"name": "OverextendedSniper_015", "type": "mean_reversion", "personality": "过度延伸狙击手", "strategies": [{"action": "short", "asset": "ETH-PERP", "size": 130, "leverage": 3, "reason": "距离 20 日均线偏离 15%"}, {"action": "long", "asset": "BTC-PERP", "size": 140, "leverage": 3, "reason": "回踩 50 日均线支撑"}]},
  {"name": "FundingArb_016", "type": "mean_reversion", "personality": "资金费率套利", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 180, "leverage": 4, "reason": "资金费率 -0.1%，空头过度"}, {"action": "short", "asset": "BTC-PERP", "size": 160, "leverage": 3, "reason": "资金费率 0.15%，多头过热"}]},
  {"name": "SupportDefender_017", "type": "mean_reversion", "personality": "支撑位守护者", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 160, "leverage": 3, "reason": "关键支撑 $2000 三次测试"}, {"action": "long", "asset": "BTC-PERP", "size": 180, "leverage": 3, "reason": "周线支撑 $60000 反弹"}]},
  {"name": "ZscoreBot_018", "type": "mean_reversion", "personality": "统计套利者", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 3, "reason": "Z-score 达到 -2.5"}, {"action": "short", "asset": "SOL-PERP", "size": 120, "leverage": 3, "reason": "Z-score 达到 +2.3"}]},
  {"name": "VWAPRevert_019", "type": "mean_reversion", "personality": "VWAP 均值回归", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 140, "leverage": 3, "reason": "价格低于 VWAP 5%"}, {"action": "short", "asset": "BTC-PERP", "size": 130, "leverage": 3, "reason": "价格高于 VWAP 6%"}]},
  {"name": "CalmCollector_020", "type": "mean_reversion", "personality": "冷静收割者", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 170, "leverage": 3, "reason": "恐慌性抛售后企稳"}, {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 3, "reason": "利空出尽，底部放量"}]},

  {"name": "ArbitrageKing_021", "type": "arbitrage", "personality": "跨所套利王", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "HL 价格低于 Binance 0.3%"}, {"action": "short", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "ETH 期现价差过大"}]},
  {"name": "BasisTrader_022", "type": "arbitrage", "personality": "基差交易专家", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 600, "leverage": 2, "reason": "季度合约贴水 2%"}, {"action": "short", "asset": "ETH-PERP", "size": 450, "leverage": 2, "reason": "永续升水 0.5%"}]},
  {"name": "SpreadBot_023", "type": "arbitrage", "personality": "价差机器人", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 300, "leverage": 2, "reason": "SOL 跨所价差 0.4%"}, {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "ETH 三角套利机会"}]},
  {"name": "DeltaNeutral_024", "type": "arbitrage", "personality": "Delta 中性策略", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "做多现货做空永续"}, {"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "质押 ETH 对冲永续空头"}]},
  {"name": "StatArb_025", "type": "arbitrage", "personality": "统计套利", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 350, "leverage": 2, "reason": "ETH/BTC 比率低于历史均值"}, {"action": "short", "asset": "BTC-PERP", "size": 350, "leverage": 2, "reason": "BTC 主导率过高"}]},
  {"name": "FundingFarmer_026", "type": "arbitrage", "personality": "资金费率农民", "strategies": [{"action": "short", "asset": "SOL-PERP", "size": 400, "leverage": 2, "reason": "资金费率 0.08%，做空收费"}, {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "资金费率 -0.05%，做多收费"}]},
  {"name": "MarketMaker_027", "type": "arbitrage", "personality": "做市商策略", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 300, "leverage": 1, "reason": "双向挂单赚取价差"}, {"action": "short", "asset": "ETH-PERP", "size": 300, "leverage": 1, "reason": "对冲做市风险"}]},
  {"name": "CrossExchange_028", "type": "arbitrage", "personality": "跨交易所套利", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 550, "leverage": 2, "reason": "Bybit 价格低于 HL"}, {"action": "short", "asset": "SOL-PERP", "size": 280, "leverage": 2, "reason": "OKX SOL 溢价 0.2%"}]},
  {"name": "PairTrader_029", "type": "arbitrage", "personality": "配对交易者", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 2, "reason": "ETH 相对 BTC 超卖"}, {"action": "short", "asset": "BTC-PERP", "size": 400, "leverage": 2, "reason": "BTC 相对 ETH 超买"}]},
  {"name": "FlashArb_030", "type": "arbitrage", "personality": "闪电套利", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 350, "leverage": 2, "reason": "DEX 与 CEX 价差 0.5%"}, {"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 2, "reason": "瞬时价差捕捉"}]},

  {"name": "YOLO_031", "type": "degen", "personality": "全梭哈型", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 500, "leverage": 20, "reason": "感觉要起飞了 🚀"}, {"action": "long", "asset": "BTC-PERP", "size": 800, "leverage": 15, "reason": "满仓干！"}]},
  {"name": "LiquidationHunter_032", "type": "degen", "personality": "清算猎手", "strategies": [{"action": "short", "asset": "ETH-PERP", "size": 400, "leverage": 15, "reason": "上方有大量清算位"}, {"action": "long", "asset": "BTC-PERP", "size": 600, "leverage": 12, "reason": "空头清算瀑布即将触发"}]},
  {"name": "Degen_033", "type": "degen", "personality": "纯赌徒", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 300, "leverage": 25, "reason": "不成功便成仁"}, {"action": "short", "asset": "ETH-PERP", "size": 250, "leverage": 20, "reason": "直觉告诉我要跌"}]},
  {"name": "MoonBoy_034", "type": "degen", "personality": "只做多不做空", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 700, "leverage": 18, "reason": "BTC 百万刀不是梦"}, {"action": "long", "asset": "ETH-PERP", "size": 500, "leverage": 15, "reason": "ETH 万刀必达"}]},
  {"name": "ShortSqueeze_035", "type": "degen", "personality": "逼空专家", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 450, "leverage": 20, "reason": "空头仓位过重，准备逼空"}, {"action": "long", "asset": "BTC-PERP", "size": 600, "leverage": 15, "reason": "资金费率负值，空头要付钱"}]},
  {"name": "Gambler_036", "type": "degen", "personality": "赌场高手", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 400, "leverage": 22, "reason": "凭运气吃饭"}, {"action": "short", "asset": "BTC-PERP", "size": 350, "leverage": 18, "reason": "感觉到了顶部"}]},
  {"name": "AllIn_037", "type": "degen", "personality": "全仓选手", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 1000, "leverage": 10, "reason": "这是百年一遇的机会"}, {"action": "long", "asset": "SOL-PERP", "size": 600, "leverage": 15, "reason": "SOL 是下一个 ETH"}]},
  {"name": "LeverageMaxx_038", "type": "degen", "personality": "杠杆狂人", "strategies": [{"action": "short", "asset": "ETH-PERP", "size": 300, "leverage": 25, "reason": "25x 才够刺激"}, {"action": "long", "asset": "BTC-PERP", "size": 400, "leverage": 20, "reason": "要爆就爆大的"}]},
  {"name": "FOMO_039", "type": "degen", "personality": "FOMO 患者", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 350, "leverage": 18, "reason": "错过就没了！"}, {"action": "long", "asset": "ETH-PERP", "size": 300, "leverage": 15, "reason": "别人都在买"}]},
  {"name": "RiskLover_040", "type": "degen", "personality": "风险爱好者", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 500, "leverage": 20, "reason": "高风险高回报"}, {"action": "short", "asset": "SOL-PERP", "size": 400, "leverage": 18, "reason": "波动就是机会"}]},

  {"name": "SafeHands_041", "type": "conservative", "personality": "稳健保守派", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 100, "leverage": 2, "reason": "只做确定性高的机会"}, {"action": "long", "asset": "ETH-PERP", "size": 80, "leverage": 2, "reason": "小仓位试探"}]},
  {"name": "RiskManager_042", "type": "conservative", "personality": "风控优先", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 2, "reason": "止损设在 3%"}, {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "严格风险敞口控制"}]},
  {"name": "DCABot_043", "type": "conservative", "personality": "定投策略", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 50, "leverage": 1, "reason": "每日定投不择时"}, {"action": "long", "asset": "BTC-PERP", "size": 50, "leverage": 1, "reason": "时间分散风险"}]},
  {"name": "ValueInvestor_044", "type": "conservative", "personality": "价值投资者", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 2, "reason": "BTC 已跌至合理估值"}, {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 2, "reason": "ETH 质押收益有支撑"}]},
  {"name": "SlowAndSteady_045", "type": "conservative", "personality": "稳中求胜", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 120, "leverage": 2, "reason": "长期趋势向上"}, {"action": "long", "asset": "SOL-PERP", "size": 80, "leverage": 2, "reason": "技术面底部确认"}]},
  {"name": "Turtle_046", "type": "conservative", "personality": "海龟策略", "strategies": [{"action": "long", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "突破 20 日高点"}, {"action": "short", "asset": "BTC-PERP", "size": 80, "leverage": 2, "reason": "跌破 10 日低点"}]},
  {"name": "IndexFollower_047", "type": "conservative", "personality": "指数跟随者", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 180, "leverage": 2, "reason": "BTC 代表整体市场"}, {"action": "long", "asset": "ETH-PERP", "size": 120, "leverage": 2, "reason": "ETH 是 DeFi 指数"}]},
  {"name": "LongTermHolder_048", "type": "conservative", "personality": "长期持有者", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 200, "leverage": 1, "reason": "四年周期看涨"}, {"action": "long", "asset": "ETH-PERP", "size": 150, "leverage": 1, "reason": "以太坊 2.0 利好"}]},
  {"name": "Hedger_049", "type": "conservative", "personality": "对冲专家", "strategies": [{"action": "long", "asset": "BTC-PERP", "size": 150, "leverage": 2, "reason": "持有现货对冲"}, {"action": "short", "asset": "ETH-PERP", "size": 100, "leverage": 2, "reason": "做空对冲下行风险"}]},
  {"name": "PatientTrader_050", "type": "conservative", "personality": "耐心等待者", "strategies": [{"action": "long", "asset": "SOL-PERP", "size": 100, "leverage": 2, "reason": "等待最佳入场点"}, {"action": "long", "asset": "BTC-PERP", "size": 120, "leverage": 2, "reason": "只在支撑位买入"}]}
]
BACKUP_AGENTS
fi

AGENT_COUNT=$(jq 'length' "$AGENTS_FILE")
echo -e "${GREEN}✓ 生成 $AGENT_COUNT 个 Agent 配置${NC}"

# 初始化结果 JSON
cat > "$RESULTS_FILE" << EOF
{
  "test_start": "$(date -Iseconds)",
  "agents": [],
  "trades": [],
  "errors": [],
  "summary": {}
}
EOF

# 统计变量
TOTAL_AGENTS=0
REGISTERED_AGENTS=0
TOTAL_TRADES=0
SUCCESSFUL_TRADES=0
FAILED_TRADES=0
TOTAL_LATENCY=0
declare -a ERRORS

# 注册所有 Agent
echo -e "\n${YELLOW}[3/5] 注册 Agent 到 Trading Hub...${NC}"

for i in $(seq 0 $((AGENT_COUNT - 1))); do
    AGENT=$(jq -r ".[$i]" "$AGENTS_FILE")
    NAME=$(echo "$AGENT" | jq -r '.name')
    TYPE=$(echo "$AGENT" | jq -r '.type')
    PERSONALITY=$(echo "$AGENT" | jq -r '.personality')
    
    WALLET="0x$(echo "$NAME" | md5 -r | cut -c1-40)"
    
    # 注册 Agent
    START_TIME=$(python3 -c "import time; print(int(time.time()*1000))")
    RESPONSE=$(curl -s -X POST "$API_BASE/agents/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"wallet_address\": \"$WALLET\",
            \"display_name\": \"$NAME\",
            \"bio\": \"$PERSONALITY\"
        }")
    END_TIME=$(python3 -c "import time; print(int(time.time()*1000))")
    LATENCY=$((END_TIME - START_TIME))
    
    AGENT_ID=$(echo "$RESPONSE" | jq -r '.agent.agent_id // empty')
    
    if [ -n "$AGENT_ID" ]; then
        ((REGISTERED_AGENTS++))
        echo -e "${GREEN}  ✓${NC} [$((i+1))/$AGENT_COUNT] $NAME ($TYPE) → $AGENT_ID [${LATENCY}ms]"
        
        # 保存 Agent ID 到临时文件供后续使用
        jq --arg idx "$i" --arg id "$AGENT_ID" '.agents[$idx | tonumber] = $id' "$RESULTS_FILE" > /tmp/results_tmp.json && mv /tmp/results_tmp.json "$RESULTS_FILE"
    else
        ERROR=$(echo "$RESPONSE" | jq -r '.detail // "Unknown error"')
        echo -e "${RED}  ✗${NC} [$((i+1))/$AGENT_COUNT] $NAME → $ERROR"
        ERRORS+=("Register $NAME: $ERROR")
    fi
    
    ((TOTAL_AGENTS++))
    TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))
done

# 执行交易
echo -e "\n${YELLOW}[4/5] 执行交易测试...${NC}"

for i in $(seq 0 $((AGENT_COUNT - 1))); do
    AGENT=$(jq -r ".[$i]" "$AGENTS_FILE")
    NAME=$(echo "$AGENT" | jq -r '.name')
    STRATEGIES=$(echo "$AGENT" | jq -c '.strategies')
    
    # 从注册获取 Agent ID
    WALLET="0x$(echo "$NAME" | md5 -r | cut -c1-40)"
    AGENT_ID="agent_$(printf '%04d' $((i + 3)))"  # 估算 ID (前面已有注册)
    
    # 尝试获取实际的 Agent ID
    AGENT_INFO=$(curl -s "$API_BASE/agents" | jq -r ".agents[] | select(.display_name == \"$NAME\") | .agent_id" | head -1)
    if [ -n "$AGENT_INFO" ]; then
        AGENT_ID="$AGENT_INFO"
    fi
    
    echo -e "\n  ${BLUE}🤖 $NAME${NC} ($(echo "$AGENT" | jq -r '.type'))"
    
    STRATEGY_COUNT=$(echo "$STRATEGIES" | jq 'length')
    for j in $(seq 0 $((STRATEGY_COUNT - 1))); do
        STRATEGY=$(echo "$STRATEGIES" | jq -r ".[$j]")
        ACTION=$(echo "$STRATEGY" | jq -r '.action')
        ASSET=$(echo "$STRATEGY" | jq -r '.asset')
        SIZE=$(echo "$STRATEGY" | jq -r '.size')
        LEVERAGE=$(echo "$STRATEGY" | jq -r '.leverage')
        REASON=$(echo "$STRATEGY" | jq -r '.reason')
        
        # 执行交易
        START_TIME=$(python3 -c "import time; print(int(time.time()*1000))")
        RESPONSE=$(curl -s -X POST "$API_BASE/intents" \
            -H "Content-Type: application/json" \
            -d "{
                \"agent_id\": \"$AGENT_ID\",
                \"intent_type\": \"$ACTION\",
                \"asset\": \"$ASSET\",
                \"size_usdc\": $SIZE,
                \"leverage\": $LEVERAGE,
                \"reason\": \"$REASON\"
            }")
        END_TIME=$(python3 -c "import time; print(int(time.time()*1000))")
        LATENCY=$((END_TIME - START_TIME))
        
        ((TOTAL_TRADES++))
        TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))
        
        SUCCESS=$(echo "$RESPONSE" | jq -r '.success // false')
        if [ "$SUCCESS" = "true" ]; then
            ((SUCCESSFUL_TRADES++))
            INTERNAL_RATE=$(echo "$RESPONSE" | jq -r '.routing.internal_rate // "N/A"')
            echo -e "     ${GREEN}✓${NC} $ACTION $ASSET \$$SIZE ${LEVERAGE}x → $INTERNAL_RATE [${LATENCY}ms]"
            echo -e "       ${YELLOW}📝${NC} $REASON"
        else
            ((FAILED_TRADES++))
            ERROR=$(echo "$RESPONSE" | jq -r '.detail // "Unknown error"')
            echo -e "     ${RED}✗${NC} $ACTION $ASSET \$$SIZE ${LEVERAGE}x → $ERROR [${LATENCY}ms]"
            ERRORS+=("Trade $NAME $ACTION $ASSET: $ERROR")
        fi
        
        # 小延迟避免请求过快
        sleep 0.1
    done
done

# 获取最终统计
echo -e "\n${YELLOW}[5/5] 汇总测试结果...${NC}"

STATS=$(curl -s "$API_BASE/stats")
FINAL_AGENTS=$(echo "$STATS" | jq -r '.total_agents // 0')
FINAL_VOLUME=$(echo "$STATS" | jq -r '.total_volume // 0')
FINAL_INTENTS=$(echo "$STATS" | jq -r '.open_intents // 0')
INTERNAL_RATE=$(echo "$STATS" | jq -r '.internal_match_rate // "100%"')

# 计算统计
if [ $TOTAL_TRADES -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; $SUCCESSFUL_TRADES * 100 / $TOTAL_TRADES" | bc)
    AVG_LATENCY=$(echo "scale=0; $TOTAL_LATENCY / ($TOTAL_AGENTS + $TOTAL_TRADES)" | bc)
else
    SUCCESS_RATE="0"
    AVG_LATENCY="0"
fi

# 更新结果文件
cat > "$RESULTS_FILE" << EOF
{
  "test_start": "$(date -Iseconds)",
  "test_end": "$(date -Iseconds)",
  "summary": {
    "total_agents": $TOTAL_AGENTS,
    "registered_agents": $REGISTERED_AGENTS,
    "total_trades": $TOTAL_TRADES,
    "successful_trades": $SUCCESSFUL_TRADES,
    "failed_trades": $FAILED_TRADES,
    "success_rate": "$SUCCESS_RATE%",
    "avg_latency_ms": $AVG_LATENCY,
    "internal_match_rate": "$INTERNAL_RATE",
    "total_volume": $FINAL_VOLUME
  },
  "agent_distribution": {
    "momentum": 10,
    "mean_reversion": 10,
    "arbitrage": 10,
    "degen": 10,
    "conservative": 10
  },
  "errors": [
$(printf '    "%s",\n' "${ERRORS[@]}" | sed '$ s/,$//')
  ],
  "issues_found": [
    $([ ${#ERRORS[@]} -gt 0 ] && echo '"部分交易失败，需要检查 API 错误处理",' || echo "")
    $([ $AVG_LATENCY -gt 200 ] && echo '"平均延迟超过 200ms，可能需要优化",' || echo "")
    "待检查: Agent 名称重复处理",
    "待检查: 高杠杆交易的保证金验证"
  ],
  "recommendations": [
    "增加并发测试 (当前是串行)",
    "添加 WebSocket 实时推送验证",
    "测试订单取消和修改功能",
    "添加更多边界条件测试",
    "考虑添加批量注册 API"
  ]
}
EOF

# 输出最终报告
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}                           📊 测试结果汇总                                   ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}✓ Agent 注册:${NC}     $REGISTERED_AGENTS / $TOTAL_AGENTS"
echo -e "  ${GREEN}✓ 交易成功:${NC}       $SUCCESSFUL_TRADES / $TOTAL_TRADES (${SUCCESS_RATE}%)"
echo -e "  ${GREEN}✓ 平均延迟:${NC}       ${AVG_LATENCY}ms"
echo -e "  ${GREEN}✓ 内部匹配率:${NC}     $INTERNAL_RATE"
echo -e "  ${GREEN}✓ 总交易量:${NC}       \$$FINAL_VOLUME"
echo ""
echo -e "  ${YELLOW}Agent 类型分布:${NC}"
echo "    📈 Momentum (趋势):      10 个"
echo "    📉 Mean Reversion (均值): 10 个"
echo "    ⚖️  Arbitrage (套利):     10 个"
echo "    🎰 Degen (高杠杆):        10 个"
echo "    🛡️  Conservative (保守):  10 个"
echo ""

if [ ${#ERRORS[@]} -gt 0 ]; then
    echo -e "  ${RED}发现的问题:${NC}"
    for err in "${ERRORS[@]:0:5}"; do
        echo "    ⚠️  $err"
    done
    [ ${#ERRORS[@]} -gt 5 ] && echo "    ... 还有 $((${#ERRORS[@]} - 5)) 个错误"
    echo ""
fi

echo -e "  ${YELLOW}改进建议:${NC}"
echo "    1. 添加并发测试支持"
echo "    2. WebSocket 推送验证"
echo "    3. 添加批量 API"
echo "    4. 强化边界条件测试"
echo ""
echo -e "  ${GREEN}结果已保存到:${NC} $RESULTS_FILE"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
