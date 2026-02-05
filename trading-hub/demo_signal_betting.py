"""
Signal Betting Demo - 预测对赌演示

展示 100% 内部匹配的 Signal 对赌功能
"""

import requests
import time

API = "http://localhost:8082"

def demo():
    print("🎲 SIGNAL BETTING DEMO")
    print("=" * 50)
    print("100% Internal Match - Zero External Fees!")
    print()
    
    # Seed
    requests.post(f"{API}/demo/seed")
    
    # 获取当前价格
    prices = requests.post("https://api.hyperliquid.xyz/info", 
                          json={"type": "allMids"}).json()
    eth_price = float(prices.get("ETH", 2150))
    btc_price = float(prices.get("BTC", 73000))
    
    print(f"📈 Current Prices:")
    print(f"   ETH: ${eth_price:,.2f}")
    print(f"   BTC: ${btc_price:,.2f}")
    print()
    
    # Signal 1: Agent_1 看涨 ETH
    target = eth_price * 1.05  # +5%
    print(f"📢 Signal 1: Agent_1 predicts ETH > ${target:,.0f}")
    resp = requests.post(f"{API}/signals", json={
        "agent_id": "agent_0001",
        "asset": "ETH-PERP",
        "signal_type": "price_above",
        "target_value": target,
        "stake_amount": 25,
        "duration_hours": 24,
    }).json()
    signal1_id = resp["signal"]["signal_id"]
    print(f"   Stake: $25")
    print(f"   Signal ID: {signal1_id}")
    print()
    
    # Signal 2: Agent_3 看跌 BTC
    target2 = btc_price * 0.95  # -5%
    print(f"📢 Signal 2: Agent_3 predicts BTC < ${target2:,.0f}")
    resp = requests.post(f"{API}/signals", json={
        "agent_id": "agent_0003",
        "asset": "BTC-PERP",
        "signal_type": "price_below",
        "target_value": target2,
        "stake_amount": 50,
        "duration_hours": 24,
    }).json()
    signal2_id = resp["signal"]["signal_id"]
    print(f"   Stake: $50")
    print(f"   Signal ID: {signal2_id}")
    print()
    
    # 显示开放的 Signals
    print("📋 Open Signals:")
    signals = requests.get(f"{API}/signals").json()["signals"]
    for s in signals:
        print(f"   [{s['signal_id'][:8]}] {s['asset']} {s['signal_type']} ${s['target_value']:,.0f} - ${s['stake_amount']}")
    print()
    
    # Fade
    print("🎯 Agent_2 fades Signal 1 (thinks ETH won't reach target)")
    resp = requests.post(f"{API}/signals/fade", json={
        "signal_id": signal1_id,
        "fader_id": "agent_0002",
    }).json()
    bet1_id = resp["bet"]["bet_id"]
    print(f"   Bet created! Pot: ${resp['bet']['total_pot']}")
    print()
    
    print("🎯 Agent_4 fades Signal 2 (thinks BTC won't drop)")
    resp = requests.post(f"{API}/signals/fade", json={
        "signal_id": signal2_id,
        "fader_id": "agent_0004",
    }).json()
    bet2_id = resp["bet"]["bet_id"]
    print(f"   Bet created! Pot: ${resp['bet']['total_pot']}")
    print()
    
    # 结算 (模拟)
    print("⏰ Fast-forward to settlement...")
    print()
    
    # Bet 1: ETH 没涨到目标，Fader 赢
    print(f"📊 Settling Bet 1 @ ETH ${eth_price:,.2f}")
    resp = requests.post(f"{API}/bets/{bet1_id}/settle", params={"price": eth_price}).json()
    print(f"   Winner: {resp['winner_id']} 🏆")
    print(f"   Payout: ${resp['payout']:.2f}")
    print()
    
    # Bet 2: BTC 也没跌到目标，Fader 赢
    print(f"📊 Settling Bet 2 @ BTC ${btc_price:,.2f}")
    resp = requests.post(f"{API}/bets/{bet2_id}/settle", params={"price": btc_price}).json()
    print(f"   Winner: {resp['winner_id']} 🏆")
    print(f"   Payout: ${resp['payout']:.2f}")
    print()
    
    # 统计
    print("=" * 50)
    print("📈 BETTING STATS")
    stats = requests.get(f"{API}/betting/stats").json()
    print(f"   Total Signals: {stats['total_signals']}")
    print(f"   Total Bets: {stats['total_bets']}")
    print(f"   Total Volume: ${stats['total_volume']:.2f}")
    print(f"   Protocol Fees: ${stats['protocol_fees']:.2f}")
    print(f"   Internal Match Rate: {stats['internal_match_rate']}")
    print()
    
    # Agent 统计
    print("🤖 Agent Performance:")
    for agent_id in ["agent_0001", "agent_0002", "agent_0003", "agent_0004"]:
        stats = requests.get(f"{API}/agents/{agent_id}/betting").json()
        if stats["wins"] + stats["losses"] > 0:
            print(f"   {agent_id}: {stats['wins']}W/{stats['losses']}L (${stats['net_pnl']:+.2f})")

if __name__ == "__main__":
    demo()
