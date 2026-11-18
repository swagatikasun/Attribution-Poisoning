from apoison import (
    Ledger,
    cluster,
    synthetic,
    report,
    fragile_merges,
    dataio,
    MultiInput,
    ChangeAddress,
    CommonCounterparty,
)


def test_single_inducible_bridge_is_fragile():
    led = Ledger()
    led.add_multi_input(["a1", "a2"], ["ao"], block=1)
    led.add_multi_input(["b1", "b2"], ["bo"], block=2)
    led.add_transfer("a1", "peer", 1.0, block=3)
    led.add_transfer("b1", "peer", 1.0, block=400)
    res = cluster(led, heuristics=[MultiInput(), ChangeAddress(), CommonCounterparty()])
    assert res.same_entity("a1", "b1")
    frag = fragile_merges(res)
    assert frag["fragile_bridges"] == 1
    assert frag["addresses_at_risk"] >= 2


def test_report_on_synthetic_has_inducible_pollution():
    led, meta = synthetic(n_users=100, seed=1)
    out = report(led, tainted=meta["tainted"])
    assert out["entities_resting_on_inducible"] > 0
    assert out["links_inducible"] > 0
    assert out["entities_touched"] > 0
    assert out["base_entities"] > out["entities"]


def test_base_clusters_group_each_user():
    led, meta = synthetic(n_users=20, addrs_per_user=2, dust_sources=0,
                          weak_user_frac=0.0, seed=2)
    res = cluster(led)
    for addrs in meta["truth"].values():
        assert res.base.connected(addrs[0], addrs[1])


def test_inducible_merges_attributed_to_heuristics():
    led, _ = synthetic(n_users=60, seed=3)
    out = report(led)
    by_h = out["inducible_merges_by_heuristic"]
    assert sum(by_h.values()) >= 1
    assert all(v > 0 for v in by_h.values())


def test_dataio_round_trip(tmp_path):
    led, _ = synthetic(n_users=10, seed=4)
    dataio.save(led, str(tmp_path))
    back = dataio.load(str(tmp_path))
    assert len(back.transfers) == len(led.transfers)
    assert back.exchanges == led.exchanges
    assert len(back.multi_input) == len(led.multi_input)
    r1 = report(led)
    r2 = report(back)
    assert r1["entities"] == r2["entities"]
