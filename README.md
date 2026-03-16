# Cross-Exchange Arbitrage Scanner

A **read-only** arbitrage bot that scans multiple crypto exchanges for price differences on the same trading pairs. It fetches order books, walks the book to estimate fillable size, subtracts fees, and reports opportunities when net profit (in basis points) exceeds your threshold.

**Important:** This bot **does not place or execute any trades**. It only discovers and logs opportunities. You (or a separate execution layer) must act on them.

---

## What the Code Does

### High-level flow

1. **Load config** — Exchanges, symbols, capital per quote, fees, and thresholds from `config.json` (or `ARB_CONFIG_PATH`).
2. **Connect exchanges** — Uses [CCXT](https://github.com/ccxt/ccxt) to create async clients for each enabled exchange (with optional sandbox, rate limits, timeouts).
3. **Poll loop** — On each cycle:
   - Fetches order books for all configured symbols from all exchanges (concurrently).
   - For each symbol, compares every pair of venues (A vs B, both directions).
   - For each direction, simulates: *buy on one venue with your quote capital, sell the filled base on the other venue*, then subtracts buy/sell fees and computes net PnL in quote and in **basis points (bps)**.
   - Logs opportunities that meet `min_net_profit_bps`, and optionally logs the best/worst candidate when none qualify.
4. **Shutdown** — On SIGINT/SIGTERM, closes all exchange connections and exits.

### Main components

| File | Role |
|------|------|
| `main.py` | Entry point, async loop, signal handling, and cycle: fetch books → find opportunities → log → sleep. |
| `config_loader.py` | Reads JSON config and builds `AppConfig` and `ExchangeConfig` (symbols, capital per quote, fees, poll interval, etc.). |
| `exchange_factory.py` | Creates CCXT async exchange instances, loads markets, supports sandbox and rate/timeout options. |
| `book_fetcher.py` | Fetches order books for all symbols on all exchanges in parallel; normalizes levels to `(price, amount)` and returns `VenueBook` list. |
| `arbitrage.py` | **Core logic:** `buy_depth()` / `sell_depth()` walk asks/bids; fee calculation in bps; `find_opportunities()` pairs venues per symbol and returns accepted opportunities plus all candidates. |
| `models.py` | Dataclasses: `ExchangeConfig`, `AppConfig`, `VenueBook`. |
| `logger.py` | Configures the `arb` logger (level via `ARB_LOG_LEVEL`, default INFO). |

### How profit is computed

- **Buy side:** With a given quote budget, the bot walks the **asks** from best price upward, accumulating base and spent quote until the budget is used.
- **Sell side:** It then walks the **bids** on the other exchange with that base amount, accumulating received quote.
- **Fees:** Each exchange has a `fee_bps` (basis points). Fees are applied to spent (buy) and received (sell).
- **Net:** `net = received - sell_fee - spent - buy_fee`. Profit in bps: `(net / spent) * 10000`.
- An opportunity is **accepted** only if `bps >= min_net_profit_bps`.

---

## Constraints and Limitations

- **No execution** — The bot only scans and logs. No orders are sent. To monetize, you must execute elsewhere (manually or via another script/service).
- **Snapshot, not live execution** — It uses a single order-book snapshot per cycle. By the time you act, the book may have moved (slippage, latency).
- **No withdrawal/deposit logic** — It assumes you already have balance on both exchanges (or that you account for transfer time/cost separately).
- **Config-driven** — Only symbols and quote currencies present in `config.json` (and in `capital_by_quote`) are considered. Exchanges must be CCXT-supported and listed in config.
- **Fee model** — Simple linear fee in bps per exchange. No tiered or maker/taker split; adjust `fee_bps` to approximate your real fees.
- **Single-threaded event loop** — One poll cycle at a time; no built-in execution queue or risk checks.
- **No persistence** — Opportunities are only logged; no database or alerting (e.g. Telegram/Discord) unless you add it.

---

## Configuration

### Config file

By default the bot reads `config.json` from the current working directory. Override with:

```bash
export ARB_CONFIG_PATH=/path/to/your/config.json
```

### Example `config.json`

```json
{
  "exchanges": [
    {
      "id": "binance",
      "fee_bps": 10,
      "enabled": true,
      "rate_limit_ms": 1000,
      "timeout_ms": 10000,
      "sandbox": false
    },
    {
      "id": "kraken",
      "fee_bps": 16,
      "enabled": true,
      "sandbox": false
    }
  ],
  "symbols": ["BTC/USDT", "ETH/USDT"],
  "capital_by_quote": {
    "USDT": "10000"
  },
  "poll_interval_seconds": 5,
  "min_net_profit_bps": 15,
  "orderbook_limit": 20,
  "max_concurrent_requests": 10
}
```

- **exchanges** — CCXT exchange id (e.g. `binance`, `kraken`). `fee_bps` is used for net profit; `enabled`, `rate_limit_ms`, `timeout_ms`, `sandbox` control connection behavior.
- **symbols** — Pairs to scan (CCXT symbol format, e.g. `BTC/USDT`).
- **capital_by_quote** — Max quote to “spend” per cycle for each quote currency (e.g. USDT). Used for depth walking.
- **poll_interval_seconds** — Sleep between scan cycles.
- **min_net_profit_bps** — Minimum net profit (after fees) in basis points to log as an opportunity.
- **orderbook_limit** — Depth requested from each exchange (number of levels).
- **max_concurrent_requests** — Concurrency cap for fetching (used in the fetcher).

### Environment variables

| Variable | Purpose |
|----------|---------|
| `ARB_CONFIG_PATH` | Path to JSON config (default: `config.json`). |
| `ARB_LOG_LEVEL` | Logging level (e.g. `DEBUG`, `INFO`). Default: `INFO`. |

---

## How to Run

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Core dependency: **ccxt** (async). Run from the repo root or ensure `arb_bot` is on `PYTHONPATH`.

2. **Create `config.json`** (or set `ARB_CONFIG_PATH`) with your exchanges, symbols, `capital_by_quote`, and `min_net_profit_bps`.

3. **Run the scanner**

   ```bash
  cd arb_bot && python main.py
  ```

   Or from repo root:

   ```bash
  python -m arb_bot.main
  ```

   Stop with Ctrl+C; the bot will close exchange connections and exit.

---

## Guide: How to Make Profit From It

Because the bot does **not** execute trades, profit depends on how you use its output.

### 1. Use it as a discovery tool

- Run the bot and watch logs for lines like:  
  `Opportunity: BTC/USDT buy@binance sell@kraken profit_bps=... profit_quote=...`
- That tells you: *right now, in this snapshot*, buying on one exchange and selling on the other could yield that net profit after fees (in theory).

### 2. Act quickly and account for reality

- **Speed** — Opportunities often disappear in seconds. Automate execution (your own execution script or bot) if you want to capture them.
- **Slippage** — The bot uses a snapshot. Real fills may be worse than the computed `profit_quote`; use limits and size limits to control risk.
- **Fees** — Set `fee_bps` in config to match your actual trading (and any withdrawal) fees so “opportunities” are realistic.

### 3. Prefer pairs and venues with low fees and good liquidity

- Lower `fee_bps` and deeper books improve the chance that reported bps are actually achievable.
- Use `capital_by_quote` and `orderbook_limit` to match the size you intend to trade; oversized capital vs. thin books can make the model optimistic.

### 4. Keep capital on both sides

- The logic assumes you can buy on exchange A and sell on B. That usually means having quote on A and base (or quick way to get it) on B, or being able to move funds fast. Withdrawal/deposit delays can erase edge.

### 5. Optional next steps to monetize

- **Manual:** Run the bot, when you see a clear opportunity, place buy and sell orders on the two exchanges yourself.
- **Semi-auto:** Add alerts (e.g. Telegram/Discord) when `min_net_profit_bps` is exceeded, then execute manually or with a simple script.
- **Execution layer:** Build a separate module that reads the same config (and optionally the bot’s output or a shared state) and places orders via CCXT or exchange APIs, with your own risk and size limits.

### 6. Risk and compliance

- Trading and moving funds between exchanges can have tax and regulatory implications.
- Only risk capital you can afford to lose; past or theoretical bps do not guarantee future results.

---

## Summary

| Aspect | Detail |
|--------|--------|
| **Purpose** | Find cross-exchange arbitrage opportunities (buy one venue, sell another) after fees. |
| **Execution** | None; scanner only. |
| **Profit** | Use the logged opportunities to place trades yourself or via another system. |
| **Constraints** | Snapshot-based, config-driven, no execution, no transfer logic. |
| **Stack** | Python 3, asyncio, CCXT. |
