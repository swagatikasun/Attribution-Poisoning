from __future__ import annotations

import numpy as np

from .model import Ledger


def synthetic(n_users=200, addrs_per_user=2, peers=30, dust_sources=5,
              dust_per_source=15, framings=10, weak_user_frac=0.3,
              deposit_dust=0, seed=0):
    rng = np.random.default_rng(seed)
    led = Ledger()
    led.exchanges.add("EX")
    truth = {}
    deposits = {}
    block = 0

    weak = set(rng.choice(n_users, size=int(weak_user_frac * n_users), replace=False).tolist())
    for u in range(n_users):
        addrs = [f"u{u}_{k}" for k in range(addrs_per_user)]
        truth[u] = addrs
        origin = f"src{u}"
        for a in addrs:
            led.add_transfer(origin, a, 1.0, block)
            block += 1
        if u not in weak and addrs_per_user > 1:
            led.add_multi_input(addrs, [f"u{u}_out"], block)
            block += 1
        deposit = f"u{u}_dep"
        deposits[u] = deposit
        led.add_transfer(addrs[0], deposit, 1.0, block)
        block += 1
        led.add_transfer(deposit, "EX", 1.0, block)
        block += 1

    shops = [f"shop{j}" for j in range(peers)]
    for u in range(n_users):
        shop = shops[int(rng.integers(0, peers))]
        led.add_transfer(truth[u][0], shop, float(rng.random() + 0.1), block)
        block += 1

    tainted = {f"dust{s}" for s in range(dust_sources)}
    for source in sorted(tainted):
        count = min(dust_per_source, n_users)
        victims = rng.choice(n_users, size=count, replace=False)
        for u in victims:
            k = int(rng.integers(0, addrs_per_user))
            led.add_transfer(source, truth[int(u)][k], 0.0001, block)
            block += 1

    if deposit_dust:
        dep_list = sorted(deposits.values())
        for source in sorted(tainted):
            picks = rng.choice(len(dep_list), size=min(deposit_dust, len(dep_list)),
                               replace=False)
            for j in picks:
                led.add_transfer(source, dep_list[int(j)], 0.0001, block)
                block += 1

    planted = []
    n_frame = min(framings, n_users)
    for u in rng.choice(n_users, size=n_frame, replace=False):
        attacker = f"frame{int(u)}"
        led.add_transfer(attacker, deposits[int(u)], 1.0, block)
        block += 1
        planted.append((attacker, int(u)))

    return led, {"truth": truth, "tainted": tainted, "framings": planted,
                 "weak_users": weak}


def add_incoming_counterparty_attack(led, meta, k_parties=3, n_targets=10, seed=0):
    """Plant the incoming common-counterparty attack of the reviewer's
    counterexample: from k_parties distinct attacker peers P, send P->victim and
    P->Z so that victim and the attacker address Z become co-receivers of each P.
    The victim's relationship to every P is incoming, so none is an authored party;
    an authored-only policy must not count these supports."""
    rng = np.random.default_rng(seed + 10_000)
    truth = meta["truth"]
    block = led.next_block()
    planted = []
    keys = sorted(truth)
    n = min(n_targets, len(keys))
    for u in rng.choice(keys, size=n, replace=False):
        u = int(u)
        v = truth[u][0]
        z = f"icp{u}"
        for j in range(k_parties):
            p = f"icp{u}_p{j}"
            led.add_transfer(p, v, 0.001, block)
            block += 1
            led.add_transfer(p, z, 0.001, block)
            block += 1
        planted.append((z, u))
    meta = dict(meta)
    meta["icp_framings"] = planted
    return led, meta
