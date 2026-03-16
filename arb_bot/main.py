import asyncio
import signal
from config_loader import load_config
from exchange_factory import create_exchanges, close_exchanges
from book_fetcher import fetch_books
from arbitrage import find_opportunities
from logger import setup_logger


async def run(config):
    logger = setup_logger()
    logger.info(
        "Starting arb bot: exchanges=%s symbols=%s poll_interval=%ss",
        [e.id for e in config.exchanges if e.enabled],
        config.symbols,
        config.poll_interval_seconds,
    )
    exchanges = await create_exchanges(config)

    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, stop.set)
        except NotImplementedError:
            pass

    cycle = 0
    try:
        while not stop.is_set():
            cycle += 1
            logger.debug("Cycle %d: fetching order books", cycle)
            books = await fetch_books(exchanges, config)
            logger.info("Fetched %d books from %d exchanges", len(books), len(exchanges))

            opportunities, all_candidates = find_opportunities(books, config)
            if opportunities:
                logger.info("Found %d opportunity(ies) above %s bps", len(opportunities), config.min_net_profit_bps)
                for o in opportunities:
                    logger.info(
                        "Opportunity: %s buy@%s sell@%s profit_bps=%s profit_quote=%s",
                        o["symbol"], o["buy"], o["sell"], o["profit_bps"], o["profit_quote"],
                    )
            elif all_candidates:
                best = all_candidates[0]
                worst = all_candidates[-1]
                logger.info(
                    "No opportunities (threshold=%s bps). Best: %s buy@%s sell@%s net %s bps, PnL %s | Worst: %s bps, PnL %s",
                    config.min_net_profit_bps,
                    best["symbol"], best["buy"], best["sell"], best["bps"], best["profit_quote"],
                    worst["bps"], worst["profit_quote"],
                )
            else:
                logger.info("No order book pairs to check (no candidates).")

            await asyncio.sleep(float(config.poll_interval_seconds))
    finally:
        logger.info("Shutting down, closing exchanges")
        await close_exchanges(exchanges)
        logger.info("Exchanges closed, exit")


def main():
    config = load_config()
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
