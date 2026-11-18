import json
import os

from apoison import synthetic, evaluate

WEAK_FRACTIONS = [0.0, 0.15, 0.3, 0.45, 0.6]
THRESHOLDS = [1, 2, 3, 4]


def main():
    os.makedirs("results", exist_ok=True)
    path = os.path.join("results", "defense_curve.jsonl")
    with open(path, "w") as f:
        for wf in WEAK_FRACTIONS:
            led, meta = synthetic(n_users=300, weak_user_frac=wf, framings=40, seed=0)
            for row in evaluate(led, meta, THRESHOLDS):
                row["weak_user_frac"] = wf
                f.write(json.dumps(row) + "\n")
                print(f"weak={wf:.2f} k={row['threshold']} "
                      f"block={row['block_rate']:.0%} recall={row['recall']:.0%}")
    print("wrote", path)


if __name__ == "__main__":
    main()
