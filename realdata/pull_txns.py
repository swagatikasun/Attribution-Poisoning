"""Pull Ethereum transactions for the labeled addresses in truth.csv.

Free Etherscan API key required (etherscan.io -> API Keys). Uses the v2 unified
endpoint with chainid=1 (Ethereum mainnet). Writes transactions.csv with columns
tx_hash,from,to,value_eth,block. Resumable: re-running skips addresses already
pulled (tracked in _done.txt), so you can stop and restart in small batches.

Usage (PowerShell):
    python pull_txns.py --key YOURKEY
    python pull_txns.py --key YOURKEY --pages 2 --batch 40
"""
import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://api.etherscan.io/v2/api"


def fetch(address, key, pages, offset=1000, pause=0.25):
    out = []
    for page in range(1, pages + 1):
        q = {
            "chainid": 1, "module": "account", "action": "txlist",
            "address": address, "startblock": 0, "endblock": 99999999,
            "page": page, "offset": offset, "sort": "desc", "apikey": key,
        }
        url = ENDPOINT + "?" + urllib.parse.urlencode(q)
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                data = json.load(r)
        except Exception as e:
            print(f"  ! {address} page {page}: {e}")
            break
        if data.get("status") != "1" or not isinstance(data.get("result"), list):
            break  # no more results, or rate note
        rows = data["result"]
        for t in rows:
            out.append((t["hash"], t["from"].lower(),
                        (t["to"] or "").lower(),
                        int(t["value"]) / 1e18, int(t["blockNumber"])))
        if len(rows) < offset:
            break
        time.sleep(pause)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="Etherscan API key")
    ap.add_argument("--pages", type=int, default=2, help="pages of 1000 per address")
    ap.add_argument("--batch", type=int, default=0, help="stop after N addresses (0 = all)")
    ap.add_argument("--truth", default="truth.csv")
    ap.add_argument("--out", default="transactions.csv")
    args = ap.parse_args()

    with open(args.truth) as f:
        addrs = [row["address"] for row in csv.DictReader(f)]

    done = set()
    if os.path.exists("_done.txt"):
        done = set(open("_done.txt").read().split())

    new_file = not os.path.exists(args.out)
    out = open(args.out, "a", newline="")
    w = csv.writer(out)
    if new_file:
        w.writerow(["tx_hash", "from", "to", "value_eth", "block"])

    pending = [a for a in addrs if a not in done]
    if args.batch:
        pending = pending[:args.batch]
    print(f"{len(done)} done, pulling {len(pending)} addresses "
          f"({len(addrs) - len(done) - len(pending)} left after this batch)")

    for i, a in enumerate(pending, 1):
        rows = fetch(a, args.key, args.pages)
        w.writerows(rows)
        out.flush()
        with open("_done.txt", "a") as d:
            d.write(a + "\n")
        print(f"  [{i}/{len(pending)}] {a}  +{len(rows)} tx")

    out.close()
    print(f"done. appended to {args.out}")


if __name__ == "__main__":
    main()
