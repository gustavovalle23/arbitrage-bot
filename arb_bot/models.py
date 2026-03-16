from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ExchangeConfig:
    id: str
    fee_bps: Decimal
    enabled: bool = True
    rate_limit_ms: Optional[int] = None
    timeout_ms: Optional[int] = None
    sandbox: bool = False


@dataclass(frozen=True)
class AppConfig:
    poll_interval_seconds: Decimal
    min_net_profit_bps: Decimal
    orderbook_limit: int
    max_concurrent_requests: int
    symbols: List[str]
    capital_by_quote: Dict[str, Decimal]
    exchanges: List[ExchangeConfig]


@dataclass(frozen=True)
class VenueBook:
    exchange: str
    symbol: str
    asks: List[Tuple[Decimal, Decimal]]
    bids: List[Tuple[Decimal, Decimal]]
