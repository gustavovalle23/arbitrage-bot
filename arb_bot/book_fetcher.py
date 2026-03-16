import logging
from decimal import Decimal
from models import VenueBook

logger = logging.getLogger("arb")


def norm(levels):
    """Normalize order book levels to (price, amount) pairs. Handles [p, a] or [p, a, ...] formats."""
    out = []
    for level in levels:
        if len(level) < 2:
            continue
        price = Decimal(str(level[0]))
        amount = Decimal(str(level[1]))
        if price > 0 and amount > 0:
            out.append((price, amount))
    return out


async def fetch_books(exchanges, config):
    books = []

    for name, ex in exchanges.items():
        for symbol in config.symbols:
            if symbol not in ex.markets:
                continue
            try:
                ob = await ex.fetch_order_book(symbol, config.orderbook_limit)
            except Exception as e:
                logger.warning("Failed to fetch %s %s: %s", name, symbol, e)
                continue

            books.append(
                VenueBook(
                    exchange=name,
                    symbol=symbol,
                    asks=norm(ob["asks"]),
                    bids=norm(ob["bids"])
                )
            )

    return books
