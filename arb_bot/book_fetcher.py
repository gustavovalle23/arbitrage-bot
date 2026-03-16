from decimal import Decimal
from models import VenueBook


def norm(levels):
    out = []
    for p, a in levels:
        price = Decimal(str(p))
        amount = Decimal(str(a))
        if price > 0 and amount > 0:
            out.append((price, amount))
    return out


async def fetch_books(exchanges, config):
    books = []

    for name, ex in exchanges.items():
        for symbol in config.symbols:
            if symbol not in ex.markets:
                continue

            ob = await ex.fetch_order_book(symbol, config.orderbook_limit)

            books.append(
                VenueBook(
                    exchange=name,
                    symbol=symbol,
                    asks=norm(ob["asks"]),
                    bids=norm(ob["bids"])
                )
            )

    return books
