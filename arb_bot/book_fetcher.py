import asyncio
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


async def _fetch_one(name, ex, symbol, limit):
    """Fetch a single order book. Returns VenueBook or None on failure."""
    try:
        ob = await ex.fetch_order_book(symbol, limit)
        return VenueBook(
            exchange=name,
            symbol=symbol,
            asks=norm(ob["asks"]),
            bids=norm(ob["bids"]),
        )
    except Exception as e:
        logger.warning("Failed to fetch %s %s: %s", name, symbol, e)
        return None


async def fetch_books(exchanges, config):
    logger.debug("Fetching order books for %s from %s", config.symbols, list(exchanges.keys()))

    tasks = []
    for name, ex in exchanges.items():
        for symbol in config.symbols:
            if symbol not in ex.markets:
                continue
            tasks.append(_fetch_one(name, ex, symbol, config.orderbook_limit))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    books = []
    for r in results:
        if isinstance(r, VenueBook):
            books.append(r)
        elif isinstance(r, Exception):
            logger.warning("Fetch error: %s", r)

    logger.debug("Fetched %d order books total", len(books))
    return books
