"""
🛡️ AI Perp DEX - 风控安全测试

测试项目:
1. 负数入金
2. 超额杠杆 (200x)
3. 无效资产
4. 自己给自己转账
5. 超额转账
6. 风险评分和限额
"""

import sys
sys.path.insert(0, '/Users/vvedition/clawd/ai-perp-dex/trading-hub')

from services.settlement import SettlementEngine, AgentBalance
from services.risk_limits import RiskManager, AgentRiskLimits
from services.position_manager import PositionManager, Position
from api.models import TradingIntent, IntentType, IntentStatus

class SecurityTester:
    def __init__(self):
        self.results = []
        self.settlement = SettlementEngine(simulation_mode=True)
        self.risk_manager = RiskManager()
        self.position_manager = PositionManager()
        
    def test(self, name: str, should_pass: bool, test_func):
        """执行测试"""
        print(f"\n{'='*60}")
        print(f"🧪 测试: {name}")
        print(f"   预期: {'✅ 应该拦截' if not should_pass else '✅ 应该通过'}")
        
        try:
            result = test_func()
            passed = True
            error = None
        except (ValueError, Exception) as e:
            passed = False
            error = str(e)
            result = None
        
        # 判断是否符合预期
        if should_pass:
            success = passed
        else:
            success = not passed
            
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   结果: {status}")
        if error:
            print(f"   错误: {error}")
        if result:
            print(f"   返回: {result}")
            
        self.results.append({
            "name": name,
            "expected_pass": should_pass,
            "actual_pass": passed,
            "success": success,
            "error": error,
        })
        return success

    def run_all_tests(self):
        print("\n" + "🔒"*30)
        print("       AI PERP DEX 安全测试报告")
        print("🔒"*30)
        
        # === 测试 1: 负数入金 ===
        def test_negative_deposit():
            self.settlement.deposit("test_agent", -1000)
            return self.settlement.get_balance("test_agent").balance_usdc
            
        self.test(
            "1. 负数入金 (-$1000)",
            should_pass=False,  # 应该被拦截
            test_func=test_negative_deposit
        )
        
        # === 测试 2: 超额杠杆 (200x) ===
        def test_excess_leverage():
            allowed, violations = self.risk_manager.check_trade(
                agent_id="test_agent",
                size=100,
                leverage=200,  # 超过 50x 限制
            )
            if not allowed:
                raise ValueError(f"杠杆超限: {[v.message for v in violations]}")
            return "交易允许"
            
        self.test(
            "2. 超额杠杆 (200x, 限制 50x)",
            should_pass=False,
            test_func=test_excess_leverage
        )
        
        # === 测试 3: 无效资产 ===
        def test_invalid_asset():
            # 检查 position_manager 是否验证资产
            position = self.position_manager.open_position(
                agent_id="test_agent",
                asset="INVALID-PERP",  # 无效资产
                side="long",
                size_usdc=100,
                entry_price=1.0,
                leverage=1,
            )
            return position.asset
        
        self.test(
            "3. 无效资产 (INVALID-PERP)",
            should_pass=False,  # 应该被拦截
            test_func=test_invalid_asset
        )
        
        # === 测试 4: 自己给自己转账 ===
        def test_self_transfer():
            # 首先入金
            self.settlement.deposit("self_test_agent", 1000)
            
            # 尝试自己给自己转账
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.settlement.settle_internal(
                    from_agent="self_test_agent",
                    to_agent="self_test_agent",  # 同一个 agent
                    amount=100,
                )
            )
            loop.close()
            return f"转账成功: {result.settlement_id}"
        
        self.test(
            "4. 自己给自己转账",
            should_pass=False,  # 应该被拦截
            test_func=test_self_transfer
        )
        
        # === 测试 4b: Intent 自匹配检查 ===
        def test_intent_self_match():
            intent_a = TradingIntent(
                agent_id="same_agent",
                intent_type=IntentType.LONG,
                asset="BTC-PERP",
            )
            intent_b = TradingIntent(
                agent_id="same_agent",  # 同一个 agent
                intent_type=IntentType.SHORT,
                asset="BTC-PERP",
            )
            
            if intent_a.is_compatible_with(intent_b):
                raise ValueError("Intent 允许自匹配!")
            return "自匹配被正确拦截"
            
        self.test(
            "4b. Intent 自匹配",
            should_pass=True,  # 这个测试本身应该通过 (因为系统会拦截)
            test_func=test_intent_self_match
        )
        
        # === 测试 5: 超额转账 ===
        def test_over_transfer():
            # 新账户只有 $1000
            self.settlement.get_balance("poor_agent")  # 创建账户
            
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.settlement.settle_internal(
                    from_agent="poor_agent",
                    to_agent="rich_agent",
                    amount=5000,  # 超过余额
                )
            )
            loop.close()
            return f"转账成功: {result.amount_usdc}"
            
        self.test(
            "5. 超额转账 ($5000, 余额 $1000)",
            should_pass=False,
            test_func=test_over_transfer
        )
        
        # === 测试 6: 风险评分和限额 ===
        def test_risk_score():
            limits = self.risk_manager.get_limits("test_agent")
            score = self.risk_manager.get_risk_score("test_agent")
            return {
                "limits": limits.to_dict(),
                "score": score,
            }
            
        self.test(
            "6. 风险评分和限额查询",
            should_pass=True,
            test_func=test_risk_score
        )
        
        # === 测试 7: 超大仓位 ===
        def test_huge_position():
            allowed, violations = self.risk_manager.check_trade(
                agent_id="test_agent",
                size=100000,  # $100k, 超过 $10k 限制
                leverage=10,
            )
            if not allowed:
                raise ValueError(f"仓位超限: {[v.message for v in violations]}")
            return "交易允许"
            
        self.test(
            "7. 超大仓位 ($100k, 限制 $10k)",
            should_pass=False,
            test_func=test_huge_position
        )
        
        # === 测试 8: Position Manager 杠杆验证 ===
        def test_pm_leverage():
            position = self.position_manager.open_position(
                agent_id="test_agent",
                asset="BTC-PERP",
                side="long",
                size_usdc=100,
                entry_price=50000,
                leverage=150,  # 超过 100x 限制
            )
            return f"开仓成功: {position.position_id}"
            
        self.test(
            "8. Position Manager 杠杆验证 (150x, 限制 100x)",
            should_pass=False,
            test_func=test_pm_leverage
        )
        
        # === 测试 9: Position Manager 仓位大小验证 ===
        def test_pm_size():
            position = self.position_manager.open_position(
                agent_id="test_agent",
                asset="BTC-PERP",
                side="long",
                size_usdc=50000,  # 超过 $10k 限制
                entry_price=50000,
                leverage=1,
            )
            return f"开仓成功: {position.position_id}"
            
        self.test(
            "9. Position Manager 仓位大小验证 ($50k, 限制 $10k)",
            should_pass=False,
            test_func=test_pm_size
        )
        
        # === 测试 10: 零金额交易 ===
        def test_zero_amount():
            allowed, violations = self.risk_manager.check_trade(
                agent_id="test_agent",
                size=0,
                leverage=10,
            )
            if violations:
                raise ValueError(f"零金额被拦截: {[v.message for v in violations]}")
            return "零金额交易允许通过"
            
        self.test(
            "10. 零金额交易",
            should_pass=False,  # 零金额应该被拦截
            test_func=test_zero_amount
        )
        
        # === 生成报告 ===
        self.generate_report()
        
    def generate_report(self):
        print("\n\n" + "="*60)
        print("📊 安全测试报告汇总")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"\n总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {total - passed}")
        print(f"通过率: {passed/total*100:.0f}%")
        
        # 漏洞列表
        vulnerabilities = [r for r in self.results if not r["success"]]
        if vulnerabilities:
            print(f"\n⚠️ 发现 {len(vulnerabilities)} 个潜在漏洞:")
            for v in vulnerabilities:
                print(f"   - {v['name']}")
                if not v['expected_pass'] and v['actual_pass']:
                    print(f"     ❌ 应该被拦截但没有!")
        
        # 风控评分
        security_score = (passed / total) * 10
        print(f"\n🛡️ 风控系统评分: {security_score:.1f}/10")
        
        if security_score >= 8:
            print("   评级: 优秀 ✅")
        elif security_score >= 6:
            print("   评级: 良好 ⚠️")
        else:
            print("   评级: 需要改进 ❌")
        
        # 改进建议
        print("\n📝 改进建议:")
        suggestions = []
        
        for r in self.results:
            if not r["success"]:
                if "负数入金" in r["name"]:
                    suggestions.append("1. 在 deposit() 函数添加金额 > 0 验证")
                if "无效资产" in r["name"]:
                    suggestions.append("2. 添加支持资产白名单验证")
                if "自己给自己转账" in r["name"]:
                    suggestions.append("3. 在 settle_internal() 添加 from != to 验证")
                if "零金额" in r["name"]:
                    suggestions.append("4. 在 check_trade() 添加 size > 0 验证")
        
        if not suggestions:
            suggestions.append("✅ 当前风控措施较为完善")
        
        for s in suggestions:
            print(f"   {s}")


if __name__ == "__main__":
    tester = SecurityTester()
    tester.run_all_tests()
