import sys

from apoison import dataio, flag_dust_senders, natural_framing_candidates, export_worklist


def main():
    if len(sys.argv) < 2:
        print("usage: python experiments/fieldwork_run.py transfers.csv "
              "[exchanges.txt] [worklist.csv]")
        return
    transfers = sys.argv[1]
    exchanges = set()
    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            exchanges = {line.strip() for line in f if line.strip()}
    out = sys.argv[3] if len(sys.argv) > 3 else "worklist.csv"

    led = dataio.load_transfers_csv(transfers, exchanges=exchanges)
    dust = flag_dust_senders(led)
    cands = natural_framing_candidates(led, dust_senders=dust)
    export_worklist(cands, out)
    print(f"transfers: {len(led.transfers)} | flagged dust senders: {len(dust)} "
          f"| candidates: {len(cands)}")
    print(f"wrote {out}; fill the vendor_linked column from a public tool, "
          f"then score with apoison.load_answers and apoison.agreement")


if __name__ == "__main__":
    main()
