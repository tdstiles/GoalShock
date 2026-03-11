## 2026-01-28 - WebSocket components using Polling
**Confusion:** The `WebSocketGoalListener` class and `UnifiedTradingEngine` docstrings claimed "sub-second event updates" via WebSockets, but the implementation had been refactored to use 10s interval polling. This discrepancy caused confusion about the system's true latency and capabilities.
**Clarification:** Updated documentation to explicitly state that `WebSocketGoalListener` implements high-frequency polling (~10s) and that the class name is retained for legacy compatibility.

## 2026-01-29 - Missing event stream in API-Football client
**Confusion:** The `APIFootballClient.detect_goals` method lacked documentation on how it identifies goals from the `fixtures` API. The `detect_goals` name implied it was fetching a discrete event feed, but it was actually performing a local delta comparison between the current scores and the previously cached `(home_score, away_score)`.
**Clarification:** Added a docstring explaining that because the API's `live=all` endpoint only provides the current match state (aggregate scores), goals must be inferred by calculating the delta against `previous_scores`.
