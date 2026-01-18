## 2025-02-14 - Stoppage Time Ignored in Late Compression
**Bug:** `AlphaTwoLateCompression` marked markets as "resolved" and stopped trading when `minute >= 90`, ignoring stoppage time.
**Cause:** `seconds_remaining` calculation used `max(0, (90 - minute) * 60)`, forcing 0 seconds for any minute >= 90.
**Fix:** Modified `feed_live_fixture_update` to assign 60 seconds of remaining time if `seconds_remaining <= 0` but status is still active (e.g. "2H"), keeping the market open during critical stoppage time.

## 2026-01-18 - Duplicate Trades in Alpha Two
**Bug:** `AlphaTwoLateCompression` executed duplicate trades for the same market opportunity if the market condition persisted across multiple updates.
**Cause:** The unique ID generated for each opportunity included a timestamp, so persistent market conditions generated new opportunity IDs, bypassing the simple ID-based deduplication check.
**Fix:** Added a check in `_analyze_market_for_clipping` to verify if an active trade already exists for the given `market_id`, returning `None` if so.

## 2026-01-28 - Stateless Price Simulation in Alpha One
**Bug:** `AlphaOneUnderdog` simulation generated stateless white noise instead of a random walk. The price calculation always started from `entry_price`, causing variance to grow linearly but preventing true price evolution.
**Cause:** `_simulate_price_movement` calculated new price as `entry_price * (1 + random_change)`, without updating the state of the position to reflect the new price.
**Fix:** Added `last_price` and `last_update_time` to `SimulatedPosition`. Updated `_simulate_price_movement` to calculate the next price step based on `last_price` and the elapsed time since `last_update_time`, ensuring proper compounding (random walk).
