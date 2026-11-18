from apoison import (
    Ledger,
    synthetic,
    frame,
    ConsentAwareClustering,
    evaluate,
    MultiInput,
)


def victim_with_deposit():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("victim", "victim_deposit", 1.0, block=100)
    led.add_transfer("victim_deposit", "EX", 1.0, block=101)
    return led


def test_defense_blocks_single_tx_framing():
    led = victim_with_deposit()
    plan = frame(led, "theft", "victim")
    attacked = plan.apply(led)
    weak = ConsentAwareClustering(threshold=1).run(attacked)
    strong = ConsentAwareClustering(threshold=2).run(attacked)
    assert weak.connected("theft", "victim")
    assert not strong.connected("theft", "victim")


def test_certified_cost_is_threshold_without_shared_support():
    led = victim_with_deposit()
    res = ConsentAwareClustering(threshold=3).run(led)
    assert res.certified_cost("victim", "outsider", 3) == 3


def test_defense_never_splits_joint_signed_cluster():
    led = Ledger()
    led.add_multi_input(["a1", "a2"], ["ao"], block=1)
    for k in (1, 2, 3):
        res = ConsentAwareClustering(threshold=k).run(led)
        assert res.connected("a1", "a2")


def test_threshold_trades_recall_for_resistance():
    led, meta = synthetic(n_users=120, weak_user_frac=0.3, framings=20, seed=5)
    curve = evaluate(led, meta, thresholds=[1, 2, 3])
    by_k = {row["threshold"]: row for row in curve}
    assert by_k[1]["block_rate"] < by_k[2]["block_rate"]
    assert by_k[2]["block_rate"] == 1.0
    assert by_k[1]["recall"] >= by_k[2]["recall"]
    assert by_k[2]["recall"] < 1.0


def test_certified_cost_matches_attack_outcome():
    led, meta = synthetic(n_users=60, framings=10, seed=6)
    attacker, u = meta["framings"][0]
    victim_addr = meta["truth"][u][0]
    res = ConsentAwareClustering(threshold=2).run(led)
    assert res.certified_cost(attacker, victim_addr, 2) == 1
    assert not res.connected(attacker, victim_addr)


def _batch_deposit_scenario(k):
    led = Ledger()
    led.exchanges.add("EX")
    b = 0
    for i in range(k):
        d = f"victim_dep{i}"
        led.add_transfer("victim", d, 1.0, b); b += 1
        led.add_transfer(d, "EX", 1.0, b); b += 1
        led.add_transfer("attacker", d, 0.0001, b); b += 1
    return led


def test_batched_supports_defeat_naive_threshold():
    led = _batch_deposit_scenario(3)
    naive = ConsentAwareClustering(threshold=3, independent=False).run(led)
    assert naive.connected("victim", "attacker")


def test_independence_blocks_batched_supports():
    led = _batch_deposit_scenario(3)
    indep = ConsentAwareClustering(threshold=2, independent=True).run(led)
    assert not indep.connected("victim", "attacker")
