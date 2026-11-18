from __future__ import annotations

from dataclasses import dataclass

from .dsu import DSU
from .heuristics import DEFAULT_HEURISTICS


@dataclass
class ClusterResult:
    links: list
    full: DSU
    base: DSU

    def same_entity(self, a, b):
        return self.full.connected(a, b)

    def inducible_dependent(self, a, b):
        return self.full.connected(a, b) and not self.base.connected(a, b)

    def entities(self):
        return self.full.groups()

    def base_entities(self):
        return self.base.groups()

    def pollution(self):
        full_groups = self.full.groups()
        total = len(full_groups)
        inducible_only = 0
        merged_base_clusters = 0
        for members in full_groups.values():
            base_roots = {self.base.find(x) for x in members}
            if len(base_roots) > 1:
                inducible_only += 1
                merged_base_clusters += len(base_roots)
        inducible_links = sum(1 for lk in self.links if lk.inducible)
        return {
            "entities": total,
            "entities_resting_on_inducible": inducible_only,
            "base_clusters_bridged": merged_base_clusters,
            "links_total": len(self.links),
            "links_inducible": inducible_links,
        }

    def poisonable_heuristics(self):
        return sorted({lk.heuristic for lk in self.links if lk.inducible})


def cluster(ledger, heuristics=None):
    heuristics = heuristics or DEFAULT_HEURISTICS
    items = ledger.addresses()
    full = DSU(items)
    base = DSU(items)
    links = []
    for h in heuristics:
        for lk in h.links(ledger):
            links.append(lk)
            full.union(lk.a, lk.b)
            if not lk.inducible:
                base.union(lk.a, lk.b)
    return ClusterResult(links=links, full=full, base=base)
