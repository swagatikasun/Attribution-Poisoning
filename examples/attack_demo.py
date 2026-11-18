from apoison import Ledger, cluster, frame, collapse, sybil_frame, forces_merge


def framing():
    led = Ledger()
    led.exchanges.add("EX")
    led.add_transfer("victim", "victim_deposit", 1.0, block=100)
    led.add_transfer("victim_deposit", "EX", 1.0, block=101)
    plan = frame(led, "theft", "victim")
    print("framing:", plan.heuristic, "| txs:", plan.transactions(),
          "| works:", forces_merge(plan, led, "theft", "victim"))


def cluster_collapse():
    led = Ledger()
    for i in range(50):
        led.add_transfer(f"b{i}", "service", 1.0, block=i)
    led.add_transfer("b0", "b_peer", 1.0, block=1000)
    plan = collapse(led, "attacker", "b0")
    print("collapse:", plan.heuristic, "| txs:", plan.transactions(),
          "| cluster size absorbed: 50 | works:",
          forces_merge(plan, led, "attacker", "b0"))


def sybil():
    led = Ledger()
    targets = [f"c{i}" for i in range(6)]
    plan = sybil_frame(led, "attacker", targets)
    res = cluster(plan.apply(led))
    print("sybil framing:", plan.heuristic, "| txs:", plan.transactions(),
          "| all linked:", res.same_entity("c0", "c5"))


if __name__ == "__main__":
    framing()
    cluster_collapse()
    sybil()
