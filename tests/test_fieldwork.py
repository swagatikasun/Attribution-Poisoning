from apoison import (
    Ledger,
    flag_dust_senders,
    natural_framing_candidates,
    export_worklist,
    load_answers,
    agreement,
)


def ledger_with_natural_candidate():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("victim", "deposit", 1.0, block=10)
    led.add_transfer("deposit", "EX", 1.0, block=11)
    for i in range(12):
        led.add_transfer("duster", f"target{i}", 0.0001, block=20 + i)
    led.add_transfer("duster", "deposit", 0.0001, block=40)
    return led


def test_flag_dust_senders():
    led = ledger_with_natural_candidate()
    flagged = flag_dust_senders(led, max_value=1e-3, min_recipients=10)
    assert "duster" in flagged
    assert "victim" not in flagged


def test_natural_candidate_found():
    led = ledger_with_natural_candidate()
    cands = natural_framing_candidates(led, dust_senders={"duster"})
    assert len(cands) == 1
    c = cands[0]
    assert c.legit == "victim"
    assert c.unsolicited == "duster"
    assert c.deposit == "deposit"


def test_worklist_round_trip(tmp_path):
    led = ledger_with_natural_candidate()
    cands = natural_framing_candidates(led, dust_senders={"duster"})
    path = str(tmp_path / "worklist.csv")
    export_worklist(cands, path)
    rows = list(open(path))
    assert rows[0].startswith("pair_id")
    assert cands[0].pair_id in rows[1]


def test_agreement_scores_answers(tmp_path):
    import csv
    led = ledger_with_natural_candidate()
    cands = natural_framing_candidates(led, dust_senders={"duster"})
    path = str(tmp_path / "answers.csv")
    export_worklist(cands, path)
    rows = list(csv.DictReader(open(path, newline="")))
    for r in rows:
        r["vendor_linked"] = "1"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    answers = load_answers(path)
    stats = agreement(cands, answers)
    assert stats["checked"] == 1
    assert stats["vendor_linked"] == 1
    assert stats["link_rate"] == 1.0
