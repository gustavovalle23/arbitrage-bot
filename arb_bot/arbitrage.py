import logging
from decimal import Decimal
from itertools import combinations

logger = logging.getLogger("arb")


def fee(v, bps):
    return v * (bps / Decimal("10000"))


def buy_depth(asks, capital):
    remaining = capital
    base = Decimal("0")
    spent = Decimal("0")

    for p, a in asks:
        cost = p * a
        if remaining >= cost:
            base += a
            spent += cost
            remaining -= cost
        else:
            part = remaining / p
            base += part
            spent += remaining
            break

    return base, spent


def sell_depth(bids, amount):
    remaining = amount
    received = Decimal("0")

    for p, a in bids:
        fill = min(a, remaining)
        received += fill * p
        remaining -= fill
        if remaining <= 0:
            break

    return received


def find_opportunities(books, config):
    """Returns (accepted_opportunities, all_candidates). all_candidates includes every checked pair with net bps and profit/loss."""
    accepted = []
    all_candidates = []

    grouped = {}
    for b in books:
        grouped.setdefault(b.symbol, []).append(b)

    logger.debug("Scanning %d symbols with %d books total", len(grouped), len(books))
    for symbol, venues in grouped.items():
        for a, b in combinations(venues, 2):
            o1 = check(a, b, symbol, config)
            o2 = check(b, a, symbol, config)

            for o in (o1, o2):
                if o is None:
                    continue
                all_candidates.append(o)
                if o.get("accepted"):
                    accepted.append(o)

    accepted.sort(key=lambda x: x["bps"], reverse=True)
    all_candidates.sort(key=lambda x: x["bps"], reverse=True)
    if accepted:
        logger.debug("Found %d opportunities for %s", len(accepted), ", ".join(f"{o['buy']}->{o['sell']}" for o in accepted[:5]))

    return accepted, all_candidates


def _fee_bps_for_exchange(config, exchange_id):
    for e in config.exchanges:
        if e.id == exchange_id:
            return e.fee_bps
    return Decimal("0")


def check(buy, sell, symbol, config):
    quote = symbol.split("/")[1]
    capital = config.capital_by_quote.get(quote)

    if not capital:
        return None

    base, spent = buy_depth(buy.asks, capital)

    if base <= 0:
        return None

    received = sell_depth(sell.bids, base)

    buy_fee = fee(spent, _fee_bps_for_exchange(config, buy.exchange))
    sell_fee = fee(received, _fee_bps_for_exchange(config, sell.exchange))

    net = received - sell_fee - spent - buy_fee

    if spent <= 0:
        return None

    bps = (net / spent) * Decimal("10000")
    accepted = bps >= config.min_net_profit_bps

    return {
        "symbol": symbol,
        "buy": buy.exchange,
        "sell": sell.exchange,
        "profit_quote": str(net),
        "profit_bps": str(bps),
        "bps": float(bps),
        "net": net,
        "accepted": accepted,
    }