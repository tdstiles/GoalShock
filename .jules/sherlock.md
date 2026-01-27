## 2026-01-21 - Fix Memory Leak in WebSocketGoalListener
**Bug:** `WebSocketGoalListener.active_fixtures` accumulated fixtures indefinitely, causing a memory leak and causing `get_active_fixtures()` to return finished games forever.
**Cause:** The polling loop (`_poll_cycle`) added new fixtures to the dictionary but never removed old ones that were no longer present in the "live" list from the API.
**Fix:** Modified `_poll_cycle` to track the set of current fixture IDs and remove any keys from `self.active_fixtures` that are not in the current set.

## 2026-01-25 - Fix Dimensional Error in Simulation Drift
**Bug:** `AlphaOneUnderdog` simulation mode caused prices to crash by ~6% in 50 seconds when they exceeded high thresholds.
**Cause:** The mean reversion drift calculation used `elapsed_step` (seconds) directly as the drift factor, instead of scaling it to the daily drift rate `dt` (fraction of day). This resulted in a drift force ~86,400 times stronger than intended relative to the daily factor.
**Fix:** Changed `drift` calculation in `_simulate_price_movement` to use `dt` instead of `elapsed_step`, aligning units with the volatility calculation and ensuring stable price simulation.

## 2026-01-27 - Fix Impossible Target Price in AlphaOne
**Bug:** AlphaOneUnderdog simulation mode created "stuck" positions that could never take profit because the calculated target price exceeded the simulation ceiling (0.99).
**Cause:** The target price calculation `current_price * (1 + take_profit_pct)` did not account for prices near 1.0, resulting in targets > 1.0 which are impossible to reach in probability markets (and capped by `SIM_PRICE_CEILING` in simulation).
**Fix:** Clamped `target_price` to `min(SIM_PRICE_CEILING, calculated_target)` in `on_goal_event`, ensuring exit targets are always reachable.
