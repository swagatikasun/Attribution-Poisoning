from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transfer:
    tx: str
    sender: str
    receiver: str
    value: float
    block: int
    asset: str = "ETH"


@dataclass(frozen=True)
class MultiInputTx:
    tx: str
    inputs: tuple
    outputs: tuple
    block: int


@dataclass(frozen=True)
class Deployment:
    tx: str
    deployer: str
    contract: str
    block: int


@dataclass
class Ledger:
    transfers: list = field(default_factory=list)
    multi_input: list = field(default_factory=list)
    deployments: list = field(default_factory=list)
    exchanges: set = field(default_factory=set)
    fingerprints: dict = field(default_factory=dict)

    def add_transfer(self, sender, receiver, value, block, tx=None, asset="ETH"):
        tx = tx or f"t{len(self.transfers)}"
        self.transfers.append(Transfer(tx, sender, receiver, value, block, asset))

    def add_deployment(self, deployer, contract, block, tx=None):
        tx = tx or f"d{len(self.deployments)}"
        self.deployments.append(Deployment(tx, deployer, contract, block))

    def add_multi_input(self, inputs, outputs, block, tx=None):
        tx = tx or f"m{len(self.multi_input)}"
        self.multi_input.append(MultiInputTx(tx, tuple(inputs), tuple(outputs), block))

    def addresses(self):
        seen = set(self.exchanges)
        for t in self.transfers:
            seen.add(t.sender)
            seen.add(t.receiver)
        for d in self.deployments:
            seen.add(d.deployer)
            seen.add(d.contract)
        for m in self.multi_input:
            seen.update(m.inputs)
            seen.update(m.outputs)
        return seen

    def _ensure_index(self):
        n = len(self.transfers)
        if getattr(self, "_idx_n", None) == n and getattr(self, "_idx_out", None) is not None:
            return
        out = {}
        inc = {}
        for t in self.transfers:
            out.setdefault(t.sender, []).append(t)
            inc.setdefault(t.receiver, []).append(t)
        self._idx_out = out
        self._idx_in = inc
        self._idx_n = n

    def outgoing(self, address):
        self._ensure_index()
        return self._idx_out.get(address, [])

    def incoming(self, address):
        self._ensure_index()
        return self._idx_in.get(address, [])

    def first_inbound(self, address):
        ins = self.incoming(address)
        if not ins:
            return None
        return min(ins, key=lambda t: (t.block, t.tx))

    def copy(self):
        return Ledger(
            transfers=list(self.transfers),
            multi_input=list(self.multi_input),
            deployments=list(self.deployments),
            exchanges=set(self.exchanges),
            fingerprints=dict(self.fingerprints),
        )

    def next_block(self):
        blocks = [t.block for t in self.transfers]
        blocks += [m.block for m in self.multi_input]
        blocks += [d.block for d in self.deployments]
        return (max(blocks) + 1) if blocks else 0

    def first_seen_block(self):
        first = {}

        def mark(address, block):
            if address not in first or block < first[address]:
                first[address] = block

        for t in self.transfers:
            mark(t.sender, t.block)
            mark(t.receiver, t.block)
        for m in self.multi_input:
            for a in m.inputs + m.outputs:
                mark(a, m.block)
        for d in self.deployments:
            mark(d.deployer, d.block)
            mark(d.contract, d.block)
        return first
