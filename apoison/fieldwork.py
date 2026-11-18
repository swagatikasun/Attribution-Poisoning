from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass

from .heuristics import DepositAddress


@dataclass(frozen=True)
class Candidate:
    pair_id: str
    deposit: str
    legit: str
    unsolicited: str
    note: str


def flag_dust_senders(ledger, max_value=1e-3, min_recipients=10, tiny_frac=0.8):
    out_by_sender = defaultdict(list)
    for t in ledger.transfers:
        out_by_sender[t.sender].append(t)
    flagged = set()
    for sender, outs in out_by_sender.items():
        recipients = {t.receiver for t in outs}
        tiny = [t for t in outs if t.value <= max_value]
        if len(recipients) >= min_recipients and len(tiny) >= tiny_frac * len(outs):
            flagged.add(sender)
    return flagged


def natural_framing_candidates(ledger, dust_senders=None, amount_tol=0.01,
                               window=3200):
    dust = dust_senders if dust_senders is not None else flag_dust_senders(ledger)
    deposits = DepositAddress(amount_tol, window)._deposit_addresses(ledger)
    candidates = []
    i = 0
    for d in sorted(set(deposits)):
        senders = {t.sender for t in ledger.incoming(d)}
        if len(senders) < 2:
            continue
        unsolicited = sorted(s for s in senders if s in dust)
        legit = sorted(s for s in senders if s not in dust)
        if not unsolicited or not legit:
            continue
        for u in unsolicited:
            candidates.append(Candidate(
                pair_id=f"c{i}",
                deposit=d,
                legit=legit[0],
                unsolicited=u,
                note="co-deposit to one exchange address; sender flagged as dust",
            ))
            i += 1
    return candidates


def export_worklist(candidates, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "address_a", "address_b", "deposit", "note",
                    "vendor_linked"])
        for c in candidates:
            w.writerow([c.pair_id, c.legit, c.unsolicited, c.deposit, c.note, ""])


def load_answers(path):
    answers = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            value = (row.get("vendor_linked") or "").strip()
            if value in ("0", "1"):
                answers[row["pair_id"]] = int(value)
    return answers


def agreement(candidates, answers):
    checked = [c for c in candidates if c.pair_id in answers]
    linked = sum(answers[c.pair_id] for c in checked)
    return {
        "candidates": len(candidates),
        "checked": len(checked),
        "vendor_linked": linked,
        "link_rate": linked / len(checked) if checked else 0.0,
    }
