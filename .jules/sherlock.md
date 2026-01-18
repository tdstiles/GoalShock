## 2026-01-18 - Race Condition in Market Cleanup Logic
**Bug:** Race condition where resolved markets were deleted from memory while trades were still active, preventing trade resolution in simulation mode.
**Cause:** The `_market_scanner_loop` aggressively cleaned up markets marked as "resolved" without checking if any active trades still relied on that market data for their own resolution logic.
**Fix:** Modified `_market_scanner_loop` in `backend/alphas/alpha_two_late_compression.py` to check for active trades referencing the market ID. If an active trade exists, the market is preserved in memory until the trade is resolved.
