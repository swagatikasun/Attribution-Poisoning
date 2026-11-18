from __future__ import annotations

import csv
import os

from .model import Ledger

SEP = ";"


def save(ledger, path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "transfers.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tx", "sender", "receiver", "value", "block", "asset"])
        for t in ledger.transfers:
            w.writerow([t.tx, t.sender, t.receiver, t.value, t.block, t.asset])
    with open(os.path.join(path, "deployments.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tx", "deployer", "contract", "block"])
        for d in ledger.deployments:
            w.writerow([d.tx, d.deployer, d.contract, d.block])
    with open(os.path.join(path, "multi_input.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tx", "inputs", "outputs", "block"])
        for m in ledger.multi_input:
            w.writerow([m.tx, SEP.join(m.inputs), SEP.join(m.outputs), m.block])
    with open(os.path.join(path, "exchanges.txt"), "w") as f:
        f.write("\n".join(sorted(ledger.exchanges)))


def load(path):
    led = Ledger()
    tpath = os.path.join(path, "transfers.csv")
    with open(tpath, newline="") as f:
        for row in csv.DictReader(f):
            led.transfers.append(_transfer(row))
    dpath = os.path.join(path, "deployments.csv")
    if os.path.exists(dpath):
        with open(dpath, newline="") as f:
            for row in csv.DictReader(f):
                led.add_deployment(row["deployer"], row["contract"],
                                   int(row["block"]), tx=row["tx"])
    mpath = os.path.join(path, "multi_input.csv")
    if os.path.exists(mpath):
        with open(mpath, newline="") as f:
            for row in csv.DictReader(f):
                inputs = row["inputs"].split(SEP) if row["inputs"] else []
                outputs = row["outputs"].split(SEP) if row["outputs"] else []
                led.add_multi_input(inputs, outputs, int(row["block"]), tx=row["tx"])
    xpath = os.path.join(path, "exchanges.txt")
    if os.path.exists(xpath):
        with open(xpath) as f:
            led.exchanges = {line.strip() for line in f if line.strip()}
    return led


def load_transfers_csv(path, exchanges=None, sender="sender", receiver="receiver",
                       value="value", block="block", asset=None):
    led = Ledger()
    led.exchanges = set(exchanges or ())
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            led.transfers.append(
                _row_transfer(row, i, sender, receiver, value, block, asset)
            )
    return led


def _transfer(row):
    from .model import Transfer
    return Transfer(row["tx"], row["sender"], row["receiver"],
                    float(row["value"]), int(row["block"]), row.get("asset", "ETH"))


def _row_transfer(row, i, sender, receiver, value, block, asset):
    from .model import Transfer
    return Transfer(
        row.get("tx", f"t{i}"),
        row[sender],
        row[receiver],
        float(row[value]),
        int(row[block]),
        row[asset] if asset else "ETH",
    )
