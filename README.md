# Attribution Poisoning

Code for studying attribution poisoning: forging on-chain evidence to mislead the
heuristics that blockchain analytics use to cluster addresses into identities.

Batches 1 to 6 are included. Batch 1 is the clustering engine and the consent
classifier that separates self-authored evidence from third-party-inducible
evidence. Batch 2 is the attack constructions (framing, cluster collapse, sybil
framing) with a fee-cost calculator and a check that each attack forces the
intended merge. Batch 3 is the pollution measurement: a CSV loader for real
Ethereum slices, a scale generator that plants both legitimate clusters and
inducible pollution, and a report of how much attribution rests on inducible
evidence. Batch 4 is the consent-aware defense and its certified cost bound.
Batch 5 evaluates clustering quality against ground truth with and without the
defense. Batch 6 is the natural-experiment harness: it flags likely dust or
poisoning senders in a real transfer slice, finds existing cases where such a
sender co-deposits with a victim, and scores how often public tools already merged
them. Everything needs no chain access and no external data; the tests and examples
run on synthetic ledgers, and real data plugs in through the loader.

## The consent criterion

A clustering heuristic links two addresses when it sees a pattern of activity
between or around them. A link between `a` and `b` is:

- **self-authored** if the only way to produce its evidence is a single on-chain
  action that required authorization from both parties (or from a single owner of
  both). A Bitcoin multi-input spend, a contract deployment, and a change spend are
  self-authored.
- **third-party-inducible** if someone other than `a` and `b` can produce the
  evidence. Sending to an address, funding it, sharing a counterparty, receiving
  the same airdrop, or matching a timing or fee pattern are all inducible, because
  an attacker can insert its own address into the pattern without any signature
  from the victim.

A heuristic is poisonable when it can merge addresses on inducible evidence alone.
Because clustering takes the transitive closure of all links (union-find), one
forged inducible link can merge two entire identities.

## Layout

```
apoison/
  model.py        transfers, deployments, multi-input transactions, the ledger
  dsu.py          union-find
  heuristics.py   the heuristics and the self-authored / inducible labels
  cluster.py      the clustering engine and the consent classifier
  attacks.py      framing, cluster collapse, sybil framing, and the fee cost
  measure.py      pollution report: inducible share, fragile bridges, dust reach
  generate.py     synthetic ledgers with planted clusters and pollution
  defense.py      consent-aware clustering and the certified cost bound
  measure.py      also holds pairwise precision/recall/F1 and the vendor eval
  fieldwork.py    flag dust senders, find natural candidates, score public tools
  dataio.py       CSV load and save, including raw transfer slices
tests/            unit tests
examples/         a framing scenario and an attack demo
experiments/      batched pollution runs and a summary printer
```

## Install

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Tests

```
python -m pytest -q
```

## Example

```
PYTHONPATH=. python examples/synthetic.py
```

The example plants a victim with an exchange deposit address and an attacker that
sends a single transfer to that deposit address. The deposit-address heuristic then
clusters the attacker with the victim. The classifier shows that the two are one
entity in the full clustering, are not connected using signed evidence only, and
that the merge rests on inducible evidence.

## Attacks

```
PYTHONPATH=. python examples/attack_demo.py
```

Each attack returns a plan of forged transactions and its cost in transactions.

- **Framing** attaches a chosen address to a victim identity. It prefers the
  victim's exchange deposit address; otherwise it co-sends to a non-hub peer the
  victim also sends to, or becomes the first funder of an unfunded victim address.
  Cost: one transaction.
- **Cluster collapse** merges the attacker into a large benign cluster. Because
  clustering is transitive, one inducible link to any member absorbs the whole
  cluster, so the cost is one transaction and does not grow with the cluster size.
  Requiring corroboration from several heuristics raises the cost in proportion to
  that number, not to the cluster size.
- **Sybil framing** links a set of independent addresses as one entity by sending
  each of them dust in one window. Cost: one transaction per target.

Every attack uses only inducible evidence, so a vendor that clusters on
self-authored evidence alone resists all three. `forces_merge` applies a plan and
confirms the merge through the clustering engine.

## Pollution measurement

`report(ledger, tainted=...)` runs the clustering with a realistic production
profile of heuristics and reports:

- `entities_resting_on_inducible`: entities that fuse two or more signed-evidence
  clusters, so they exist only because of inducible evidence.
