# 🐕 Hound: Bug Recon <2026-01-20>

## 1. Critical: AlphaTwo Trades on Default Fake Prices (FIXED)
- **Location:** `backend/engine_unified.py` (lines 351, 359) and `backend/alphas/alpha_two_late_compression.py` (line 527)
- **Impact:** **High** (Guaranteed financial loss or invalid simulation data)
- **Likelihood:** **High** (Occurs whenever market data fetch fails or market is not found)
- **Why this is a bug:**
  The `UnifiedTradingEngine` defaults `yes_price` and `no_price` to `0.5` when it fails to fetch market data (e.g., API error, market not found). `AlphaTwoLateCompression` treats this `0.5` as a valid market price. If the strategy calculates a target price of `1.0` (high confidence), it sees `0.5` as a 100% profit opportunity and attempts to trade. In Live mode, this places limit orders at `0.5` which likely won't fill (if real price > 0.5) or fill immediately at a loss (if real price < 0.5). In Simulation, it records fake trades with 100% PnL.
- **How to reproduce:**
  Run `AlphaTwo` in simulation mode with `polymarket_key` but disconnect internet or ensure API returns error. Observe logs showing trades executing at exactly `0.50` entry price.
- **Suggested Owner:** Sherlock
- **Resolution:** Fixed by Sherlock (2026-01-21). Updated DEFAULT_MARKET_PRICE to -1.0 in `engine_unified.py` to signal invalid data. Added guard clauses in `AlphaTwoLateCompression` to strictly reject prices < 0.

## 2. Critical: Kalshi Price Inversion & Negative Spread (FIXED)
- **Location:** `backend/exchanges/kalshi.py` (line 114, `get_orderbook`)
- **Impact:** **High** (Trading on inverted prices, immediate loss)
- **Likelihood:** **High** (Always occurs for Kalshi markets)
- **Why this is a bug:**
  The `get_orderbook` method calculates `yes_ask` as `no_bids[0][0]`. This assumes `Yes Ask == No Bid`. In binary markets, `Yes + No ≈ 100`. Therefore, `Yes Ask` should be roughly `1 - No Bid` (or `100 - No Bid` in cents). By setting `Yes Ask = No Bid`, the client incorrectly prices the asset. For example, if No Bid is 10 cents (implying Yes is ~90 cents), the client reports Yes Ask as 10 cents. The bot thinks it can buy cheap and executes a Buy order at 10 cents, which will not fill (market is at 90). The unit test `test_get_orderbook_success` incorrectly asserts this negative spread (`0.60` bid vs `0.38` ask) is correct.
- **How to reproduce:**
  Run `backend/tests/exchanges/test_kalshi_client.py`. The test `test_get_orderbook_success` passes but asserts a negative spread (`yes_bid` > `yes_ask`), confirming the logic error.
- **Suggested Owner:** Bolt
- **Resolution:** Fixed by Sherlock (2026-01-20). Updated calculation to `100 - no_bids[0][0]` and corrected unit tests.

## 3. High: Ghost Positions in Live Trading (FIXED)
- **Location:** `backend/alphas/alpha_one_underdog.py` (line 463) and `backend/alphas/alpha_two_late_compression.py` (line 576)
- **Impact:** **High** (State desynchronization, tracking non-existent trades)
- **Likelihood:** **High** (Limit orders frequently miss the book in fast-moving markets)
- **Why this is a bug:**
  Both strategies assume that `place_order` (which sends a LIMIT order) results in an immediate fill. They create a "Position" object and track PnL based on the limit price immediately after the API acknowledges receipt of the order. If the order sits in the orderbook unfilled (e.g. price moved), the bot tracks a "ghost position". `AlphaOne` verifies fill status on *exit*, but not *entry*. `AlphaTwo` does not appear to verify fill status at all.
- **How to reproduce:**
  In Live mode, trigger a trade signal where the limit price is slightly below the market ask. The order will be placed but not filled. The logs will show "Trade executed" and the bot will start reporting PnL updates for a position you don't actually hold.
- **Suggested Owner:** Sentinel
- **Resolution:** Fixed by Sherlock (2026-01-21). Added fill verification loop in `AlphaOneUnderdog` and `AlphaTwoLateCompression`. Strategies now poll `get_order` to confirm `FILLED` status before creating positions, cancelling orders that timeout.

## 4. Medium: Sequential Event Loop Blocking
- **Location:** `backend/engine_unified.py` (line 335, `_on_fixture_update`)
- **Impact:** **Medium** (System latency, missed opportunities)
- **Likelihood:** **High** (Always occurs when multiple fixtures are active)
- **Why this is a bug:**
  The `_on_fixture_update` method iterates through the list of fixtures and calls `_get_fixture_market_prices` (which performs network I/O) sequentially using `await` inside the loop. If there are 50 active fixtures and each call takes 1s, the loop blocks the entire engine (including the "10s" polling cycle) for 50 seconds. This causes massive latency in goal detection and trade execution.
- **How to reproduce:**
  Mock `APIFootballClient` to return 50 fixtures. Measure the time it takes for one poll cycle in `UnifiedTradingEngine`.
- **Suggested Owner:** Bolt

## 5. Low: Polymarket Market Search Fragility
- **Location:** `backend/engine_unified.py` (line 351) and `backend/exchanges/polymarket.py` (line 42)
- **Impact:** **Low** (Missed trades)
- **Likelihood:** **Medium**
- **Why this is a bug:**
  The bot constructs a search query string `"{home_team} vs {away_team}"` to find markets. If the exchange uses a different naming convention (e.g. "Away vs Home" or different spelling), the market search fails. While not a logic error, it's a fragile assumption that leads to `DEFAULT_MARKET_PRICE` fallbacks (triggering Bug #1).
- **How to reproduce:**
  Find a match where teams are listed differently on API-Football vs Polymarket. The bot will fail to find the market.
- **Suggested Owner:** Sherlock
