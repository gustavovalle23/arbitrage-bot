import ccxt.async_support as ccxt


async def create_exchanges(config):
    result = {}

    for e in config.exchanges:
        if not e.enabled:
            continue

        cls = getattr(ccxt, e.id)
        opts = {"enableRateLimit": True}

        if e.rate_limit_ms:
            opts["rateLimit"] = e.rate_limit_ms

        if e.timeout_ms:
            opts["timeout"] = e.timeout_ms

        ex = cls(opts)

        if e.sandbox and hasattr(ex, "set_sandbox_mode"):
            ex.set_sandbox_mode(True)

        await ex.load_markets()

        result[e.id] = ex

    return result


async def close_exchanges(exchanges):
    for e in exchanges.values():
        await e.close()
