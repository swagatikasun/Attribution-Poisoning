from apoison import (
    Ledger,
    flag_dust_senders,
    natural_framing_candidates,
    agreement,
)


def main():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("alice", "alice_deposit", 1.0, block=10)
    led.add_transfer("alice_deposit", "EX", 1.0, block=11)
    for i in range(15):
        led.add_transfer("poisoner", f"stranger{i}", 0.0001, block=20 + i)
    led.add_transfer("poisoner", "alice_deposit", 0.0001, block=40)

    dust = flag_dust_senders(led)
    cands = natural_framing_candidates(led, dust_senders=dust)
    print("flagged dust senders:", sorted(dust))
    for c in cands:
        print("candidate:", c.legit, "vs", c.unsolicited, "at", c.deposit)

    answers = {c.pair_id: 1 for c in cands}
    print("if a public tool links them:", agreement(cands, answers))


if __name__ == "__main__":
    main()
