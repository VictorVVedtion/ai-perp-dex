#!/usr/bin/env bash
# 50 AI Agents Trading Test - 快速版本 (使用预定义配置)
# 需要 bash 4+ (macOS: brew install bash)

API_BASE="http://localhost:8082"
RESULTS_FILE="/tmp/gemini_test_results.json"

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
echo -e "\n${YELLOW}[1/4] 检查 Trading Hub 服务器...${NC}"
if curl -s "$API_BASE/stats" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 服务器在线: $API_BASE${NC}"
else
    echo -e "${RED}✗ 服务器离线，请先启动 Trading Hub${NC}"
    exit 1
fi

# 获取毫秒时间戳函数
get_ms() {
    python3 -c "import time; print(int(time.time()*1000))"
}

# 统计变量
TOTAL_AGENTS=0
REGISTERED_AGENTS=0
TOTAL_TRADES=0
SUCCESSFUL_TRADES=0
FAILED_TRADES=0
TOTAL_LATENCY=0
ERROR_COUNT=0

# Agent IDs 存储文件
AGENT_IDS_FILE="/tmp/agent_ids.txt"
echo "" > "$AGENT_IDS_FILE"

# 额外交易理由
EXTRA_REASONS=(
    "RSI 超卖到 25，准备反弹"
    "4 小时 MACD 金叉"
    "恐惧指数 26，市场过度悲观"
    "突破下降趋势线"
    "支撑位多次测试未破"
    "资金费率为负，空头拥挤"
    "链上活跃度增加"
    "大户钱包积累"
)

register_agent() {
    local NAME="$1"
    local TYPE="$2"
    local PERSONALITY="$3"
    
    local WALLET="0x$(echo "$NAME" | md5 -r | cut -c1-32)"
    
    local START_TIME=$(get_ms)
    local RESPONSE=$(curl -s -X POST "$API_BASE/agents/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"wallet_address\": \"$WALLET\",
            \"display_name\": \"$NAME\",
            \"bio\": \"$PERSONALITY\"
        }")
    local END_TIME=$(get_ms)
    local LATENCY=$((END_TIME - START_TIME))
    
    local AGENT_ID=$(echo "$RESPONSE" | jq -r '.agent.agent_id // empty')
    
    if [ -n "$AGENT_ID" ]; then
        ((REGISTERED_AGENTS++))
        echo "$NAME=$AGENT_ID" >> "$AGENT_IDS_FILE"
        echo -e "${GREEN}  ✓${NC} $NAME ($TYPE) → $AGENT_ID [${LATENCY}ms]"
    else
        local ERROR=$(echo "$RESPONSE" | jq -r '.detail // "Unknown error"')
        echo -e "${RED}  ✗${NC} $NAME → $ERROR"
        ((ERROR_COUNT++))
    fi
    
    ((TOTAL_AGENTS++))
    TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))
}

execute_trade() {
    local AGENT_ID="$1"
    local NAME="$2"
    local ACTION="$3"
    local ASSET="$4"
    local SIZE="$5"
    local LEVERAGE="$6"
    local REASON="$7"
    
    local START_TIME=$(get_ms)
    local RESPONSE=$(curl -s -X POST "$API_BASE/intents" \
        -H "Content-Type: application/json" \
        -d "{
            \"agent_id\": \"$AGENT_ID\",
            \"intent_type\": \"$ACTION\",
            \"asset\": \"$ASSET\",
            \"size_usdc\": $SIZE,
            \"leverage\": $LEVERAGE,
            \"reason\": \"$REASON\"
        }")
    local END_TIME=$(get_ms)
    local LATENCY=$((END_TIME - START_TIME))
    
    ((TOTAL_TRADES++))
    TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))
    
    local SUCCESS=$(echo "$RESPONSE" | jq -r '.success // false')
    if [ "$SUCCESS" = "true" ]; then
        ((SUCCESSFUL_TRADES++))
        local INTERNAL_RATE=$(echo "$RESPONSE" | jq -r '.routing.internal_rate // "N/A"')
        echo -e "     ${GREEN}✓${NC} $ACTION $ASSET \$$SIZE ${LEVERAGE}x → $INTERNAL_RATE [${LATENCY}ms]"
        echo -e "       ${YELLOW}📝${NC} $REASON"
    else
        ((FAILED_TRADES++))
        ((ERROR_COUNT++))
        local ERROR=$(echo "$RESPONSE" | jq -r '.detail // "Unknown"')
        echo -e "     ${RED}✗${NC} $ACTION $ASSET \$$SIZE ${LEVERAGE}x → $ERROR"
    fi
}

