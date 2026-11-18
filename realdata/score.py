"""Real-data utility and poisoning resistance on exchange-labeled Ethereum data.

Ground truth: truth.csv maps labeled addresses to their exchange. Transactions:
transactions.csv (tx_hash,from,to,value_eth,block) pulled from Etherscan.

Part A measures how the undefended common-counterparty pipeline and the
consent-aware defense cluster the labeled addresses: pairwise precision/recall over
same-exchange pairs, singletons, and how many distinct exchanges fall into the
largest component (cross-exchange contamination).

Part B injects the incoming common-counterparty forgery between distinct exchanges
and measures how many forced cross-exchange merges each policy admits.
"""
import csv
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apoison.model import Ledger
from apoison.cluster import cluster
from apoison.defense import ConsentAwareClustering
from apoison.heuristics import CommonCounterparty

_HERE = Path(__file__).resolve().parent
TRUTH = str(_HERE / "truth.csv")
TX = str(_HERE / "transactions.csv")


def load():
    truth = {r["address"]: r["entity_id"] for r in csv.DictReader(open(TRUTH))}
    led = Ledger()
    for r in csv.DictReader(open(TX)):
        s, rc = r["from"], r["to"]
        if not s or not rc or s == rc:
            continue
        led.add_transfer(s, rc, float(r["value_eth"]), int(r["block"]))
    return truth, led


def pairwise(find, truth):
    comp = {}
    for a in truth:
        comp.setdefault(find(a), []).append(a)
    tp = fp = 0
    for members in comp.values():
        for x, y in combinations(members, 2):
            if truth[x] == truth[y]:
                tp += 1
            else:
                fp += 1
    byent = {}
    for a in truth:
        byent.setdefault(truth[a], []).append(a)
    total_pos = sum(len(v) * (len(v) - 1) // 2 for v in byent.values())
    fn = total_pos - tp
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / total_pos if total_pos else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else float("nan")
    singles = sum(1 for m in comp.values() if len(m) == 1)
    big = max(comp.values(), key=len)
    big_exch = len({truth[a] for a in big})
    return dict(tp=tp, fp=fp, fn=fn, prec=prec, rec=rec, f1=f1,
                singletons=singles, largest_addrs=len(big),
                largest_exchanges=big_exch, tp_pairs=tp)


def part_a(truth, led):
    print("== Part A: clustering quality over 333 labeled addresses ==")
    undef = cluster(led, [CommonCounterparty(hub_cap=20)])
    m_undef = pairwise(undef.full.find, truth)
    rows = [("undefended (all cc-links)", m_undef)]
    for k in (2, 3):
        d = ConsentAwareClustering(k, [CommonCounterparty(hub_cap=20)],
                                   independent=True, authored_only=True).run(led)
        rows.append((f"consent-aware k={k}", pairwise(d.defended.find, truth)))
    hdr = f"{'policy':<26}{'prec':>7}{'rec':>7}{'F1':>7}{'single':>8}{'big(addr/exch)':>16}"
    print(hdr)
    for name, m in rows:
        print(f"{name:<26}{m['prec']:>7.3f}{m['rec']:>7.3f}{m['f1']:>7.3f}"
              f"{m['singletons']:>8}{m['largest_addrs']:>8}/{m['largest_exchanges']:<7}")
    retained = rows[1][1]['tp_pairs'] / m_undef['tp_pairs'] if m_undef['tp_pairs'] else 0
    print(f"legitimate same-exchange pairs retained by consent-aware k=2: "
          f"{retained:.2f}")
    return rows


def part_b(truth, led, n_pairs=60, k_peers=2, seed=0):
    import random
    rng = random.Random(seed)
    byent = {}
    for a in truth:
        byent.setdefault(truth[a], []).append(a)
    ents = sorted(byent)
    # distinct-exchange hot-wallet pairs that are NOT already merged by the defense
    d0 = ConsentAwareClustering(2, [CommonCounterparty(hub_cap=20)],
                                independent=True, authored_only=True).run(led)
    cand = []
    tries = 0
    while len(cand) < n_pairs and tries < 5000:
        tries += 1
        e1, e2 = rng.sample(ents, 2)
        a = rng.choice(byent[e1]); b = rng.choice(byent[e2])
        if not d0.defended.connected(a, b):
            cand.append((a, b))
    # inject the incoming-counterparty forgery for each pair into a copy
    led2 = Ledger()
    led2.transfers = list(led.transfers)
    blk = max(t.block for t in led.transfers) + 1
    for i, (a, b) in enumerate(cand):
        for j in range(k_peers):
            p = f"forge_{i}_{j}"
            led2.add_transfer(p, a, 0.001, blk); blk += 1
            led2.add_transfer(p, b, 0.001, blk); blk += 1
    undef = cluster(led2, [CommonCounterparty(hub_cap=20)])
    dfn = ConsentAwareClustering(2, [CommonCounterparty(hub_cap=20)],
                                 independent=True, authored_only=True).run(led2)
    u_merged = sum(undef.full.connected(a, b) for a, b in cand)
    d_merged = sum(dfn.defended.connected(a, b) for a, b in cand)
    print("\n== Part B: forged cross-exchange merges (incoming counterparty) ==")
    print(f"pairs tested: {len(cand)}  (k_peers={k_peers})")
    print(f"undefended merged by forgery : {u_merged}/{len(cand)} "
          f"({u_merged/len(cand):.0%})")
    print(f"consent-aware merged         : {d_merged}/{len(cand)} "
          f"({d_merged/len(cand):.0%})")


if __name__ == "__main__":
    truth, led = load()
    print(f"loaded {len(led.transfers)} transfers, {len(truth)} labeled addresses\n")
    part_a(truth, led)
    part_b(truth, led)