- `fragile_bridges`: inducible links whose removal would split an entity, each a
  merge that one forged transaction created.
- `addresses_at_risk`: addresses on the smaller side of those bridges.
- `dust_recipients` and `entities_touched`: reach of a set of tainted senders.
- `inducible_merges_by_heuristic`: which heuristic caused each inducible merge.

Run the batched experiments (one batch per command):

```
PYTHONPATH=. python experiments/run.py scale
PYTHONPATH=. python experiments/run.py density
PYTHONPATH=. python experiments/run.py dust
PYTHONPATH=. python experiments/analyze.py
```

## The defense

`ConsentAwareClustering(threshold=k)` clusters on self-authored evidence and merges
two signed-evidence clusters only when at least `k` distinct third parties induce a
link between them. Each inducible link records the party that induces it (a deposit
address, a shared peer, a funder, an airdropper), and one forged transaction can
introduce the attacker at only one such party, so `k` distinct parties require `k`
forged transactions.

`DefenseResult.certified_cost(a, b, k)` returns `k` minus the number of distinct
inducing parties already linking the two clusters. This is a lower bound on the
transactions an attacker must create to force the merge, because each additional
party needs its own forging transaction.

```
PYTHONPATH=. python examples/defense_demo.py
PYTHONPATH=. python experiments/defense_run.py
```

The sweep reports the trade-off. At `k = 2` every single-transaction framing is
blocked. When legitimate clusters are joined by self-authored evidence, recall is
unchanged; the only recall cost falls on legitimate entities that rest solely on
inducible evidence, which is the fraction the sweep varies.

## Clustering quality

`vendor_eval(ledger, meta, thresholds)` scores clustering against the planted
ground truth using pairwise precision, recall and F1, computed from a contingency
table so it scales. It compares the undefended production clustering (the vendor an
attacker targets) with the consent-aware defense at each threshold, over the
attack-relevant address universe (user addresses and the planted framing
attackers).

```
PYTHONPATH=. python examples/vendor_demo.py
PYTHONPATH=. python experiments/vendor_run.py
```

Under active poisoning the undefended clustering has near-zero precision on this
universe, because framings and dust fuse unrelated identities. At threshold two the
defense restores precision close to one and blocks every single-transaction
framing, at a recall cost equal to the share of legitimate clusters that rest on a
single inducible link.

## Using real data

`dataio.load_transfers_csv` reads a transfer slice exported from a public source
(for example Google BigQuery's `crypto_ethereum.transactions` or a Dune query) with
columns for sender, receiver, value and block, and an optional set of known
exchange addresses. The same `report` then runs on it unchanged.

## Checking real tools (no transactions, no funds)

The forged patterns already exist on-chain, so no new transaction is needed to test
real tools. The harness reads a public slice, flags likely dust or poisoning
senders, and lists existing cases where such a sender co-deposits to the same
exchange address as a victim:

```
PYTHONPATH=. python experiments/fieldwork_run.py transfers.csv exchanges.txt worklist.csv
```

This writes a worklist with an empty `vendor_linked` column. Look each pair up in a
free public attribution tool, mark the column `1` if the tool already clusters the
two addresses and `0` if not, then score how often tools merged on this inducible
evidence:

```
from apoison import load_answers, agreement, dataio, flag_dust_senders, natural_framing_candidates
led = dataio.load_transfers_csv("transfers.csv", exchanges={...})
cands = natural_framing_candidates(led, flag_dust_senders(led))
print(agreement(cands, load_answers("worklist.csv")))
```

Everything here is read-only. Notify any tool found vulnerable before publishing.

## Heuristics

| Heuristic | Evidence | Poisonable |
| --- | --- | --- |
| `multi_input` | self-authored | no |
| `change_address` | self-authored | no |
| `deployment` | self-authored | no |
| `deposit_address` | third-party-inducible | yes |
| `first_funder` | third-party-inducible | yes |
| `token_airdrop` | third-party-inducible | yes |
| `common_counterparty` | third-party-inducible | yes |
| `gas_fingerprint` | third-party-inducible | yes |
| `temporal_coactivity` | third-party-inducible | yes |

The safe heuristics share one property: their evidence is a single transaction that
the linked parties had to sign together, so an outsider cannot insert a victim into
it. In the account model there is no such joint-signature primitive for ordinary
transfers, so most account-model heuristics are poisonable.