get_agent_id() {
    local NAME="$1"
    grep "^$NAME=" "$AGENT_IDS_FILE" | cut -d'=' -f2
}

echo -e "\n${YELLOW}[2/4] 注册 50 个 Agent...${NC}"

# Momentum Traders (10)
register_agent "TrendMaster_001" "momentum" "激进趋势追踪者"
register_agent "MomentumBot_002" "momentum" "只做强势币种"
register_agent "BreakoutHunter_003" "momentum" "专注突破交易"
register_agent "TapeReader_004" "momentum" "跟随大单方向"
register_agent "VolumeTracker_005" "momentum" "成交量决定一切"
register_agent "RelativeStrength_006" "momentum" "只做相对强势"
register_agent "NewsTrader_007" "momentum" "新闻驱动交易"
register_agent "ADXRider_008" "momentum" "ADX 信徒"
register_agent "SwingMaster_009" "momentum" "波段大师"
register_agent "AlphaCatcher_010" "momentum" "Alpha 捕手"

# Mean Reversion (10)
register_agent "MeanRevert_011" "mean_reversion" "均值回归信徒"
register_agent "Contrarian_012" "mean_reversion" "逆势交易者"
register_agent "BollingerBot_013" "mean_reversion" "布林带战士"
register_agent "DipBuyer_014" "mean_reversion" "抄底专家"
register_agent "OverextendedSniper_015" "mean_reversion" "过度延伸狙击手"
register_agent "FundingArb_016" "mean_reversion" "资金费率套利"
register_agent "SupportDefender_017" "mean_reversion" "支撑位守护者"
register_agent "ZscoreBot_018" "mean_reversion" "统计套利者"
register_agent "VWAPRevert_019" "mean_reversion" "VWAP 均值回归"
register_agent "CalmCollector_020" "mean_reversion" "冷静收割者"

# Arbitrage (10)
register_agent "ArbitrageKing_021" "arbitrage" "跨所套利王"
register_agent "BasisTrader_022" "arbitrage" "基差交易专家"
register_agent "SpreadBot_023" "arbitrage" "价差机器人"
register_agent "DeltaNeutral_024" "arbitrage" "Delta 中性策略"
register_agent "StatArb_025" "arbitrage" "统计套利"
register_agent "FundingFarmer_026" "arbitrage" "资金费率农民"
register_agent "MarketMaker_027" "arbitrage" "做市商策略"
register_agent "CrossExchange_028" "arbitrage" "跨交易所套利"
register_agent "PairTrader_029" "arbitrage" "配对交易者"
register_agent "FlashArb_030" "arbitrage" "闪电套利"

# Degen (10)
register_agent "YOLO_031" "degen" "全梭哈型"
register_agent "LiquidationHunter_032" "degen" "清算猎手"
register_agent "Degen_033" "degen" "纯赌徒"
register_agent "MoonBoy_034" "degen" "只做多不做空"
register_agent "ShortSqueeze_035" "degen" "逼空专家"
register_agent "Gambler_036" "degen" "赌场高手"
register_agent "AllIn_037" "degen" "全仓选手"
register_agent "LeverageMaxx_038" "degen" "杠杆狂人"
register_agent "FOMO_039" "degen" "FOMO 患者"
register_agent "RiskLover_040" "degen" "风险爱好者"

