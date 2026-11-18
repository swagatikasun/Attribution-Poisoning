from apoison import synthetic, evaluate


def main():
    led, meta = synthetic(n_users=300, weak_user_frac=0.3, framings=40, seed=0)
    print("threshold | framing block rate | recall")
    for row in evaluate(led, meta, thresholds=[1, 2, 3, 4]):
        print(f"    {row['threshold']}     |"
              f"      {row['block_rate']:.0%}        |"
              f"  {row['recall']:.0%}")


if __name__ == "__main__":
    main()
