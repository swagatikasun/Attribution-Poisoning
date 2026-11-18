import json
import os
import sys
import time

from apoison import synthetic, report

BATCHES = {
    "scale": [50, 100, 200, 400, 800],
    "density": [10, 20, 40, 80, 160],
    "dust": [0, 2, 5, 10, 20],
}


def run_scale(sizes):
    for n in sizes:
        led, meta = synthetic(n_users=n, seed=0)
        t0 = time.perf_counter()
        out = report(led, tainted=meta["tainted"])
        out["config"] = {"batch": "scale", "n_users": n}
        out["seconds"] = round(time.perf_counter() - t0, 3)
        yield out


def run_density(peer_counts):
    for p in peer_counts:
        led, meta = synthetic(n_users=200, peers=p, seed=0)
        out = report(led, tainted=meta["tainted"])
        out["config"] = {"batch": "density", "peers": p}
        yield out


def run_dust(source_counts):
    for s in source_counts:
        led, meta = synthetic(n_users=200, dust_sources=s, seed=0)
        out = report(led, tainted=meta["tainted"])
        out["config"] = {"batch": "dust", "dust_sources": s}
        yield out


RUNNERS = {"scale": run_scale, "density": run_density, "dust": run_dust}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in BATCHES:
        print("usage: python experiments/run.py [scale|density|dust]")
        return
    batch = sys.argv[1]
    os.makedirs("results", exist_ok=True)
    path = os.path.join("results", f"pollution_{batch}.jsonl")
    with open(path, "w") as f:
        for out in RUNNERS[batch](BATCHES[batch]):
            f.write(json.dumps(out) + "\n")
            cfg = out["config"]
            print(cfg, "entities_on_inducible:", out["entities_resting_on_inducible"],
                  "fragile:", out["fragile_bridges"])
    print("wrote", path)


if __name__ == "__main__":
    main()
