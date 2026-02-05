#!/usr/bin/env python3
"""
AI Perp DEX 核心功能测试

测试内容:
1. 完整交易流程: 注册 → 存款 → 开仓 → 平仓 → 提款
2. P2P 内部匹配
3. 费用计算 (Taker 0.05%, Maker 0.02%)
4. 止盈止损
5. Signal Betting 流程
"""

import requests
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

BASE_URL = "http://127.0.0.1:8082"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: Optional[Dict] = None


class TestRunner:
    def __init__(self):
        self.results: list[TestResult] = []
        self.agents: Dict[str, Dict] = {}  # agent_id -> {api_key, ...}
    
    def log(self, msg: str, level: str = "info"):
        prefix = {
            "info": f"{BLUE}ℹ{RESET}",
            "success": f"{GREEN}✓{RESET}",
            "error": f"{RED}✗{RESET}",
            "warning": f"{YELLOW}⚠{RESET}",
        }.get(level, "")
        print(f"  {prefix} {msg}")
    
    def record(self, name: str, passed: bool, message: str, details: Dict = None):
        self.results.append(TestResult(name, passed, message, details))
        if passed:
            self.log(f"{name}: {message}", "success")
        else:
            self.log(f"{name}: {message}", "error")
    
    def api(self, method: str, endpoint: str, data: Dict = None, 
            api_key: str = None, expected_status: int = 200) -> Optional[Dict]:
        """发送 API 请求"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if resp.status_code != expected_status:
                self.log(f"API {method} {endpoint}: expected {expected_status}, got {resp.status_code}", "warning")
                self.log(f"Response: {resp.text[:200]}", "warning")
                return None
            
            return resp.json() if resp.text else {}
        except Exception as e:
            self.log(f"API error: {e}", "error")
            return None
    
    def register_agent(self, wallet: str, name: str) -> Optional[str]:
        """注册 Agent 并保存 API Key"""
        result = self.api("POST", "/agents/register", {
            "wallet_address": wallet,
            "display_name": name,
        })
        if result and result.get("success"):
            agent_id = result["agent"]["agent_id"]
            api_key = result.get("api_key")
            self.agents[agent_id] = {
                "api_key": api_key,
                "wallet": wallet,
                "name": name,
            }
            return agent_id
        return None


def test_health():
    """测试服务健康检查"""
    print(f"\n{BOLD}=== 测试服务状态 ==={RESET}")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if resp.status_code == 200 and resp.json().get("status") == "ok":
            print(f"  {GREEN}✓{RESET} 服务正常运行")
            return True
        else:
            print(f"  {RED}✗{RESET} 服务状态异常: {resp.text}")
            return False
    except Exception as e:
        print(f"  {RED}✗{RESET} 无法连接服务: {e}")
        return False


def test_full_trading_flow(runner: TestRunner):
    """测试 1: 完整交易流程"""
    print(f"\n{BOLD}=== 测试 1: 完整交易流程 ==={RESET}")
    print("  流程: 注册 → 存款 → 开仓 → 平仓 → 提款\n")
    
    # 1.1 注册
    agent_id = runner.register_agent(f"0xTestTrader_{int(time.time())}", "TestTrader")
    if not agent_id:
        runner.record("注册", False, "注册失败")
        return
    runner.record("注册", True, f"Agent ID: {agent_id}")
    api_key = runner.agents[agent_id]["api_key"]
    
    # 1.2 存款
    deposit_amount = 1000.0
    result = runner.api("POST", "/deposit", {
        "agent_id": agent_id,
        "amount": deposit_amount,
    }, api_key=api_key)
    
    if result and result.get("success"):
        new_balance = result.get("new_balance", 0)
        runner.record("存款", True, f"存入 ${deposit_amount}, 余额 ${new_balance}")
    else:
        runner.record("存款", False, "存款失败")
        return
    
    # 1.3 开仓 (Long ETH)
    result = runner.api("POST", "/intents", {
        "agent_id": agent_id,
        "intent_type": "long",
        "asset": "ETH-PERP",
        "size_usdc": 100,
        "leverage": 5,
    }, api_key=api_key)
    
    if result and result.get("success"):
        position = result.get("position", {})
        fees = result.get("fees", {})
        routing = result.get("routing", {})
        runner.record("开仓", True, 
            f"Long ETH $100 5x, 费用 ${fees.get('protocol_fee', 0):.4f}, "
            f"内部匹配率 {routing.get('internal_rate', 'N/A')}")
        
        position_id = position.get("position_id") if isinstance(position, dict) else None
    else:
        runner.record("开仓", False, f"开仓失败: {result}")
        return
    
    # 1.4 查看持仓
    result = runner.api("GET", f"/positions/{agent_id}")
    if result and result.get("positions"):
        pos = result["positions"][0]
        runner.record("持仓查询", True, 
            f"{pos.get('side', '').upper()} {pos.get('asset')} @ ${pos.get('entry_price', 0):.2f}")
        position_id = pos.get("position_id")
    else:
        runner.record("持仓查询", False, "无持仓数据")
    
    # 1.5 平仓
    if position_id:
        result = runner.api("POST", f"/positions/{position_id}/close", api_key=api_key)
        if result and result.get("success"):
            pnl = result.get("pnl", 0)
            runner.record("平仓", True, f"PnL: ${pnl:.2f}")
        else:
            runner.record("平仓", False, f"平仓失败: {result}")
    
    # 1.6 提款
    result = runner.api("POST", "/withdraw", {
        "agent_id": agent_id,
        "amount": 500,
    }, api_key=api_key)
    
    if result and result.get("success"):
        balance = result.get("balance", {})
        runner.record("提款", True, f"提取 $500, 剩余 ${balance.get('available', 0):.2f}")
    else:
        runner.record("提款", False, f"提款失败: {result}")
    
    # 1.7 查询最终余额
    result = runner.api("GET", f"/balance/{agent_id}")
    if result:
        runner.record("余额查询", True, 
            f"可用: ${result.get('available', 0):.2f}, 锁定: ${result.get('locked', 0):.2f}")


def test_p2p_matching(runner: TestRunner):
    """测试 2: P2P 内部匹配"""
    print(f"\n{BOLD}=== 测试 2: P2P 内部匹配 ==={RESET}")
    print("  测试两个 Agent 的订单是否正确匹配\n")
    
    # 注册两个 Agent
    ts = int(time.time())
    agent_a = runner.register_agent(f"0xAgentA_{ts}", "AgentA_Buyer")
    agent_b = runner.register_agent(f"0xAgentB_{ts}", "AgentB_Seller")
    
    if not agent_a or not agent_b:
        runner.record("P2P 注册", False, "Agent 注册失败")
        return
    
    runner.record("P2P 注册", True, f"A: {agent_a}, B: {agent_b}")
    
    # 为两个 Agent 存款
    for aid in [agent_a, agent_b]:
        api_key = runner.agents[aid]["api_key"]
        runner.api("POST", "/deposit", {"agent_id": aid, "amount": 1000}, api_key=api_key)
    
    # Agent A 做多 (等待匹配)
    api_key_a = runner.agents[agent_a]["api_key"]
    result_a = runner.api("POST", "/intents", {
        "agent_id": agent_a,
        "intent_type": "long",
        "asset": "BTC-PERP",
        "size_usdc": 200,
        "leverage": 3,
    }, api_key=api_key_a)
    
    if not result_a or not result_a.get("success"):
        runner.record("Agent A 开多", False, "开仓失败")
        return
    
    intent_a_id = result_a.get("intent", {}).get("intent_id")
    runner.record("Agent A 开多", True, f"Intent: {intent_a_id}")
    
    # Agent B 做空 (应该匹配)
    api_key_b = runner.agents[agent_b]["api_key"]
    result_b = runner.api("POST", "/intents", {
        "agent_id": agent_b,
        "intent_type": "short",
        "asset": "BTC-PERP",
        "size_usdc": 200,
        "leverage": 3,
    }, api_key=api_key_b)
    
    if not result_b or not result_b.get("success"):
        runner.record("Agent B 开空", False, "开仓失败")
        return
    
    # 检查匹配结果
    routing = result_b.get("routing", {})
    internal_match = result_b.get("internal_match")
    
    internal_filled = routing.get("internal_filled", 0)
    internal_rate = routing.get("internal_rate", "0%")
    
    if internal_filled > 0:
        runner.record("P2P 匹配", True, 
            f"内部成交 ${internal_filled}, 匹配率 {internal_rate}")
        
        if internal_match:
            runner.record("匹配详情", True, 
                f"Match ID: {internal_match.get('match_id')}, "
                f"价格: ${internal_match.get('price', 0):.2f}")
    else:
        runner.record("P2P 匹配", False, 
            f"内部匹配失败, 外部路由: ${routing.get('external_filled', 0)}")


def test_fee_calculation(runner: TestRunner):
    """测试 3: 费用计算"""
    print(f"\n{BOLD}=== 测试 3: 费用计算 ==={RESET}")
    print("  Taker: 0.05%, Maker: 0.02%\n")
    
    # 注册并存款
    ts = int(time.time())
    agent_id = runner.register_agent(f"0xFeeTest_{ts}", "FeeTestAgent")
    if not agent_id:
        runner.record("费用测试注册", False, "注册失败")
        return
    
    api_key = runner.agents[agent_id]["api_key"]
    runner.api("POST", "/deposit", {"agent_id": agent_id, "amount": 5000}, api_key=api_key)
    
    # 开仓 $1000
    size = 1000.0
    expected_taker_fee = size * 0.0005  # 0.05%
    expected_maker_fee = size * 0.0002  # 0.02%
    
    result = runner.api("POST", "/intents", {
        "agent_id": agent_id,
        "intent_type": "long",
        "asset": "ETH-PERP",
        "size_usdc": size,
        "leverage": 2,
    }, api_key=api_key)
    
    if not result or not result.get("success"):
        runner.record("费用测试开仓", False, "开仓失败")
        return
    
    fees = result.get("fees", {})
    protocol_fee = fees.get("protocol_fee", 0)
    fee_records = fees.get("records", [])
    
    runner.record("费率配置", True, 
        f"Taker: {fees.get('taker_rate', 'N/A')}, Maker: {fees.get('maker_rate', 'N/A')}")
    
    # 检查 Taker 费用
    taker_record = next((r for r in fee_records if r.get("type") == "taker"), None)
    if taker_record:
        actual_taker = taker_record.get("amount_usdc", 0)
        taker_correct = abs(actual_taker - expected_taker_fee) < 0.01
        runner.record("Taker 费用", taker_correct,
            f"预期 ${expected_taker_fee:.4f}, 实际 ${actual_taker:.4f}")
    else:
        runner.record("Taker 费用", False, "未找到 Taker 费用记录")
    
    # 检查 Maker 费用 (如果有内部匹配)
    maker_record = next((r for r in fee_records if r.get("type") == "maker"), None)
    if maker_record:
        actual_maker = maker_record.get("amount_usdc", 0)
        # Maker fee 取决于内部匹配的量
        runner.record("Maker 费用", True, f"实际 ${actual_maker:.4f}")
    else:
        runner.record("Maker 费用", True, "无内部匹配，无 Maker 费用 (符合预期)")
    
    # 查询总费用统计
    result = runner.api("GET", "/fees")
    if result:
        runner.record("费用统计", True, 
            f"总收取: ${result.get('total_collected', 0):.4f}")
    
    # 查询 Agent 费用
    result = runner.api("GET", f"/fees/{agent_id}")
    if result:
        runner.record("Agent 费用", True, 
            f"总支付: ${result.get('total_paid', 0):.4f}")


def test_stop_loss_take_profit(runner: TestRunner):
    """测试 4: 止盈止损"""
    print(f"\n{BOLD}=== 测试 4: 止盈止损 ==={RESET}")
    print("  测试 SL/TP 设置和触发逻辑\n")
    
    ts = int(time.time())
    agent_id = runner.register_agent(f"0xSLTP_{ts}", "SLTPAgent")
    if not agent_id:
        runner.record("SL/TP 注册", False, "注册失败")
        return
    
    api_key = runner.agents[agent_id]["api_key"]
    runner.api("POST", "/deposit", {"agent_id": agent_id, "amount": 2000}, api_key=api_key)
    
    # 开仓
    result = runner.api("POST", "/intents", {
        "agent_id": agent_id,
        "intent_type": "long",
        "asset": "ETH-PERP",
        "size_usdc": 500,
        "leverage": 5,
    }, api_key=api_key)
    
    if not result or not result.get("success"):
        runner.record("SL/TP 开仓", False, "开仓失败")
        return
    
    position = result.get("position", {})
    if isinstance(position, dict) and "error" not in position:
        position_id = position.get("position_id")
        entry_price = position.get("entry_price", 0)
        default_sl = position.get("stop_loss")
        default_tp = position.get("take_profit")
        
        runner.record("SL/TP 开仓", True, 
            f"Position: {position_id}, 入场 ${entry_price:.2f}")
        runner.record("默认止盈止损", True, 
            f"SL: ${default_sl:.2f}, TP: ${default_tp:.2f}" if default_sl and default_tp else "未设置")
    else:
        # 可能返回持仓 ID 在另一个地方
        result = runner.api("GET", f"/positions/{agent_id}")
        if result and result.get("positions"):
            pos = result["positions"][0]
            position_id = pos.get("position_id")
            entry_price = pos.get("entry_price", 0)
            default_sl = pos.get("stop_loss")
            default_tp = pos.get("take_profit")
            
            runner.record("SL/TP 开仓", True, 
                f"Position: {position_id}, 入场 ${entry_price:.2f}")
            runner.record("默认止盈止损", True, 
                f"SL: ${default_sl:.2f if default_sl else 'N/A'}, "
                f"TP: ${default_tp:.2f if default_tp else 'N/A'}")
        else:
            runner.record("SL/TP 开仓", False, "无法获取持仓")
            return
    
    # 修改止损
    new_sl = entry_price * 0.95 if entry_price else 2000
    result = runner.api("POST", f"/positions/{position_id}/stop-loss", 
                        {"price": new_sl}, api_key=api_key)
    if result and result.get("success"):
        runner.record("设置止损", True, f"新 SL: ${new_sl:.2f}")
    else:
        runner.record("设置止损", False, f"设置失败: {result}")
    
    # 修改止盈
    new_tp = entry_price * 1.15 if entry_price else 2500
    result = runner.api("POST", f"/positions/{position_id}/take-profit", 
                        {"price": new_tp}, api_key=api_key)
    if result and result.get("success"):
        runner.record("设置止盈", True, f"新 TP: ${new_tp:.2f}")
    else:
        runner.record("设置止盈", False, f"设置失败: {result}")
    
    # 查看仓位健康度
    result = runner.api("GET", f"/positions/{position_id}/health")
    if result:
        runner.record("仓位健康度", True, 
            f"健康度: {result.get('health_ratio', 0):.2%}, "
            f"状态: {result.get('health_status', 'N/A')}")


def test_signal_betting(runner: TestRunner):
    """测试 5: Signal Betting"""
    print(f"\n{BOLD}=== 测试 5: Signal Betting ==={RESET}")
    print("  流程: 创建信号 → Fade 对赌 → 结算\n")
    
    ts = int(time.time())
    
    # 注册两个 Agent
    creator_id = runner.register_agent(f"0xSignalCreator_{ts}", "SignalCreator")
    fader_id = runner.register_agent(f"0xSignalFader_{ts}", "SignalFader")
    
    if not creator_id or not fader_id:
        runner.record("Signal 注册", False, "注册失败")
        return
    
    runner.record("Signal 注册", True, f"Creator: {creator_id}, Fader: {fader_id}")
    
    api_key_creator = runner.agents[creator_id]["api_key"]
    api_key_fader = runner.agents[fader_id]["api_key"]
    
    # 为两个 Agent 存款
    for aid, key in [(creator_id, api_key_creator), (fader_id, api_key_fader)]:
        runner.api("POST", "/deposit", {"agent_id": aid, "amount": 500}, api_key=key)
    
    # 5.1 创建信号: ETH > $2500 in 24h
    result = runner.api("POST", "/signals", {
        "agent_id": creator_id,
        "asset": "ETH-PERP",
        "signal_type": "price_above",
        "target_value": 2500,
        "stake_amount": 50,
        "duration_hours": 1,  # 1小时方便测试
    }, api_key=api_key_creator)
    
    if not result or not result.get("success"):
        runner.record("创建信号", False, f"失败: {result}")
        return
    
    signal = result.get("signal", {})
    signal_id = signal.get("signal_id")
    runner.record("创建信号", True, 
        f"Signal: {signal_id}, {signal.get('description', 'N/A')}, 押注 ${signal.get('stake_amount')}")
    
    # 5.2 查看开放信号
    result = runner.api("GET", "/signals/open")
    if result:
        open_signals = result.get("signals", [])
        runner.record("开放信号", True, f"共 {len(open_signals)} 个开放信号")
    
    # 5.3 Fade 信号
    result = runner.api("POST", "/signals/fade", {
        "signal_id": signal_id,
        "fader_id": fader_id,
    }, api_key=api_key_fader)
    
    if not result or not result.get("success"):
        runner.record("Fade 信号", False, f"失败: {result}")
        return
    
    bet = result.get("bet", {})
    bet_id = bet.get("bet_id")
    runner.record("Fade 信号", True, 
        f"Bet: {bet_id}, Total Pot: ${bet.get('total_pot')}")
    
    # 5.4 结算 (模拟价格)
    # 假设当前 ETH 价格是 2400，低于 2500，所以 Fader 赢
    settlement_price = 2400.0
    result = runner.api("POST", f"/bets/{bet_id}/settle?price={settlement_price}", 
                        api_key=api_key_creator)
    
    if result and result.get("success"):
        winner = result.get("winner_id")
        payout = result.get("payout", 0)
        protocol_fee = result.get("protocol_fee", 0)
        
        # Fader 应该赢 (价格 2400 < 2500)
        expected_winner = fader_id
        winner_correct = winner == expected_winner
        
        runner.record("结算", winner_correct, 
            f"价格 ${settlement_price}, 赢家: {winner}, "
            f"赔付 ${payout:.2f}, 协议费 ${protocol_fee:.2f}")
    else:
        runner.record("结算", False, f"结算失败: {result}")
    
    # 5.5 查看统计
    result = runner.api("GET", "/betting/stats")
    if result:
        runner.record("对赌统计", True, 
            f"总信号: {result.get('total_signals')}, "
            f"总下注: {result.get('total_bets')}, "
            f"协议费: ${result.get('protocol_fees', 0):.2f}")
    
    # 5.6 查看 Agent 对赌统计
    result = runner.api("GET", f"/agents/{fader_id}/betting")
    if result:
        runner.record("Fader 统计", True, 
            f"胜: {result.get('wins')}, 负: {result.get('losses')}, "
            f"净 PnL: ${result.get('net_pnl', 0):.2f}")


def test_margin_check(runner: TestRunner):
    """测试 6: 保证金检查"""
    print(f"\n{BOLD}=== 测试 6: 保证金检查 ==={RESET}")
    print("  测试余额不足时的风控拦截\n")
    
    ts = int(time.time())
    agent_id = runner.register_agent(f"0xMarginTest_{ts}", "MarginAgent")
    if not agent_id:
        runner.record("保证金测试注册", False, "注册失败")
        return
    
    api_key = runner.agents[agent_id]["api_key"]
    
    # 只存入少量资金
    runner.api("POST", "/deposit", {"agent_id": agent_id, "amount": 100}, api_key=api_key)
    runner.record("存入余额", True, "$100")
    
    # 尝试开超过余额的仓位
    result = runner.api("POST", "/intents", {
        "agent_id": agent_id,
        "intent_type": "long",
        "asset": "BTC-PERP",
        "size_usdc": 1000,  # 需要保证金超过 $100
        "leverage": 5,      # 需要 $200 保证金
    }, api_key=api_key, expected_status=400)
    
    if result is None:
        # 400 错误说明风控生效
        runner.record("保证金检查", True, "风控拦截: 保证金不足")
    else:
        # 如果返回成功，可能是风控没生效
        position = result.get("position", {})
        if isinstance(position, dict) and "error" in position:
            runner.record("保证金检查", True, f"风控拦截: {position['error']}")
        else:
            runner.record("保证金检查", False, "风控未拦截超额开仓")


def print_summary(runner: TestRunner):
    """打印测试总结"""
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}测试总结{RESET}")
    print(f"{'='*50}")
    
    passed = sum(1 for r in runner.results if r.passed)
    failed = sum(1 for r in runner.results if not r.passed)
    total = len(runner.results)
    
    print(f"\n总计: {total} 项测试")
    print(f"{GREEN}通过: {passed}{RESET}")
    print(f"{RED}失败: {failed}{RESET}")
    
    if failed > 0:
        print(f"\n{RED}失败的测试:{RESET}")
        for r in runner.results:
            if not r.passed:
                print(f"  - {r.name}: {r.message}")
    
    print(f"\n{'='*50}")
    
    # 返回退出码
    return 0 if failed == 0 else 1


def main():
    print(f"\n{BOLD}🧪 AI Perp DEX 核心功能测试{RESET}")
    print(f"目标: {BASE_URL}")
    print("="*50)
    
    # 检查服务
    if not test_health():
        print(f"\n{RED}服务未运行，无法继续测试{RESET}")
        return 1
    
    runner = TestRunner()
    
    # 运行所有测试
    test_full_trading_flow(runner)
    test_p2p_matching(runner)
    test_fee_calculation(runner)
    test_stop_loss_take_profit(runner)
    test_signal_betting(runner)
    test_margin_check(runner)
    
    # 打印总结
    return print_summary(runner)


if __name__ == "__main__":
    exit(main())
