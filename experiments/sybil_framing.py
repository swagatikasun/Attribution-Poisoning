"""Sybil framing through a soft similarity feature.

The attacker cannot forge a hard ownership link to the victim without the victim's
deposit footprint, but soft features are a different matter. Here the attacker
creates S sybil addresses that all carry the victim's gas fingerprint, so a
pipeline that treats a shared fingerprint as evidence groups the sybils with the
victim. We measure contamination under two pipelines:

  soft-aware   includes the gas-fingerprint feature as a clustering signal
  hard-only    the production profile, which excludes soft features

The authorship criterion labels the gas fingerprint as third-party-inducible, so it
is forgeable by construction; the hard-only profile is immune only because it does
not use the feature, not because the consent defense neutralizes a soft score. A
sybil-classifier-aware defense is out of scope and left as future work.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apoison.model import Ledger
from apoison.cluster import cluster
from apoison.heuristics import (
    MultiInput, ChangeAddress, Deployment, GasFingerprint, DepositAddress, FirstFunder,
)

SOFT_AWARE = [MultiInput(), ChangeAddress(), Deployment(),
              DepositAddress(), GasFingerprint()]
HARD_ONLY = [MultiInput(), ChangeAddress(), Deployment(),
             DepositAddress(), FirstFunder()]


def build(n_sybils, n_legit=30):
    led = Ledger()
    block = 0
    for u in range(n_legit):
        a0, a1 = f"u{u}_0", f"u{u}_1"
        led.add_transfer(f"src{u}", a0, 1.0, block); block += 1
        led.add_transfer(f"src{u}", a1, 1.0, block); block += 1
        led.add_multi_input([a0, a1], [f"u{u}_out"], block); block += 1
        led.fingerprints[a0] = f"fp{u}"   # each legit user its own fingerprint
        led.fingerprints[a1] = f"fp{u}"
    victim = "u0_0"                        # victim carries fingerprint fp0
    for s in range(n_sybils):              # attacker sybils mimic fp0
        z = f"syb{s}"
        led.add_transfer("atk_src", z, 0.01, block); block += 1
        led.fingerprints[z] = "fp0"
    sybils = [f"syb{s}" for s in range(n_sybils)]
    return led, victim, sybils


def run(sweep=(1, 5, 20, 50)):
    rows = []
    for S in sweep:
        led, victim, sybils = build(S)
        for name, heur in (("soft-aware", SOFT_AWARE), ("hard-only", HARD_ONLY)):
            res = cluster(led, heur)
            contam = sum(res.same_entity(victim, z) for z in sybils)
            rows.append({"sybils": S, "pipeline": name,
                         "contaminating": contam,
                         "rate": contam / S})
    return rows


if __name__ == "__main__":
    rows = run()
    print(f"{'sybils':>7}{'pipeline':>12}{'in victim entity':>18}{'rate':>8}")
    for r in rows:
        print(f"{r['sybils']:>7}{r['pipeline']:>12}"
              f"{r['contaminating']:>18}{r['rate']:>8.2f}")
