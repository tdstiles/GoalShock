# 🐕 Hound: Bug Recon <2024-05-22>

## 1. Polymarket Live Orders Unsigned (Critical)
*   **Location:** `backend/exchanges/polymarket.py` (Line 104, `place_order`)
*   **Status:** **FIXED** (Sherlock)
*   **Impact:** **High** (Live trading impossible)
*   **Likelihood:** **High** (100% failure rate in Live mode)
*   **Why this is a bug:** The `place_order` method sends a plain JSON payload to the Polymarket CLOB API without an EIP-712 signature. The API requires cryptographic signatures for all orders. The code contains comments acknowledging this (`# Daniel Note In production: Use private key to sign order`) but the implementation is missing.
*   **Resolution:** Added `py-clob-client` dependency and updated `PolymarketClient` to use `ClobClient.create_and_post_order` for EIP-712 compliant order signing using `POLYMARKET_PRIVATE_KEY`.

## 2. AlphaTwo Live Execution Missing (Critical)
*   **Location:** `backend/alphas/alpha_two_late_compression.py` (Line 414, `_place_exchange_order`)
*   **Status:** **FIXED** (Sherlock)
*   **Impact:** **High** (Live trading impossible for AlphaTwo)
*   **Likelihood:** **High** (100% failure rate)
*   **Why this is a bug:** The `_place_exchange_order` method explicitly returns `False` with a placeholder comment (`# Placeholder`), preventing any live trades from being executed even if a valid opportunity is found.
*   **Resolution:** Implemented `_place_exchange_order` to fetch market details, resolve token IDs (using explicit `tokens` mapping or `clobTokenIds` fallback), and execute orders via `PolymarketClient.place_order`.

## 3. Triple API Call Redundancy (High)
*   **Location:** `backend/engine_unified.py`, `backend/bot/websocket_goal_listener.py`, `backend/main_realtime.py`
*   **Impact:** **High** (API Rate Limit Exhaustion)
*   **Likelihood:** **High** (Certainty)
*   **Why this is a bug:** The system polls the API-Football `fixtures` endpoint from three independent loops running simultaneously:
    1. `UnifiedTradingEngine._live_fixture_loop` (30s interval)
    2. `WebSocketGoalListener._poll_cycle` (30s interval)
    3. `RealtimeIngestor._poll_live_matches` (via `main_realtime.py`)
    This triples the API usage, consuming ~8,600 calls/day against a 7,500 limit, guaranteeing daily service denial.
*   **Suggested Owner:** Bolt

## 4. AlphaTwo Live Resolution Missing (High)
*   **Location:** `backend/alphas/alpha_two_late_compression.py` (Line 432, `_check_market_resolution`)
*   **Status:** **FIXED** (Sherlock)
*   **Impact:** **High** (Memory Leak, Incorrect PnL)
*   **Likelihood:** **High** (Certainty in Live mode)
*   **Why this is a bug:** The `_check_market_resolution` method is guarded by `if self.simulation_mode:`. In Live mode, it returns `None`, meaning trades are never marked as resolved. This causes the `trades` dictionary to grow indefinitely and PnL is never realized/logged.
*   **Resolution:** Added `get_market` to `PolymarketClient` to fetch resolution details from Gamma API and implemented live resolution check in `AlphaTwoLateCompression`.

## 5. RealtimeIngestor Goal Detail Dependency (Medium)
*   **Location:** `backend/bot/realtime_ingestor.py` (Line 150, `_create_goal_event`)
*   **Impact:** **Medium** (Missed goal alerts in UI)
*   **Likelihood:** **Medium** (Depends on API response format)
*   **Why this is a bug:** The ingestor relies on `fixture_data.get("events", [])` to extract goal details (scorer, assist). However, the standard `/fixtures?live=all` endpoint often returns fixtures *without* the detailed events array unless specifically configured or requested. If events are missing, `_create_goal_event` returns `None`, silencing the goal alert.
*   **Suggested Owner:** Bolt

## 6. Shutdown Race Condition (Medium)
*   **Location:** `backend/engine_unified.py` (Methods `stop` vs `_live_fixture_loop`)
*   **Impact:** **Medium** (Error spam during shutdown)
*   **Likelihood:** **Medium**
*   **Why this is a bug:** The `stop()` method closes HTTP/WS clients immediately. However, the infinite loops (`while self.running`) might still be executing or waking up from sleep. They will attempt to use the closed clients before checking the `running` flag, causing `RuntimeError` or connection errors to be logged during shutdown.
*   **Suggested Owner:** Bolt

## 7. AlphaOne Simulation Exit Price (Medium)
*   **Location:** `backend/alphas/alpha_one_underdog.py` (Line 384, `monitor_positions`)
*   **Status:** **FIXED** (Sherlock)
*   **Impact:** **Medium** (Inaccurate Simulation PnL)
*   **Likelihood:** **Medium**
*   **Why this is a bug:** In simulation, the strategy uses `_get_current_market_price` (which returns the Ask price) to trigger Take Profit/Stop Loss and to calculate Exit Price. In reality, selling a position receives the Bid price. Using Ask price ignores the spread and inflates simulation performance.
*   **Resolution:** Added `get_bid_price` to `PolymarketClient` and updated `AlphaOneUnderdog` to use `_get_exit_price` (Bid) for position monitoring.

## 8. AlphaTwo Stoppage Time Discontinuity (Low)
*   **Location:** `backend/alphas/alpha_two_late_compression.py` (Line 522, `feed_live_fixture_update`)
*   **Impact:** **Low** (Minor logic error)
*   **Likelihood:** **Medium**
*   **Why this is a bug:** The logic assumes a fixed "stoppage buffer" added to the total time. At minute 45 (HT) and 90 (FT), the calculation for `seconds_remaining` can jump discontinuously (e.g., from 1 minute left to 8 minutes left) due to the way the buffer is applied, potentially confusing the volatility model.
*   **Suggested Owner:** Sherlock

## 9. Memory Leak in Event Log (Low)
*   **Location:** `backend/alphas/alpha_one_underdog.py`, `backend/alphas/alpha_two_late_compression.py`
*   **Impact:** **Low** (Memory growth over long uptime)
*   **Likelihood:** **Low**
*   **Why this is a bug:** The `self.event_log` list is appended to indefinitely and never pruned or flushed to disk automatically. While event objects are small, running the bot for months without restart could lead to significant memory consumption.
*   **Suggested Owner:** Bolt
