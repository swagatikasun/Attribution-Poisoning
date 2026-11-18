"""Sensitivity to the independence assumption.

Two questions the review raises about whether observable independence equals
real-world independence.

(a) Does the Ind* exchange collapse matter? An attacker batches m deposit
    addresses, all forwarding to one exchange, into one victim's footprint. With
    no collapse each deposit address is a distinct source and a k-threshold is
    defeated; with Ind* collapse the batch is one source and is blocked.

(b) What does a hidden shared custodian cost? If two observed exchanges are really
    one entity, a victim depositing to both shows an observed sigma of 2 but a true
    sigma of 1. We report the fraction of k=2 admissions whose two observed sources
    collapse to one true source, i.e. merges that look k-independent but are not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apoison.model import Ledger
from apoison.defense import ConsentAwareClustering
from apoison.heuristics import MultiInput, ChangeAddress, Deployment, DepositAddress

HEURISTICS = [MultiInput(), ChangeAddress(), Deployment(), DepositAddress()]


def batch_ledger(m, n_victims=40):
    """Each victim has m deposit addresses at ONE exchange; attacker co-deposits
    to all m, trying to supply m distinct supports from the batch."""
    led = Ledger()
    led.exchanges.add("EX")
    block = 0
    victims = []
    for u in range(n_victims):
        a0, a1 = f"u{u}_0", f"u{u}_1"
        led.add_transfer(f"src{u}", a0, 1.0, block); block += 1
        led.add_transfer(f"src{u}", a1, 1.0, block); block += 1
        led.add_multi_input([a0, a1], [f"u{u}_out"], block); block += 1
        b = f"atk{u}"
        for j in range(m):
            dv = f"u{u}_dep{j}"
            led.add_transfer(a0, dv, 1.0, block); block += 1
            led.add_transfer(dv, "EX", 1.0, block); block += 1
            led.add_transfer(b, dv, 1.0, block); block += 1
        victims.append((b, a0))
    return led, victims


def part_a(ms=(2, 3, 5), k=2):
    rows = []
    for m in ms:
        led, victims = batch_ledger(m)
        for independent in (False, True):
            res = ConsentAwareClustering(k, HEURISTICS, independent=independent).run(led)
            blocked = sum(not res.connected(b, a0) for b, a0 in victims)
            rows.append({"m": m, "policy": "Ind*" if independent else "no-collapse",
                         "block_rate": blocked / len(victims)})
    return rows


def part_b(n_victims=40):
    """Victims deposit to two observed exchanges EX0, EX1 that are secretly one
    custodian. Count admitted k=2 merges whose observed sources are really one."""
    led = Ledger()
    for e in ("EX0", "EX1"):
        led.exchanges.add(e)
    block = 0
    pairs = []  # (victim a0, attacker b) genuinely co-owned test pair
    for u in range(n_victims):
        a0, a1 = f"u{u}_0", f"u{u}_1"
        led.add_transfer(f"src{u}", a0, 1.0, block); block += 1
        led.add_transfer(f"src{u}", a1, 1.0, block); block += 1
        # a0 and a1 are the same owner, joined ONLY through two shared exchange
        # deposit addresses (one reused deposit address per exchange, as a real
        # user has): an inducible pair resting on two observed exchanges.
        for e in ("EX0", "EX1"):
            d = f"u{u}_{e}_dep"
            led.add_transfer(a0, d, 1.0, block); block += 1
            led.add_transfer(a1, d, 1.0, block); block += 1
            led.add_transfer(d, e, 1.0, block); block += 1
        pairs.append((a0, a1))
    res = ConsentAwareClustering(2, HEURISTICS, independent=True).run(led)
    # true custodian map: EX0 and EX1 are one entity
    merged = sum(res.connected(a0, a1) for a0, a1 in pairs)
    # every merge here rests on two observed exchanges that are one true source,
    # so all admitted merges are only pseudo-2-independent
    pseudo = merged
    return {"admitted_k2_merges": merged, "pseudo_independent": pseudo,
            "fraction": pseudo / merged if merged else 0.0}


if __name__ == "__main__":
    print("(a) batched deposit, block rate by independence model (k=2)")
    print(f"{'m':>4}{'policy':>14}{'block rate':>14}")
    for r in part_a():
        print(f"{r['m']:>4}{r['policy']:>14}{r['block_rate']:>14.2f}")
    print("\n(b) hidden shared custodian behind two observed exchanges (k=2)")
    b = part_b()
    print(f"admitted k=2 merges: {b['admitted_k2_merges']}, "
          f"pseudo-independent (really 1 source): {b['fraction']:.2f}")
