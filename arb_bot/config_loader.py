import json
import os
from decimal import Decimal
from models import AppConfig, ExchangeConfig


def d(v):
    return Decimal(str(v))


def load_config():
    path = os.getenv("ARB_CONFIG_PATH", "config.json")

    with open(path) as f:
        raw = json.load(f)

    exchanges = [
        ExchangeConfig(
            id=e["id"],
            fee_bps=d(e["fee_bps"]),
            enabled=e.get("enabled", True),
            rate_limit_ms=e.get("rate_limit_ms"),
            timeout_ms=e.get("timeout_ms"),
            sandbox=e.get("sandbox", False)
        )
        for e in raw["exchanges"]
    ]

    capital = {k: d(v) for k, v in raw["capital_by_quote"].items()}

    return AppConfig(
        poll_interval_seconds=d(raw["poll_interval_seconds"]),
        min_net_profit_bps=d(raw["min_net_profit_bps"]),
        orderbook_limit=int(raw["orderbook_limit"]),
        max_concurrent_requests=int(raw["max_concurrent_requests"]),
        symbols=raw["symbols"],
        capital_by_quote=capital,
        exchanges=exchanges
    )