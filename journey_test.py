#!/usr/bin/env python3
import sys
import asyncio
import uuid
import time

# Required path injection
sys.path.insert(0, 'trading-hub')

from services.settlement import settlement_engine
from services.position_manager import position_manager
from services.fee_service import fee_service, FeeType
from services.signal_betting import signal_betting, SignalType


# Dependency injection (required)
position_manager.set_settlement_engine(settlement_engine)
fee_service.set_position_manager(position_manager)


RUN_ID = uuid.uuid4().hex[:8]
AGENT_A = f"agent_alice_{RUN_ID}"
AGENT_B = f"agent_bob_{RUN_ID}"
TREASURY = "protocol_treasury"

# Shared state
state = {
    "baseline_total": None,
    "external_in": 0.0,
    "external_out": 0.0,
    "btc_position_id": None,
    "btc_entry": None,
    "eth_position_id": None,
    "eth_entry": None,
    "tx_sig_valid": None,
    "tx_amount_valid": None,
}


def get_balance(agent_id: str) -> float:
    return settlement_engine.get_balance(agent_id).available


def assert_true(cond: bool, msg: str = "assertion failed"):
    if not cond:
        raise AssertionError(msg)


def assert_close(a: float, b: float, tol: float = 1e-6, msg: str = "values not close"):
    if abs(a - b) > tol:
        raise AssertionError(f"{msg}: {a} vs {b}")


def normalize_result(res):
    if res is None:
        return True, None
    if isinstance(res, tuple) and len(res) == 2:
        return bool(res[0]), res[1]
    if isinstance(res, bool):
        return res, None
    return True, None


