from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

SELF = "self"
INDUCIBLE = "inducible"
PARTIAL = "partial"


@dataclass(frozen=True)
class Link:
    a: str
    b: str
    heuristic: str
    inducible: bool
    evidence: tuple
    support: str = None
    authored: bool = False


def _chain(members, heuristic, inducible, evidence, support=None, authored=False):
    members = sorted(members)
    for a, b in zip(members, members[1:]):
        yield Link(a, b, heuristic, inducible, evidence, support, authored)


class Heuristic:
    name = "heuristic"
    evidence_type = SELF

    @property
    def poisonable(self):
        return self.evidence_type in (INDUCIBLE, PARTIAL)

    def links(self, ledger):
        return iter(())


class MultiInput(Heuristic):
    name = "multi_input"
    evidence_type = SELF

    def links(self, ledger):
        for m in ledger.multi_input:
            if len(m.inputs) > 1:
                yield from _chain(m.inputs, self.name, False, (m.tx,))


class ChangeAddress(Heuristic):
    name = "change_address"
    evidence_type = SELF

    def links(self, ledger):
        first = ledger.first_seen_block()
        for m in ledger.multi_input:
            fresh = [o for o in m.outputs if first.get(o, m.block) >= m.block and o not in m.inputs]
            if len(fresh) == 1 and m.inputs:
                yield Link(sorted(m.inputs)[0], fresh[0], self.name, False, (m.tx,))


class Deployment(Heuristic):
    name = "deployment"
    evidence_type = SELF

    def links(self, ledger):
        for d in ledger.deployments:
            yield Link(d.deployer, d.contract, self.name, False, (d.tx,))


class GasFingerprint(Heuristic):
    name = "gas_fingerprint"
    evidence_type = INDUCIBLE

    def links(self, ledger):
        groups = defaultdict(list)
        for address, tag in ledger.fingerprints.items():
            groups[tag].append(address)
        for tag, members in groups.items():
            if len(members) > 1:
                yield from _chain(members, self.name, True, (f"fp:{tag}",), support=f"fp:{tag}")


class DepositAddress(Heuristic):
    name = "deposit_address"
    evidence_type = INDUCIBLE

    def __init__(self, amount_tol=0.01, window=3200):
        self.amount_tol = amount_tol
        self.window = window

    def _deposit_addresses(self, ledger):
        for address in ledger.addresses():
            if address in ledger.exchanges:
                continue
            outs = [t for t in ledger.outgoing(address) if t.receiver in ledger.exchanges]
            if not outs:
                continue
            ins = ledger.incoming(address)
            for o in outs:
                match = [
                    i for i in ins
                    if 0 <= o.block - i.block <= self.window
                    and abs(i.value - o.value) <= self.amount_tol
                ]
                if match:
                    yield address
                    break

    def links(self, ledger):
        for d in self._deposit_addresses(ledger):
            senders = {t.sender for t in ledger.incoming(d)}
            if len(senders) > 1:
                yield from _chain(senders, self.name, True, (f"deposit:{d}",),
                                  support=d, authored=True)


class FirstFunder(Heuristic):
    name = "first_funder"
    evidence_type = INDUCIBLE

    def links(self, ledger):
        for address in ledger.addresses():
            funder = ledger.first_inbound(address)
            if funder and funder.sender != address:
                yield Link(address, funder.sender, self.name, True, (funder.tx,), support=funder.sender)


class TokenAirdrop(Heuristic):
    name = "token_airdrop"
    evidence_type = INDUCIBLE

    def __init__(self, min_recipients=3, window=20):
        self.min_recipients = min_recipients
        self.window = window

    def links(self, ledger):
        groups = defaultdict(list)
        for t in ledger.transfers:
            groups[(t.sender, t.asset, t.block // self.window)].append(t)
        for (sender, asset, bucket), batch in groups.items():
            recipients = {t.receiver for t in batch}
            if len(recipients) >= self.min_recipients:
                yield from _chain(recipients, self.name, True, (f"drop:{sender}:{asset}:{bucket}",), support=f"drop:{sender}")


class CommonCounterparty(Heuristic):
    name = "common_counterparty"
    evidence_type = INDUCIBLE

    def __init__(self, hub_cap=25):
        self.hub_cap = hub_cap

    def links(self, ledger):
        senders_to = defaultdict(set)
        receivers_from = defaultdict(set)
        for t in ledger.transfers:
            senders_to[t.receiver].add(t.sender)
            receivers_from[t.sender].add(t.receiver)
        for peer, co_senders in senders_to.items():
            if 1 < len(co_senders) <= self.hub_cap:
                yield from _chain(co_senders, self.name, True, (f"cosend:{peer}",),
                                  support=peer, authored=True)
        for peer, co_receivers in receivers_from.items():
            if 1 < len(co_receivers) <= self.hub_cap:
                yield from _chain(co_receivers, self.name, True, (f"corecv:{peer}",),
                                  support=peer, authored=False)


class TemporalCoActivity(Heuristic):
    name = "temporal_coactivity"
    evidence_type = INDUCIBLE

    def __init__(self, window=5, cap=25):
        self.window = window
        self.cap = cap

    def links(self, ledger):
        members = defaultdict(set)
        for t in ledger.transfers:
            bucket = t.block // self.window
            members[bucket].add(t.sender)
            members[bucket].add(t.receiver)
        for bucket, addrs in members.items():
            if 1 < len(addrs) <= self.cap:
                yield from _chain(addrs, self.name, True, (f"time:{bucket}",), support=f"time:{bucket}")


DEFAULT_HEURISTICS = [
    MultiInput(),
    ChangeAddress(),
    Deployment(),
    GasFingerprint(),
    DepositAddress(),
    FirstFunder(),
    TokenAirdrop(),
    CommonCounterparty(),
    TemporalCoActivity(),
]

PRODUCTION_HEURISTICS = [
    MultiInput(),
    ChangeAddress(),
    Deployment(),
    DepositAddress(),
    FirstFunder(),
    TokenAirdrop(),
]
