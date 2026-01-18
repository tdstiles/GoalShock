## 2026-01-18 - Race Condition in Market Cleanup Logic
**Bug:** Race condition where resolved markets were deleted from memory while trades were still active, preventing trade resolution in simulation mode.
**Cause:** The `_market_scanner_loop` aggressively cleaned up markets marked as "resolved" without checking if any active trades still relied on that market data for their own resolution logic.
**Fix:** Modified `_market_scanner_loop` in `backend/alphas/alpha_two_late_compression.py` to check for active trades referencing the market ID. If an active trade exists, the market is preserved in memory until the trade is resolved.

## 2026-01-20 - Division by Zero in Alpha Two Analysis and PnL
**Bug:** `ZeroDivisionError` crash when analyzing markets with 0.0 price or calculating PnL for trades with 0.0 entry price.
**Cause:** The `expected_profit_pct` calculation `((target - current) / current)` and PnL calculation `(1 - entry) / entry` assumed `current_price` and `entry_price` would always be positive, which fails for invalid market data or extreme edge cases (0% probability).
**Fix:** Added guard clauses in `backend/alphas/alpha_two_late_compression.py`:
1. In `_analyze_market_for_clipping`, return `None` if `current_price <= 0.001`.
2. In `_process_trade_resolution`, check if `entry_price > 0.001` before performing division.
