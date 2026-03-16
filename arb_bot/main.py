import asyncio
import signal
from config_loader import load_config
from exchange_factory import create_exchanges, close_exchanges
from book_fetcher import fetch_books
from arbitrage import find_opportunities
from logger import setup_logger


async def run(config):
    logger = setup_logger()
    exchanges = await create_exchanges(config)

    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, stop.set)
        except NotImplementedError:
            pass

    try:
        while not stop.is_set():
            books = await fetch_books(exchanges, config)
            opportunities = find_opportunities(books, config)

            for o in opportunities:
                logger.info(o)

            await asyncio.sleep(float(config.poll_interval_seconds))
    finally:
        await close_exchanges(exchanges)


def main():
    config = load_config()
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
