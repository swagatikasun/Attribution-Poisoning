from apoison import synthetic, vendor_eval


def main():
    led, meta = synthetic(n_users=300, framings=40, dust_sources=5,
                          weak_user_frac=0.3, seed=0)
    print("mode        | precision | recall | f1   | framing block")
    for r in vendor_eval(led, meta, thresholds=[1, 2, 3]):
        print(f"{r['mode']:11s} |   {r['precision']:.2f}    |"
              f"  {r['recall']:.2f}  | {r['f1']:.2f} |   {r['block_rate']:.0%}")


if __name__ == "__main__":
    main()
