
from decimal import Decimal
from itertools import combinations


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
    out = []

    grouped = {}
    for b in books:
        grouped.setdefault(b.symbol, []).append(b)

    for symbol, venues in grouped.items():
        for a, b in combinations(venues, 2):
            o1 = check(a, b, symbol, config)
            o2 = check(b, a, symbol, config)

            if o1:
                out.append(o1)
            if o2:
                out.append(o2)

    out.sort(key=lambda x: x["profit_bps"], reverse=True)

    return out


def check(buy, sell, symbol, config):
    quote = symbol.split("/")[1]
    capital = config.capital_by_quote.get(quote)

    if not capital:
        return None

    base, spent = buy_depth(buy.asks, capital)

    if base <= 0:
        return None

    received = sell_depth(sell.bids, base)

    gross = received - spent

    buy_fee = fee(spent, next(e.fee_bps for e in config.exchanges if e.id == buy.exchange))
    sell_fee = fee(received, next(e.fee_bps for e in config.exchanges if e.id == sell.exchange))

    net = received - sell_fee - spent - buy_fee

    if spent <= 0:
        return None

    bps = (net / spent) * Decimal("10000")

    if bps < config.min_net_profit_bps:
        return None

    return {
        "symbol": symbol,
        "buy": buy.exchange,
        "sell": sell.exchange,
        "profit_quote": str(net),
        "profit_bps": str(bps)
    }