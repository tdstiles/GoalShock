## 2026-01-18 - Alpha Two Simulation Logic Fix

**Bug:** Trades in simulation mode never resolved, accumulating indefinitely without PnL calculation.
**Cause:**
1. The `feed_live_fixture_update` method explicitly returned early on match completion ('FT'), preventing the internal `monitored_markets` state from ever updating to 'resolved'.
2. The `_check_market_resolution` method was hardcoded to return `None`, with no logic to check internal state in simulation mode.
**Fix:**
1. Modified `feed_live_fixture_update` to handle 'FT' status by marking the market as resolved and updating the final score.
2. Implemented simulation logic in `_check_market_resolution` to look up the resolved status from `monitored_markets` and calculate the outcome using the existing `_predict_outcome` logic.
