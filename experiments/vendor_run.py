import json
import os
import time

from apoison import synthetic, vendor_eval

SIZES = [100, 200, 400, 800, 1600]
THRESHOLDS = [1, 2, 3]


def main():
    os.makedirs("results", exist_ok=True)
    path = os.path.join("results", "vendor_eval.jsonl")
    with open(path, "w") as f:
        for n in SIZES:
            led, meta = synthetic(n_users=n, framings=int(0.1 * n),
                                  dust_sources=5, weak_user_frac=0.3, seed=0)
            t0 = time.perf_counter()
            rows = vendor_eval(led, meta, THRESHOLDS)
            dt = round(time.perf_counter() - t0, 2)
            for r in rows:
                r["n_users"] = n
                f.write(json.dumps(r) + "\n")
            vendor = next(r for r in rows if r["mode"] == "vendor")
            k2 = next(r for r in rows if r["mode"] == "defended_k2")
            print(f"n={n:5d} | vendor P={vendor['precision']:.2f} "
                  f"-> defended(k2) P={k2['precision']:.2f} "
                  f"R={k2['recall']:.2f} block={k2['block_rate']:.0%} | {dt}s")
    print("wrote", path)


if __name__ == "__main__":
    main()
