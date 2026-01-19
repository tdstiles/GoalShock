# Sherlock's Journal

## 2026-01-18 - AlphaTwo Race Condition in Live Trading
**Bug:** Duplicate trades placed for the same market during live trading.
**Cause:** The `_analyze_market_for_clipping` loop detected a "new" opportunity while the previous opportunity for the same market was still awaiting execution (`await _place_exchange_order`). Since the trade wasn't yet in `self.trades`, the bot would try to execute it again.
**Fix:** Introduced `self.pending_orders: Set[str]` to track market IDs currently in the execution phase. `_analyze_market_for_clipping` now returns `None` if the market ID is in `pending_orders`.

## 2026-05-23 - Silent Failure in WebSocket Fallback Logic
**Bug:** `HybridGoalListener` failed to switch to polling mode when the WebSocket listener exhausted all reconnection attempts.
**Cause:** `WebSocketGoalListener.start()` catches all exceptions internally and returns gracefully when `max_reconnect_attempts` is reached. The calling `_run_websocket` method assumed a clean return meant intentional stoppage, thus bypassing the `except Exception` block intended to trigger `use_polling_fallback`.
**Fix:** Modified `_run_websocket` to check if `self.running` is True but `self.ws_listener.running` is False after `start()` returns. This state indicates an unexpected stop, triggering the fallback to HTTP polling.

## 2025-02-19 - AlphaTwo Blind Spot on Draw Logic
**Bug:** `AlphaTwoLateCompression` silently ignored trading opportunities for matches that were tied (Draw) late in the game.
**Cause:** The `_predict_outcome` method returned `None` for any Draw scenario where the market was not yet resolved or `time_remaining > 0`. This prevented the bot from detecting high-confidence "NO" opportunities for "Team to Win" markets during late-game draws.
**Fix:** Updated `_predict_outcome` to calculate confidence for Draw scenarios instead of returning `None`. Updated `_calculate_soccer_confidence` to return `CONFIDENCE_HIGH` for Draws (lead margin 0) when `seconds_remaining < TIME_THRESHOLD_CRITICAL`.

## 2026-06-15 - AlphaOneUnderdog Inverted Confidence Logic
**Bug:** `AlphaOneUnderdog` assigned higher trade confidence to weaker underdogs (e.g., 1% win probability) than to stronger underdogs (e.g., 40% win probability) when they took the lead.
**Cause:** The confidence formula `1 - (odds / threshold)` inverted the relationship. Since "odds" here represented probability (0.0-1.0), a lower probability resulted in a higher factor. This contradicted the strategy of backing capable underdogs.
**Fix:** Corrected the formula to `min(1.0, odds / threshold)`, ensuring confidence scales positively with the underdog's pre-match win probability.
