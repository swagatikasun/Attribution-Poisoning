from apoison import Ledger, cluster, MultiInput, DepositAddress


def build_framing_ledger():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("victim", "victim_deposit", 1.0, block=100)
    led.add_transfer("victim_deposit", "EX", 1.0, block=101)
    led.add_transfer("theft", "victim_deposit", 1.0, block=205)
    return led


def test_framing_merges_victim_and_theft():
    res = cluster(build_framing_ledger())
    assert res.same_entity("victim", "theft")


def test_framing_rests_on_inducible_evidence():
    res = cluster(build_framing_ledger())
    assert res.inducible_dependent("victim", "theft")
    assert not res.base.connected("victim", "theft")


def test_defense_separates_framed_pair():
    led = build_framing_ledger()
    res = cluster(led)
    assert res.base.find("victim") != res.base.find("theft")


def test_pollution_counts_inducible_entities():
    res = cluster(build_framing_ledger())
    stats = res.pollution()
    assert stats["entities_resting_on_inducible"] >= 1
    assert stats["links_inducible"] >= 1


def test_self_only_clustering_is_not_poisonable():
    led = build_framing_ledger()
    res = cluster(led, heuristics=[MultiInput()])
    assert res.poisonable_heuristics() == []
    assert not res.same_entity("victim", "theft")


def test_deposit_only_reproduces_attack():
    led = build_framing_ledger()
    res = cluster(led, heuristics=[DepositAddress()])
    assert res.same_entity("victim", "theft")
    assert res.inducible_dependent("victim", "theft")
