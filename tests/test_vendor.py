from apoison import (
    Ledger,
    cluster,
    synthetic,
    partition_metrics,
    truth_map,
    vendor_eval,
)


def test_metrics_perfect_on_truth():
    led, meta = synthetic(n_users=30, dust_sources=0, framings=0, weak_user_frac=0.0,
                          seed=1)
    labels = truth_map(led, meta)
    res = cluster(led)
    m = partition_metrics(res.base, labels)
    assert m["recall"] == 1.0


def test_vendor_precision_hurt_by_attacks():
    led, meta = synthetic(n_users=150, framings=30, dust_sources=5, seed=2)
    rows = vendor_eval(led, meta, thresholds=[2])
    vendor = next(r for r in rows if r["mode"] == "vendor")
    assert vendor["precision"] < 1.0


def test_defense_recovers_precision():
    led, meta = synthetic(n_users=150, framings=30, dust_sources=5, seed=3)
    rows = vendor_eval(led, meta, thresholds=[2])
    vendor = next(r for r in rows if r["mode"] == "vendor")
    defended = next(r for r in rows if r["mode"] == "defended_k2")
    assert defended["precision"] > vendor["precision"]
    assert defended["block_rate"] == 1.0


def test_defense_precision_improves_with_threshold():
    led, meta = synthetic(n_users=150, framings=30, dust_sources=5, seed=4)
    rows = vendor_eval(led, meta, thresholds=[1, 2])
    p1 = next(r for r in rows if r["mode"] == "defended_k1")["precision"]
    p2 = next(r for r in rows if r["mode"] == "defended_k2")["precision"]
    assert p2 >= p1