def mk_tx_sig(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def mk_wallet(prefix: str) -> str:
    # Ensure > 20 chars for valid wallet
    return f"{prefix}_wallet_{uuid.uuid4().hex}"


async def run_test(name, func, results):
    try:
        res = func()
        if asyncio.iscoroutine(res):
            res = await res
        ok, detail = normalize_result(res)
        if ok:
            print(f"PASS - {name}")
            results.append(True)
        else:
            print(f"FAIL - {name}: {detail or 'returned False'}")
            results.append(False)
    except Exception as e:
        print(f"FAIL - {name}: {e}")
        results.append(False)


# === Tests ===

def test_register_deposit():
    amount_a = 10000.0
    amount_b = 5000.0
    before_a = get_balance(AGENT_A)
    before_b = get_balance(AGENT_B)
    bal_a = settlement_engine.deposit(AGENT_A, amount_a)
    bal_b = settlement_engine.deposit(AGENT_B, amount_b)
    assert_close(bal_a.available - before_a, amount_a, msg="agent A deposit mismatch")
    assert_close(bal_b.available - before_b, amount_b, msg="agent B deposit mismatch")

    # baseline total after registration
    state["baseline_total"] = get_balance(AGENT_A) + get_balance(AGENT_B) + get_balance(TREASURY)


def test_check_balance():
    bal = settlement_engine.get_balance(AGENT_A)
    assert_true(bal.available > 0, "balance should be positive")


async def test_deposit_with_tx_verification_valid():
    tx_sig = mk_tx_sig("tx_valid")
    amount = 250.0
    before = get_balance(AGENT_A)
    res = await settlement_engine.deposit_with_tx_verification(
        AGENT_A, amount, tx_sig, from_wallet=mk_wallet("from")
    )
    assert_true(res.get("success") is True, f"deposit failed: {res}")
    after = get_balance(AGENT_A)
    assert_close(after - before, amount, msg="onchain deposit delta mismatch")
    state["external_in"] += amount
    state["tx_sig_valid"] = tx_sig
    state["tx_amount_valid"] = amount


async def test_deposit_with_tx_verification_double_spend():
    tx_sig = state["tx_sig_valid"]
    amount = state["tx_amount_valid"]
    res = await settlement_engine.deposit_with_tx_verification(
        AGENT_A, amount, tx_sig, from_wallet=mk_wallet("from")
    )
    assert_true(res.get("success") is False, "double spend should fail")
    err = (res.get("error") or "").lower()
    assert_true("duplicate" in err or "processed" in err, f"unexpected error: {res}")


async def test_deposit_with_tx_verification_invalid_signature():
    res = await settlement_engine.deposit_with_tx_verification(
        AGENT_A, 100.0, "bad", from_wallet=mk_wallet("from")
    )
    assert_true(res.get("success") is False, "invalid signature should fail")
    err = (res.get("error") or "").lower()
    assert_true("invalid" in err or "format" in err, f"unexpected error: {res}")


async def test_deposit_with_tx_verification_invalid_amount_zero():
    res = await settlement_engine.deposit_with_tx_verification(
        AGENT_A, 0.0, mk_tx_sig("tx_zero"), from_wallet=mk_wallet("from")
    )
    assert_true(res.get("success") is False, "zero amount should fail")
    err = (res.get("error") or "").lower()
    assert_true("positive" in err or "amount" in err, f"unexpected error: {res}")


async def test_deposit_with_tx_verification_invalid_amount_negative():
    res = await settlement_engine.deposit_with_tx_verification(
        AGENT_A, -5.0, mk_tx_sig("tx_neg"), from_wallet=mk_wallet("from")
    )
    assert_true(res.get("success") is False, "negative amount should fail")
    err = (res.get("error") or "").lower()
    assert_true("positive" in err or "amount" in err, f"unexpected error: {res}")


def test_open_btc_long_5x():
    pos = position_manager.open_position(
        AGENT_A, "BTC-PERP", "long", size_usdc=1000.0, entry_price=50000.0, leverage=5
    )
    assert_true(pos.leverage == 5, "leverage mismatch")
    assert_true(pos.side.value == "long", "side mismatch")
    state["btc_position_id"] = pos.position_id
    state["btc_entry"] = pos.entry_price


def test_update_pnl():
    pos = position_manager.positions[state["btc_position_id"]]
    pos.update_pnl(state["btc_entry"] * 1.02)
    assert_true(pos.unrealized_pnl != 0.0, "PnL should update")


def test_set_stop_loss_take_profit():
    pid = state["btc_position_id"]
    sl = state["btc_entry"] * 0.95
    tp = state["btc_entry"] * 1.05
    position_manager.set_stop_loss(pid, sl)
    position_manager.set_take_profit(pid, tp)
    pos = position_manager.positions[pid]
    assert_close(pos.stop_loss, sl, msg="stop loss not set")
    assert_close(pos.take_profit, tp, msg="take profit not set")


def test_close_btc_position():
    pid = state["btc_position_id"]
    entry = state["btc_entry"]
    pos = position_manager.close_position_manual(pid, close_price=entry)
    assert_true(pos.is_open is False, "position should be closed")
    assert_close(pos.realized_pnl or 0.0, 0.0, msg="realized pnl should be zero")


def test_open_eth_short():
    pos = position_manager.open_position(
        AGENT_A, "ETH-PERP", "short", size_usdc=500.0, entry_price=3000.0, leverage=3
    )
    assert_true(pos.side.value == "short", "side mismatch")
    state["eth_position_id"] = pos.position_id
    state["eth_entry"] = pos.entry_price


def test_collect_fee_and_treasury_increase():
    treasury_before = get_balance(TREASURY)
    agent_before = get_balance(AGENT_A)
    size = 1000.0
    record = fee_service.collect_fee(AGENT_A, size, FeeType.TAKER)
    expected_fee = size * fee_service.config.taker_rate
    treasury_after = get_balance(TREASURY)
    agent_after = get_balance(AGENT_A)
    assert_close(record.amount_usdc, expected_fee, msg="fee amount mismatch")
    assert_close(treasury_after - treasury_before, expected_fee, msg="treasury did not increase")
    assert_close(agent_before - agent_after, expected_fee, msg="agent balance did not decrease by fee")


def test_close_eth_position():
    pid = state["eth_position_id"]
    entry = state["eth_entry"]
    pos = position_manager.close_position_manual(pid, close_price=entry)
    assert_true(pos.is_open is False, "ETH position should be closed")
    assert_close(pos.realized_pnl or 0.0, 0.0, msg="ETH realized pnl should be zero")


async def test_signal_betting_flow():
    stake = 50.0
    target = 60000.0

    creator_before = get_balance(AGENT_A)
    signal = signal_betting.create_signal(
        creator_id=AGENT_A,
        asset="BTC-PERP",
        signal_type=SignalType.PRICE_ABOVE,
        target_value=target,
        stake_amount=stake,
        duration_hours=1,
        current_price=55000.0,
    )
    creator_after = get_balance(AGENT_A)
    assert_close(creator_before - creator_after, stake, msg="creator stake not deducted")

    fader_before = get_balance(AGENT_B)
    bet = signal_betting.fade_signal(signal.signal_id, AGENT_B)
    fader_after = get_balance(AGENT_B)
    assert_close(fader_before - fader_after, stake, msg="fader stake not deducted")

    treasury_before = get_balance(TREASURY)
    winner_before = get_balance(AGENT_A)
    bet = await signal_betting.settle_bet(bet.bet_id, settlement_price=target + 1000.0)

    expected_fee = bet.total_pot * signal_betting.PROTOCOL_FEE_RATE
    expected_payout = bet.total_pot - expected_fee

    assert_true(bet.winner_id == AGENT_A, "creator should win in this setup")
    winner_after = get_balance(AGENT_A)
    treasury_after = get_balance(TREASURY)

    assert_close(winner_after - winner_before, expected_payout, msg="winner payout mismatch")
    assert_close(treasury_after - treasury_before, expected_fee, msg="protocol fee mismatch")


async def test_withdraw_onchain_success():
    amount = 100.0
    wallet = mk_wallet("valid")
    before = get_balance(AGENT_A)
    res = await settlement_engine.withdraw_onchain(AGENT_A, amount, wallet)
    assert_true(res.get("success") is True, f"withdraw should succeed: {res}")
    after = get_balance(AGENT_A)
    assert_close(before - after, amount, msg="withdraw did not reduce balance")
    state["external_out"] += amount


async def test_withdraw_onchain_cooldown():
    amount = 10.0
    wallet = mk_wallet("valid")
    res = await settlement_engine.withdraw_onchain(AGENT_A, amount, wallet)
    assert_true(res.get("success") is False, "cooldown withdraw should fail")
    err = (res.get("error") or "").lower()
    assert_true("cooldown" in err, f"unexpected error: {res}")


async def test_withdraw_onchain_excess():
    wallet = mk_wallet("valid")
    res = await settlement_engine.withdraw_onchain(AGENT_A, 1e9, wallet)
    assert_true(res.get("success") is False, "excess withdraw should fail")
    err = (res.get("error") or "").lower()
    assert_true("insufficient" in err, f"unexpected error: {res}")


async def test_withdraw_onchain_invalid_wallet():
    res = await settlement_engine.withdraw_onchain(AGENT_B, 10.0, "bad")
    assert_true(res.get("success") is False, "invalid wallet should fail")
    err = (res.get("error") or "").lower()
    assert_true("invalid wallet" in err, f"unexpected error: {res}")


def test_funds_conservation():
    # Ensure no open positions for our agents
    open_a = position_manager.get_positions(AGENT_A, only_open=True)
    open_b = position_manager.get_positions(AGENT_B, only_open=True)
    assert_true(len(open_a) == 0, "agent A has open positions")
    assert_true(len(open_b) == 0, "agent B has open positions")

    final_total = get_balance(AGENT_A) + get_balance(AGENT_B) + get_balance(TREASURY)
    expected = state["baseline_total"] + state["external_in"] - state["external_out"]
    assert_close(final_total, expected, tol=1e-4, msg="funds not conserved")


def test_all_12_pairs(pair_asset):
    # Open and close immediately to validate support
    pos = position_manager.open_position(
        AGENT_A, pair_asset, "long", size_usdc=100.0, entry_price=100.0, leverage=2
    )
    pos = position_manager.close_position_manual(pos.position_id, close_price=100.0)
    assert_true(pos.is_open is False, f"position not closed for {pair_asset}")


def test_boundary_zero_amount():
    try:
        position_manager.open_position(
            AGENT_A, "BTC-PERP", "long", size_usdc=0.0, entry_price=50000.0, leverage=1
        )
        raise AssertionError("zero amount should fail")
    except ValueError:
        return


def test_boundary_negative_amount():
    try:
        position_manager.open_position(
            AGENT_A, "BTC-PERP", "long", size_usdc=-10.0, entry_price=50000.0, leverage=1
        )
        raise AssertionError("negative amount should fail")
    except ValueError:
        return


def test_boundary_huge_amount():
    try:
        position_manager.open_position(
            AGENT_A, "BTC-PERP", "long", size_usdc=1_000_000.0, entry_price=50000.0, leverage=1
        )
        raise AssertionError("huge amount should fail")
    except ValueError:
        return


def test_boundary_max_leverage_20x():
    pos = position_manager.open_position(
        AGENT_A, "BTC-PERP", "long", size_usdc=100.0, entry_price=50000.0, leverage=20
    )
    pos = position_manager.close_position_manual(pos.position_id, close_price=50000.0)
    assert_true(pos.is_open is False, "20x position should close")


def test_boundary_over_leverage_21x():
    try:
        position_manager.open_position(
            AGENT_A, "BTC-PERP", "long", size_usdc=100.0, entry_price=50000.0, leverage=21
        )
        raise AssertionError("21x should fail")
    except ValueError:
        return


async def main():
    results = []

    # 1. Register + deposit
    await run_test("1. Register (deposit)", test_register_deposit, results)

    # 2. Check balance
    await run_test("2. Check balance", test_check_balance, results)

    # 3. On-chain deposit verification
    await run_test("3.1 deposit_with_tx_verification valid", test_deposit_with_tx_verification_valid, results)
    await run_test("3.2 deposit_with_tx_verification double spend", test_deposit_with_tx_verification_double_spend, results)
    await run_test("3.3 deposit_with_tx_verification invalid signature", test_deposit_with_tx_verification_invalid_signature, results)
    await run_test("3.4 deposit_with_tx_verification invalid amount (zero)", test_deposit_with_tx_verification_invalid_amount_zero, results)
    await run_test("3.5 deposit_with_tx_verification invalid amount (negative)", test_deposit_with_tx_verification_invalid_amount_negative, results)

    # 4. Open BTC long 5x
    await run_test("4. Open BTC long 5x", test_open_btc_long_5x, results)

    # 5. Update PnL
    await run_test("5. Update PnL", test_update_pnl, results)

    # 6. Set SL/TP
    await run_test("6. Set stop loss / take profit", test_set_stop_loss_take_profit, results)

    # 7. Close position
    await run_test("7. Close BTC position", test_close_btc_position, results)

    # 8. Open ETH short
    await run_test("8. Open ETH short", test_open_eth_short, results)

    # 9. Collect fee + treasury increase
    await run_test("9. Collect fee + treasury balance", test_collect_fee_and_treasury_increase, results)

    # Close ETH position (cleanup before conservation)
    await run_test("9.1 Close ETH position", test_close_eth_position, results)

    # 10. Signal betting flow
    await run_test("10. Signal betting create/fade/settle", test_signal_betting_flow, results)

    # 11. Withdraw on-chain tests
    await run_test("11.1 Withdraw onchain success", test_withdraw_onchain_success, results)
    await run_test("11.2 Withdraw onchain cooldown", test_withdraw_onchain_cooldown, results)
    await run_test("11.3 Withdraw onchain excess", test_withdraw_onchain_excess, results)
    await run_test("11.4 Withdraw onchain invalid wallet", test_withdraw_onchain_invalid_wallet, results)

    # 12. Funds conservation
    await run_test("12. Funds conservation", test_funds_conservation, results)

    # 13. Test all 12 trading pairs
    pairs = [
        "BTC-PERP", "ETH-PERP", "SOL-PERP", "DOGE-PERP", "PEPE-PERP", "WIF-PERP",
        "ARB-PERP", "OP-PERP", "SUI-PERP", "AVAX-PERP", "LINK-PERP", "AAVE-PERP",
    ]
    for pair in pairs:
        await run_test(f"13. Pair {pair}", lambda p=pair: test_all_12_pairs(p), results)

    # 14. Boundary tests
    await run_test("14.1 Boundary zero amount", test_boundary_zero_amount, results)
    await run_test("14.2 Boundary negative amount", test_boundary_negative_amount, results)
    await run_test("14.3 Boundary huge amount", test_boundary_huge_amount, results)
    await run_test("14.4 Boundary max leverage 20x", test_boundary_max_leverage_20x, results)
    await run_test("14.5 Boundary over leverage 21x", test_boundary_over_leverage_21x, results)

    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed
    print("\n=== TEST SUMMARY ===")
    print(f"Total: {total}, Passed: {passed}, Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
