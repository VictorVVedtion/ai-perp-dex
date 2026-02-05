#!/bin/bash
# AI Agent 用户体验测试脚本
# 用法: ./agent_test.sh "Agent Name"

set -e
BASE_URL="http://localhost:8082"
AGENT_NAME="${1:-TestAgent}"
WALLET="0x${AGENT_NAME}_$(date +%s)"

echo "═══════════════════════════════════════════════════════════"
echo "🤖 $AGENT_NAME 开始测试 AI Perp DEX"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. 注册
echo "📝 注册账户..."
REG=$(curl -s -X POST "$BASE_URL/agents/register" \
  -H "Content-Type: application/json" \
  -d "{\"wallet_address\": \"$WALLET\", \"display_name\": \"$AGENT_NAME\"}")

API_KEY=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_key',''))" 2>/dev/null)
AGENT_ID=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent',{}).get('agent_id',''))" 2>/dev/null)

if [ -z "$API_KEY" ]; then
  echo "❌ 注册失败: $REG"
  exit 1
fi
echo "✅ 注册成功: $AGENT_ID"

# 2. 领取资金
echo ""
echo "💰 领取测试资金..."
FAUCET=$(curl -s -X POST "$BASE_URL/faucet" -H "X-API-Key: $API_KEY")
BAL=$(echo "$FAUCET" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_balance',0))" 2>/dev/null)
echo "✅ 余额: \$$BAL"

# 3. 查看行情
echo ""
echo "📊 查看市场行情..."
PRICES=$(curl -s "$BASE_URL/prices")
BTC_PRICE=$(echo "$PRICES" | python3 -c "import sys,json; print(json.load(sys.stdin)['prices']['BTC']['price'])" 2>/dev/null)
ETH_PRICE=$(echo "$PRICES" | python3 -c "import sys,json; print(json.load(sys.stdin)['prices']['ETH']['price'])" 2>/dev/null)
echo "   BTC: \$$BTC_PRICE"
echo "   ETH: \$$ETH_PRICE"

# 4. 开仓
echo ""
echo "📈 开仓 BTC Long..."
TRADE=$(curl -s -X POST "$BASE_URL/intents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"intent_type\": \"long\", \"asset\": \"BTC-PERP\", \"size_usdc\": 1000, \"leverage\": 5}")

POS_ID=$(echo "$TRADE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('position',{}).get('position_id',''))" 2>/dev/null)
if [ -n "$POS_ID" ]; then
  echo "✅ 开仓成功: $POS_ID"
else
  echo "❌ 开仓失败: $TRADE"
fi

# 5. 查看持仓
echo ""
echo "📋 查看持仓..."
POSITIONS=$(curl -s "$BASE_URL/positions/$AGENT_ID")
POS_COUNT=$(echo "$POSITIONS" | python3 -c "import sys,json; print(len([p for p in json.load(sys.stdin).get('positions',[]) if p.get('is_open')]))" 2>/dev/null)
echo "   持仓数: $POS_COUNT"

# 6. 创建 Signal
echo ""
echo "🎯 发布 Signal 预测..."
TARGET=$(python3 -c "print(int($BTC_PRICE) + 1000)")
SIGNAL=$(curl -s -X POST "$BASE_URL/signals" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"asset\": \"BTC-PERP\", \"signal_type\": \"price_above\", \"target_value\": $TARGET, \"stake_amount\": 100, \"duration_hours\": 24}")

SIG_ID=$(echo "$SIGNAL" | python3 -c "import sys,json; print(json.load(sys.stdin).get('signal',{}).get('signal_id',''))" 2>/dev/null)
if [ -n "$SIG_ID" ]; then
  echo "✅ Signal 发布: BTC > \$$TARGET"
else
  echo "❌ Signal 失败: $SIGNAL"
fi

# 7. 平仓
echo ""
echo "💵 平仓..."
if [ -n "$POS_ID" ]; then
  CLOSE=$(curl -s -X POST "$BASE_URL/positions/$POS_ID/close" -H "X-API-Key: $API_KEY")
  echo "✅ 平仓完成"
fi

# 8. 最终余额
echo ""
echo "💰 最终余额..."
FINAL_BAL=$(curl -s "$BASE_URL/balance/$AGENT_ID" | python3 -c "import sys,json; print(json.load(sys.stdin).get('balance',0))" 2>/dev/null)
echo "   余额: \$$FINAL_BAL"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ $AGENT_NAME 测试完成!"
echo "═══════════════════════════════════════════════════════════"

# 输出评价
echo ""
echo "📋 $AGENT_NAME 的评价:"
echo "   请在下方提供你的测试体验反馈..."