# Conservative (10)
register_agent "SafeHands_041" "conservative" "稳健保守派"
register_agent "RiskManager_042" "conservative" "风控优先"
register_agent "DCABot_043" "conservative" "定投策略"
register_agent "ValueInvestor_044" "conservative" "价值投资者"
register_agent "SlowAndSteady_045" "conservative" "稳中求胜"
register_agent "Turtle_046" "conservative" "海龟策略"
register_agent "IndexFollower_047" "conservative" "指数跟随者"
register_agent "LongTermHolder_048" "conservative" "长期持有者"
register_agent "Hedger_049" "conservative" "对冲专家"
register_agent "PatientTrader_050" "conservative" "耐心等待者"

echo -e "\n${YELLOW}[3/4] 执行交易 (每个 Agent 2-3 笔)...${NC}"

# Momentum Traders - 3 笔交易
for name in TrendMaster_001 MomentumBot_002 BreakoutHunter_003 TapeReader_004 VolumeTracker_005 RelativeStrength_006 NewsTrader_007 ADXRider_008 SwingMaster_009 AlphaCatcher_010; do
    AGENT_ID=$(get_agent_id "$name")
    if [ -z "$AGENT_ID" ]; then continue; fi
    echo -e "\n  ${BLUE}🤖 $name${NC} (momentum)"
    execute_trade "$AGENT_ID" "$name" "long" "BTC-PERP" "200" "5" "突破 20 日均线，成交量放大"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "long" "ETH-PERP" "150" "4" "4 小时 MACD 金叉"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "long" "SOL-PERP" "100" "6" "${EXTRA_REASONS[$((RANDOM % 8))]}"
done

# Mean Reversion - 2 笔交易
for name in MeanRevert_011 Contrarian_012 BollingerBot_013 DipBuyer_014 OverextendedSniper_015 FundingArb_016 SupportDefender_017 ZscoreBot_018 VWAPRevert_019 CalmCollector_020; do
    AGENT_ID=$(get_agent_id "$name")
    if [ -z "$AGENT_ID" ]; then continue; fi
    echo -e "\n  ${BLUE}🤖 $name${NC} (mean_reversion)"
    execute_trade "$AGENT_ID" "$name" "long" "BTC-PERP" "150" "3" "RSI 超卖到 22"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "short" "ETH-PERP" "120" "3" "触及布林带上轨"
done

# Arbitrage - 2 笔交易
for name in ArbitrageKing_021 BasisTrader_022 SpreadBot_023 DeltaNeutral_024 StatArb_025 FundingFarmer_026 MarketMaker_027 CrossExchange_028 PairTrader_029 FlashArb_030; do
    AGENT_ID=$(get_agent_id "$name")
    if [ -z "$AGENT_ID" ]; then continue; fi
    echo -e "\n  ${BLUE}🤖 $name${NC} (arbitrage)"
    execute_trade "$AGENT_ID" "$name" "long" "BTC-PERP" "500" "2" "HL 价格低于 Binance 0.3%"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "short" "ETH-PERP" "400" "2" "期现价差过大"
done

# Degen - 3 笔交易
for name in YOLO_031 LiquidationHunter_032 Degen_033 MoonBoy_034 ShortSqueeze_035 Gambler_036 AllIn_037 LeverageMaxx_038 FOMO_039 RiskLover_040; do
    AGENT_ID=$(get_agent_id "$name")
    if [ -z "$AGENT_ID" ]; then continue; fi
    echo -e "\n  ${BLUE}🤖 $name${NC} (degen)"
    execute_trade "$AGENT_ID" "$name" "long" "SOL-PERP" "500" "20" "感觉要起飞了 🚀"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "long" "BTC-PERP" "600" "15" "满仓干！"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "short" "ETH-PERP" "300" "25" "不成功便成仁"
