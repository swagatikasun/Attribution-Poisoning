from apoison import Ledger, cluster


def framing_scenario():
    led = Ledger()
    led.exchanges.add("EXCHANGE")

    led.add_transfer("victim_wallet", "victim_deposit", 1.0, block=100)
    led.add_transfer("victim_deposit", "EXCHANGE", 1.0, block=101)

    led.add_transfer("theft_address", "victim_deposit", 1.0, block=205)

    led.add_deployment("victim_wallet", "victim_contract", block=90)

    return led


def main():
    led = framing_scenario()
    res = cluster(led)

    print("same entity (victim_wallet, theft_address):",
          res.same_entity("victim_wallet", "theft_address"))
    print("inducible-dependent:",
          res.inducible_dependent("victim_wallet", "theft_address"))
    print("connected using signed evidence only:",
          res.base.connected("victim_wallet", "theft_address"))
    print("poisonable heuristics that fired:", res.poisonable_heuristics())
    print("pollution:", res.pollution())


if __name__ == "__main__":
    main()
