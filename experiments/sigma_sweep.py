"""Feasibility tracks the victim's own shared-party count.

A victim deposits to sigma distinct exchanges (authored, outgoing). An attacker
address B tries to force a false merge with the victim by co-depositing to every
one of the victim's deposit addresses, with an unbounded transaction budget. Under
the Ind* proxy the sigma deposit addresses collapse to sigma exchange sources, so
the merge is admitted only when sigma >= k. The attacker cannot raise sigma: it
cannot make the victim deposit to an exchange the victim does not use.

Expected: false-merge rate is 1 exactly when sigma >= k, and 0 otherwise,
independent of how many transactions the attacker sends.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apoison.model import Ledger
from apoison.defense import ConsentAwareClustering
from apoison.heuristics import MultiInput, ChangeAddress, Deployment, DepositAddress

HEURISTICS = [MultiInput(), ChangeAddress(), Deployment(), DepositAddress()]


def build(sigma, n_victims=40, attacker_budget=99, seed=0):
    led = Ledger()
    exchanges = [f"EX{e}" for e in range(sigma)]
    for e in exchanges:
        led.exchanges.add(e)
    block = 0
    victims = []
    for u in range(n_victims):
        a0, a1 = f"u{u}_0", f"u{u}_1"
        led.add_transfer(f"src{u}", a0, 1.0, block); block += 1
        led.add_transfer(f"src{u}", a1, 1.0, block); block += 1
        led.add_multi_input([a0, a1], [f"u{u}_out"], block); block += 1
        b = f"atk{u}"  # attacker-controlled target, its own component
        for e in range(sigma):
            dv = f"u{u}_dep{e}"
            led.add_transfer(a0, dv, 1.0, block); block += 1          # victim deposits (authored)
            led.add_transfer(dv, exchanges[e], 1.0, block); block += 1
            if e < attacker_budget:                                   # attacker co-deposits to same dep addr
                led.add_transfer(b, dv, 1.0, block); block += 1
        victims.append((b, a0))
    return led, victims


def run(sigmas=(1, 2, 3, 4), thresholds=(2, 3, 4)):
    rows = []
    for sigma in sigmas:
        led, victims = build(sigma)
        for k in thresholds:
            res = ConsentAwareClustering(k, HEURISTICS, independent=True).run(led)
            merged = sum(res.connected(b, a0) for b, a0 in victims)
            rows.append({"sigma": sigma, "k": k,
                         "false_merge_rate": merged / len(victims)})
    return rows


if __name__ == "__main__":
    rows = run()
    print(f"{'sigma':>6}{'k':>4}{'false-merge rate':>20}")
    for r in rows:
        print(f"{r['sigma']:>6}{r['k']:>4}{r['false_merge_rate']:>20.2f}")
