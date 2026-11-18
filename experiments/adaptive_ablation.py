"""Two-route adaptive ablation.

Compares a count-all corroboration policy with the authored-only policy of
Theorem 1 against two adaptive attacks:

  deposit batch       attacker co-deposits to a victim's exchange deposit address
                      (authored on both sides; blocked by the Ind* threshold)
  incoming peers      attacker sends P->victim and P->Z from several peers P
                      (incoming to the victim; the reviewer's counterexample)

The authored-only policy should block both; the count-all policy should fall to
the incoming-peer route once the attacker uses at least k distinct peers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apoison.defense import ConsentAwareClustering
from apoison.generate import synthetic, add_incoming_counterparty_attack
from apoison.heuristics import (
    MultiInput, ChangeAddress, Deployment, DepositAddress, CommonCounterparty,
)

HEURISTICS = [
    MultiInput(), ChangeAddress(), Deployment(),
    DepositAddress(), CommonCounterparty(),
]


def run(seeds, k_parties=3, thresholds=(2, 3)):
    rows = []
    for authored_only in (False, True):
        for k in thresholds:
            dep_blocked = dep_total = icp_blocked = icp_total = 0
            for seed in seeds:
                led, meta = synthetic(n_users=200, framings=10, seed=seed)
                led, meta = add_incoming_counterparty_attack(
                    led, meta, k_parties=k_parties, n_targets=10, seed=seed)
                res = ConsentAwareClustering(
                    k, HEURISTICS, independent=True,
                    authored_only=authored_only).run(led)
                truth = meta["truth"]
                for atk, u in meta["framings"]:
                    dep_total += 1
                    dep_blocked += not res.connected(atk, truth[u][0])
                for z, u in meta["icp_framings"]:
                    icp_total += 1
                    icp_blocked += not res.connected(z, truth[u][0])
            rows.append({
                "policy": "authored-only" if authored_only else "count-all",
                "k": k,
                "deposit_block_rate": dep_blocked / dep_total,
                "incoming_block_rate": icp_blocked / icp_total,
            })
    return rows


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--k-parties", type=int, default=3)
    args = ap.parse_args()
    rows = run(range(args.seeds), k_parties=args.k_parties)
    print(f"{'policy':<14}{'k':>3}{'deposit block':>16}{'incoming block':>16}")
    for r in rows:
        print(f"{r['policy']:<14}{r['k']:>3}"
              f"{r['deposit_block_rate']:>16.2f}{r['incoming_block_rate']:>16.2f}")
