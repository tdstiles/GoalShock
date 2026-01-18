# Sherlock's Journal

## 2026-01-18 - AlphaTwo Race Condition in Live Trading
**Bug:** Duplicate trades placed for the same market during live trading.
**Cause:** The `_analyze_market_for_clipping` loop detected a "new" opportunity while the previous opportunity for the same market was still awaiting execution (`await _place_exchange_order`). Since the trade wasn't yet in `self.trades`, the bot would try to execute it again.
**Fix:** Introduced `self.pending_orders: Set[str]` to track market IDs currently in the execution phase. `_analyze_market_for_clipping` now returns `None` if the market ID is in `pending_orders`.
