from __future__ import annotations

from dataclasses import dataclass, field

from .cluster import cluster
from .heuristics import DepositAddress


@dataclass
class AttackPlan:
    goal: str
    heuristic: str
    forged: list = field(default_factory=list)
    note: str = ""

    def transactions(self):
        return len(self.forged)

    def fee(self, per_tx=1.0):
        return per_tx * len(self.forged)

    def gas_fee(self, gwei, gas_limit=21000):
        return len(self.forged) * gas_limit * gwei * 1e-9

    def apply(self, ledger):
        out = ledger.copy()
        block = out.next_block()
        for i, (sender, receiver, value) in enumerate(self.forged):
            out.add_transfer(sender, receiver, value, block + i, tx=f"forge{i}")
        return out


def _outgoing_peers(ledger, address, exclude):
    peers = {t.receiver for t in ledger.outgoing(address)}
    return [p for p in peers if p not in exclude and p != address]


def _non_hub_peer(ledger, address, hub_cap):
    counts = {}
    for t in ledger.transfers:
        counts.setdefault(t.receiver, set()).add(t.sender)
    for p in _outgoing_peers(ledger, address, ledger.exchanges):
        if len(counts.get(p, ())) < hub_cap:
            return p
    return None


def frame(ledger, attacker, victim, hub_cap=25, window=3200, amount_tol=0.01):
    deposits = set(DepositAddress(amount_tol, window)._deposit_addresses(ledger))
    victim_deposits = [
        d for d in deposits if any(t.sender == victim for t in ledger.incoming(d))
    ]
    if victim_deposits:
        d = sorted(victim_deposits)[0]
        return AttackPlan(
            goal=f"frame {attacker} as {victim}",
            heuristic="deposit_address",
            forged=[(attacker, d, 1.0)],
            note="attacker co-sends to the victim's exchange deposit address",
        )

    peer = _non_hub_peer(ledger, victim, hub_cap)
    if peer is not None:
        return AttackPlan(
            goal=f"frame {attacker} as {victim}",
            heuristic="common_counterparty",
            forged=[(attacker, peer, 1.0)],
            note="attacker co-sends to a non-hub peer the victim also sends to",
        )

    if ledger.first_inbound(victim) is None:
        return AttackPlan(
            goal=f"frame {attacker} as {victim}",
            heuristic="first_funder",
            forged=[(attacker, victim, 1.0)],
            note="attacker becomes the first funder of the unfunded victim address",
        )

    return None


def collapse(ledger, attacker, benign_member, redundancy=1, hub_cap=25):
    peers = _outgoing_peers(ledger, benign_member, ledger.exchanges)
    counts = {}
    for t in ledger.transfers:
        counts.setdefault(t.receiver, set()).add(t.sender)
    peers = [p for p in sorted(peers) if len(counts.get(p, ())) < hub_cap]
    if len(peers) < redundancy:
        return None
    forged = [(attacker, p, 1.0) for p in peers[:redundancy]]
    return AttackPlan(
        goal=f"collapse {attacker} into the cluster of {benign_member}",
        heuristic="common_counterparty",
        forged=forged,
        note="one co-send per corroborating heuristic; cost is independent of cluster size",
    )


def sybil_frame(ledger, source, targets, window=20):
    forged = [(source, t, 0.001) for t in sorted(targets)]
    return AttackPlan(
        goal=f"link {len(targets)} addresses as one sybil entity",
        heuristic="token_airdrop",
        forged=forged,
        note="attacker sends dust to every target in one window so they cluster as co-recipients",
    )


def forces_merge(plan, ledger, a, b, heuristics=None):
    res = cluster(plan.apply(ledger), heuristics=heuristics)
    return res.same_entity(a, b) and res.inducible_dependent(a, b)
