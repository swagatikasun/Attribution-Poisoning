import glob
import json
import os


def rows(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def share(out):
    base = out["base_entities"] or 1
    return out["entities_resting_on_inducible"] / base


def main():
    paths = sorted(glob.glob(os.path.join("results", "pollution_*.jsonl")))
    if not paths:
        print("no results; run experiments/run.py first")
        return
    for path in paths:
        print("==", os.path.basename(path))
        for out in rows(path):
            cfg = out["config"]
            print(
                dict(cfg),
                "| base_entities:", out["base_entities"],
                "| resting_on_inducible:", out["entities_resting_on_inducible"],
                f"({share(out):.0%})",
                "| fragile_bridges:", out["fragile_bridges"],
                "| addresses_at_risk:", out["addresses_at_risk"],
                "| entities_touched_by_dust:", out.get("entities_touched", 0),
            )


if __name__ == "__main__":
    main()
