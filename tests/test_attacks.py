from apoison import (
    Ledger,
    cluster,
    frame,
    collapse,
    sybil_frame,
    forces_merge,
    merge_amplification,
    MultiInput,
)


def victim_with_deposit():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("victim", "victim_deposit", 1.0, block=100)
    led.add_transfer("victim_deposit", "EX", 1.0, block=101)
    return led


def test_frame_via_deposit_costs_one_tx():
    led = victim_with_deposit()
    plan = frame(led, "theft", "victim")
    assert plan is not None
    assert plan.heuristic == "deposit_address"
    assert plan.transactions() == 1
    assert forces_merge(plan, led, "theft", "victim")


def test_frame_does_not_mutate_original():
    led = victim_with_deposit()
    before = len(led.transfers)
    plan = frame(led, "theft", "victim")
    plan.apply(led)
    assert len(led.transfers) == before


def test_frame_via_common_counterparty():
    led = Ledger()
    led.add_transfer("victim", "shop", 1.0, block=10)
    plan = frame(led, "theft", "victim")
    assert plan is not None
    assert plan.heuristic == "common_counterparty"
    assert plan.transactions() == 1
    assert forces_merge(plan, led, "theft", "victim")


def test_frame_via_first_funder_when_unfunded():
    led = Ledger()
    led.add_deployment("victim", "ctr", block=1)
    plan = frame(led, "theft", "victim")
    assert plan is not None
    assert plan.heuristic == "first_funder"


def _big_cluster(size):
    led = Ledger()
    for i in range(size):
        led.add_transfer(f"b{i}", "hub_service", 1.0, block=i)
    led.add_transfer("b0", "b_peer", 1.0, block=1000)
    return led


def test_collapse_cost_independent_of_cluster_size():
    small = _big_cluster(5)
    large = _big_cluster(60)
    p_small = collapse(small, "attacker", "b0")
    p_large = collapse(large, "attacker", "b0")
    assert p_small.transactions() == p_large.transactions() == 1
    assert forces_merge(p_small, small, "attacker", "b0")
    assert forces_merge(p_large, large, "attacker", "b0")


def test_collapse_redundancy_raises_cost():
    led = Ledger()
    led.add_transfer("b0", "p1", 1.0, block=1)
    led.add_transfer("b0", "p2", 1.0, block=2)
    plan = collapse(led, "attacker", "b0", redundancy=2)
    assert plan.transactions() == 2


def test_sybil_frame_links_all_targets():
    led = Ledger()
    targets = ["c1", "c2", "c3", "c4"]
    plan = sybil_frame(led, "attacker", targets)
    assert plan.transactions() == len(targets)
    res = cluster(plan.apply(led))
    assert res.same_entity("c1", "c4")
    assert res.inducible_dependent("c1", "c4")


def test_attacks_fail_against_self_only_vendor():
    led = victim_with_deposit()
    plan = frame(led, "theft", "victim")
    assert not forces_merge(plan, led, "theft", "victim", heuristics=[MultiInput()])


def test_gas_fee_scales_with_transactions_and_price():
    led = _big_cluster(5)
    plan = collapse(led, "attacker", "b0")
    assert plan.gas_fee(5) == plan.transactions() * 21000 * 5 * 1e-9
    assert plan.gas_fee(50) == 10 * plan.gas_fee(5)


def test_merge_amplification_exceeds_one_forged_transaction():
    led = _big_cluster(60)
    plan = collapse(led, "attacker", "b0")
    amp = merge_amplification(led, plan, "attacker")
    assert amp["forged_tx"] == 1
    assert amp["addresses_affected"] > 10
    assert amp["amplification"] == amp["addresses_affected"]
