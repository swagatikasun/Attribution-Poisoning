from apoison import (
    Ledger,
    MultiInput,
    ChangeAddress,
    DeploymentHeuristic as DeploymentH,
    DepositAddress,
    FirstFunder,
    TokenAirdrop,
    CommonCounterparty,
    GasFingerprint,
    TemporalCoActivity,
    DEFAULT_HEURISTICS,
    SELF,
    INDUCIBLE,
)


def test_self_heuristics_never_inducible():
    led = Ledger()
    led.add_multi_input(["a", "b", "c"], ["change_out"], block=1)
    led.add_deployment("dev", "ctr", block=2)
    for h in (MultiInput(), ChangeAddress(), DeploymentH()):
        links = list(h.links(led))
        assert links
        assert all(not lk.inducible for lk in links)


def test_inference_heuristics_always_inducible():
    led = Ledger()
    led.add_transfer("a", "peer", 1.0, block=1)
    led.add_transfer("b", "peer", 1.0, block=2)
    led.fingerprints = {"a": "sig", "b": "sig"}
    for h in (CommonCounterparty(), GasFingerprint(), TemporalCoActivity()):
        links = list(h.links(led))
        assert links
        assert all(lk.inducible for lk in links)


def test_multi_input_links_all_inputs():
    led = Ledger()
    led.add_multi_input(["a", "b", "c"], ["out"], block=1)
    roots = set()
    for lk in MultiInput().links(led):
        roots.add(lk.a)
        roots.add(lk.b)
    assert {"a", "b", "c"} <= roots


def test_deposit_address_is_inducible():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("owner", "deposit", 1.0, block=10)
    led.add_transfer("deposit", "EX", 1.0, block=11)
    led.add_transfer("stranger", "deposit", 1.0, block=12)
    links = list(DepositAddress().links(led))
    assert links
    assert all(lk.inducible for lk in links)
    pair = {frozenset((lk.a, lk.b)) for lk in links}
    assert frozenset(("owner", "stranger")) in pair


def test_first_funder_is_inducible():
    led = Ledger()
    led.add_transfer("funder", "fresh", 1.0, block=5)
    links = [lk for lk in FirstFunder().links(led) if "fresh" in (lk.a, lk.b)]
    assert links and all(lk.inducible for lk in links)


def test_token_airdrop_links_recipients():
    led = Ledger()
    for r in ("r1", "r2", "r3"):
        led.add_transfer("airdropper", r, 0.001, block=1, asset="TKN")
    links = list(TokenAirdrop(min_recipients=3).links(led))
    assert links and all(lk.inducible for lk in links)


def test_common_counterparty_links_co_senders():
    led = Ledger()
    led.add_transfer("s1", "peer", 1.0, block=1)
    led.add_transfer("s2", "peer", 1.0, block=2)
    links = list(CommonCounterparty().links(led))
    assert links
    assert all(lk.inducible for lk in links)


def test_evidence_types_declared():
    kinds = {h.name: h.evidence_type for h in DEFAULT_HEURISTICS}
    safe = {"multi_input", "change_address", "deployment"}
    for name, kind in kinds.items():
        assert kind == (SELF if name in safe else INDUCIBLE)
