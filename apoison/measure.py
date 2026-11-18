from __future__ import annotations

from collections import defaultdict

from .cluster import cluster
from .dsu import DSU
from .defense import ConsentAwareClustering
from .heuristics import PRODUCTION_HEURISTICS


def truth_map(ledger, meta):
    tm = {}
    for u, addrs in meta["truth"].items():
        for a in addrs:
            tm[a] = f"user{u}"
    for attacker, _ in meta.get("framings", []):
        tm[attacker] = attacker
    return tm


def partition_metrics(dsu, labels):
    sc = defaultdict(int)
    sg = defaultdict(int)
    overlap = defaultdict(int)
    for a, tid in labels.items():
        c = dsu.find(a)
        sc[c] += 1
        sg[tid] += 1
        overlap[(c, tid)] += 1

    def pairs(n):
        return n * (n - 1) // 2

    same_cluster = sum(pairs(n) for n in sc.values())
    same_truth = sum(pairs(n) for n in sg.values())
    agree = sum(pairs(n) for n in overlap.values())
    precision = agree / same_cluster if same_cluster else 1.0
    recall = agree / same_truth if same_truth else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def vendor_eval(ledger, meta, thresholds, heuristics=None):
    labels = truth_map(ledger, meta)
    rows = []
    res = cluster(ledger, heuristics or PRODUCTION_HEURISTICS)
    vendor = partition_metrics(res.full, labels)
    vendor["mode"] = "vendor"
    vendor["block_rate"] = 0.0
    rows.append(vendor)
    framings = meta.get("framings", [])
    for k in thresholds:
        d = ConsentAwareClustering(k, heuristics).run(ledger)
        m = partition_metrics(d.defended, labels)
        m["mode"] = f"defended_k{k}"
        m["threshold"] = k
        blocked = sum(
            1 for attacker, u in framings
            if not d.connected(attacker, meta["truth"][u][0])
        )
        m["block_rate"] = blocked / len(framings) if framings else 1.0
        rows.append(m)
    return rows


def base_sizes(result):
    sizes = defaultdict(int)
    for x in result.base.parent:
        sizes[result.base.find(x)] += 1
    return sizes


def effective_inducible_merges(result):
    merged = DSU(base_sizes(result).keys())
    per_heuristic = defaultdict(int)
    for lk in result.links:
        if not lk.inducible:
            continue
        ua, ub = result.base.find(lk.a), result.base.find(lk.b)
        if ua != ub and merged.union(ua, ub):
            per_heuristic[lk.heuristic] += 1
    return dict(per_heuristic)


def fragile_merges(result):
    size = base_sizes(result)
    edges = []
    adj = defaultdict(list)
    for lk in result.links:
        if not lk.inducible:
            continue
        u, v = result.base.find(lk.a), result.base.find(lk.b)
        if u == v:
            continue
        i = len(edges)
        edges.append((u, v))
        adj[u].append((v, i))
        adj[v].append((u, i))

    disc, low = {}, {}
    timer = [0]
    visited = set()
    bridge_ids = set()
    for start in size:
        if start in visited:
            continue
        visited.add(start)
        disc[start] = low[start] = timer[0]
        timer[0] += 1
        stack = [(start, -1, iter(adj[start]))]
        while stack:
            node, parent_edge, neighbors = stack[-1]
            pushed = False
            for nbr, ei in neighbors:
                if ei == parent_edge:
                    continue
                if nbr not in visited:
                    visited.add(nbr)
                    disc[nbr] = low[nbr] = timer[0]
                    timer[0] += 1
                    stack.append((nbr, ei, iter(adj[nbr])))
                    pushed = True
                    break
                low[node] = min(low[node], disc[nbr])
            if not pushed:
                stack.pop()
                if stack:
                    upper = stack[-1][0]
                    low[upper] = min(low[upper], low[node])
                    if low[node] > disc[upper]:
                        bridge_ids.add(parent_edge)

    blocks = DSU(list(size.keys()))
    for i, (u, v) in enumerate(edges):
        if i not in bridge_ids:
            blocks.union(u, v)

    block_size = defaultdict(int)
    for root in size:
        block_size[blocks.find(root)] += size[root]

    entity_blocks = defaultdict(set)
    for root in size:
        entity_blocks[result.full.find(root)].add(blocks.find(root))

    at_risk = 0
    for ent, bset in entity_blocks.items():
        if len(bset) > 1:
            sizes = [block_size[b] for b in bset]
            at_risk += sum(sizes) - max(sizes)
    return {"fragile_bridges": len(bridge_ids), "addresses_at_risk": at_risk}


def dust_touch(ledger, result, tainted):
    touched = set()
    recipients = set()
    for t in ledger.transfers:
        if t.sender in tainted:
            recipients.add(t.receiver)
            touched.add(result.full.find(t.receiver))
    return {
        "tainted_sources": len(tainted),
        "dust_recipients": len(recipients),
        "entities_touched": len(touched),
    }


def merge_amplification(ledger, plan, anchor, heuristics=None):
    before = cluster(ledger, heuristics)
    after = cluster(plan.apply(ledger), heuristics)

    def entity_size(result, address):
        if address not in result.full.parent:
            return 0
        root = result.full.find(address)
        return len(result.full.groups().get(root, [address]))

    size_before = entity_size(before, anchor)
    size_after = entity_size(after, anchor)
    tx = plan.transactions()
    affected = size_after - size_before
    return {
        "entity_before": size_before,
        "entity_after": size_after,
        "forged_tx": tx,
        "addresses_affected": affected,
        "amplification": affected / tx if tx else 0.0,
    }


def report(ledger, heuristics=None, tainted=None):
    result = cluster(ledger, heuristics or PRODUCTION_HEURISTICS)
    out = result.pollution()
    out["addresses"] = len(ledger.addresses())
    out["base_entities"] = len(result.base.groups())
    out["inducible_merges_by_heuristic"] = effective_inducible_merges(result)
    out.update(fragile_merges(result))
    if tainted:
        out.update(dust_touch(ledger, result, tainted))
    return out
