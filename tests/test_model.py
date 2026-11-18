from apoison import Ledger


def test_addresses_cover_all_roles():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("a", "b", 1.0, block=1)
    led.add_deployment("c", "ctr", block=2)
    led.add_multi_input(["d", "e"], ["f"], block=3)
    assert led.addresses() == {"EX", "a", "b", "c", "ctr", "d", "e", "f"}


def test_first_inbound_picks_earliest():
    led = Ledger()
    led.add_transfer("x", "target", 1.0, block=50)
    led.add_transfer("y", "target", 1.0, block=10)
    assert led.first_inbound("target").sender == "y"


def test_first_inbound_none_when_unfunded():
    led = Ledger()
    led.add_transfer("target", "z", 1.0, block=1)
    assert led.first_inbound("target") is None