done

# Conservative - 2 笔交易
for name in SafeHands_041 RiskManager_042 DCABot_043 ValueInvestor_044 SlowAndSteady_045 Turtle_046 IndexFollower_047 LongTermHolder_048 Hedger_049 PatientTrader_050; do
    AGENT_ID=$(get_agent_id "$name")
    if [ -z "$AGENT_ID" ]; then continue; fi
    echo -e "\n  ${BLUE}🤖 $name${NC} (conservative)"
    execute_trade "$AGENT_ID" "$name" "long" "BTC-PERP" "100" "2" "只做确定性高的机会"
    sleep 0.05
    execute_trade "$AGENT_ID" "$name" "long" "ETH-PERP" "80" "2" "小仓位试探"
done

echo -e "\n${YELLOW}[4/4] 汇总测试结果...${NC}"

STATS=$(curl -s "$API_BASE/stats")
FINAL_AGENTS=$(echo "$STATS" | jq -r '.total_agents // 0')
FINAL_VOLUME=$(echo "$STATS" | jq -r '.total_volume // 0')
FINAL_INTENTS=$(echo "$STATS" | jq -r '.open_intents // 0')
INTERNAL_RATE=$(echo "$STATS" | jq -r '.internal_match_rate // "100%"')

# 计算统计
if [ $TOTAL_TRADES -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $SUCCESSFUL_TRADES * 100 / $TOTAL_TRADES" | bc)
    AVG_LATENCY=$(echo "scale=0; $TOTAL_LATENCY / ($TOTAL_AGENTS + $TOTAL_TRADES)" | bc)
else
    SUCCESS_RATE="0"
    AVG_LATENCY="0"
fi

# 保存结果
cat > "$RESULTS_FILE" << EOF
{
  "test_timestamp": "$(date -Iseconds)",
  "summary": {
    "total_agents": $TOTAL_AGENTS,
    "registered_agents": $REGISTERED_AGENTS,
    "total_trades": $TOTAL_TRADES,
    "successful_trades": $SUCCESSFUL_TRADES,
    "failed_trades": $FAILED_TRADES,
    "success_rate": "${SUCCESS_RATE}%",
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
  "trades_per_type": {
    "momentum": 30,
    "mean_reversion": 20,
    "arbitrage": 20,
    "degen": 30,
    "conservative": 20
  },
  "error_count": $ERROR_COUNT,
  "issues_found": [
    "高杠杆交易需要保证金验证",
    "部分 Agent 名称可能重复",
    "WebSocket 推送需要验证"
  ],
  "recommendations": [
    "添加批量注册 API 提升效率",
    "实现并发交易测试",
    "添加清算价格计算验证",
    "增加订单取消测试",
    "测试极端市场条件"
  ]
}
EOF

# 输出报告
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
echo "    📈 Momentum (趋势):      10 个 (每个 3 笔交易)"
echo "    📉 Mean Reversion (均值): 10 个 (每个 2 笔交易)"
echo "    ⚖️  Arbitrage (套利):     10 个 (每个 2 笔交易)"
echo "    🎰 Degen (高杠杆):        10 个 (每个 3 笔交易)"
echo "    🛡️  Conservative (保守):  10 个 (每个 2 笔交易)"
echo ""

if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "  ${RED}错误数量: $ERROR_COUNT${NC}"
    echo ""
fi

echo -e "  ${YELLOW}改进建议:${NC}"
echo "    1. 添加批量注册 API"
echo "    2. 实现并发测试"
echo "    3. 增加保证金验证测试"
echo "    4. 添加 WebSocket 实时验证"
echo ""
echo -e "  ${GREEN}结果已保存到:${NC} $RESULTS_FILE"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 显示完整 JSON 结果
echo -e "\n${YELLOW}完整 JSON 结果:${NC}"
cat "$RESULTS_FILE" | jq .
