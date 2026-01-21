## 2026-01-21 - Fix Memory Leak in WebSocketGoalListener
**Bug:** `WebSocketGoalListener.active_fixtures` accumulated fixtures indefinitely, causing a memory leak and causing `get_active_fixtures()` to return finished games forever.
**Cause:** The polling loop (`_poll_cycle`) added new fixtures to the dictionary but never removed old ones that were no longer present in the "live" list from the API.
**Fix:** Modified `_poll_cycle` to track the set of current fixture IDs and remove any keys from `self.active_fixtures` that are not in the current set.
