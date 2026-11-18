from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .cluster import cluster
from .dsu import DSU
from .heuristics import PRODUCTION_HEURISTICS


@dataclass
class DefenseResult:
    defended: DSU
    base: DSU
    support: dict

    def connected(self, a, b):
        return self.defended.connected(a, b)

    def certified_cost(self, a, b, threshold):
        ra, rb = self.base.find(a), self.base.find(b)
        if ra == rb:
            return 0
        have = len(self.support.get(frozenset((ra, rb)), ()))
        return max(0, threshold - have)


class ConsentAwareClustering:
    def __init__(self, threshold=2, heuristics=None, independent=False,
                 authored_only=True):
        self.threshold = threshold
        self.heuristics = heuristics or PRODUCTION_HEURISTICS
        self.independent = independent
        self.authored_only = authored_only

    def _deposit_exchange(self, ledger):
        mapping = {}
        for d in ledger.addresses():
            if d in ledger.exchanges:
                continue
            for t in ledger.outgoing(d):
                if t.receiver in ledger.exchanges:
                    mapping[d] = ("exchange", t.receiver)
                    break
        return mapping

    def _support_key(self, support, dep2ex):
        if self.independent and support in dep2ex:
            return dep2ex[support]
        return support

    def run(self, ledger):
        res = cluster(ledger, self.heuristics)
        dep2ex = self._deposit_exchange(ledger) if self.independent else {}
        support = defaultdict(set)
        for lk in res.links:
            if not lk.inducible:
                continue
            if self.authored_only and not lk.authored:
                continue
            ra, rb = res.base.find(lk.a), res.base.find(lk.b)
            if ra != rb and lk.support is not None:
                support[frozenset((ra, rb))].add(self._support_key(lk.support, dep2ex))

        defended = DSU(res.base.parent.keys())
        for members in res.base.groups().values():
            members = iter(members)
            first = next(members)
            for m in members:
                defended.union(first, m)
        for pair, supports in support.items():
            if len(supports) >= self.threshold:
                a, b = tuple(pair)
                defended.union(a, b)
        return DefenseResult(defended=defended, base=res.base, support=dict(support))


def evaluate(ledger, meta, thresholds, heuristics=None):
    out = []
    for k in thresholds:
        res = ConsentAwareClustering(k, heuristics).run(ledger)
        framings = meta.get("framings", [])
        blocked = sum(
            1 for attacker, u in framings
            if not res.connected(attacker, meta["truth"][u][0])
        )
        truth = meta["truth"]
        kept = sum(
            1 for addrs in truth.values()
            if all(res.connected(addrs[0], a) for a in addrs)
        )
        out.append({
            "threshold": k,
            "framings": len(framings),
            "framings_blocked": blocked,
            "block_rate": blocked / len(framings) if framings else 1.0,
            "recall": kept / len(truth) if truth else 1.0,
        })
    return out
