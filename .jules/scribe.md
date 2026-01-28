## 2026-01-28 - WebSocket components using Polling
**Confusion:** The `WebSocketGoalListener` class and `UnifiedTradingEngine` docstrings claimed "sub-second event updates" via WebSockets, but the implementation had been refactored to use 10s interval polling. This discrepancy caused confusion about the system's true latency and capabilities.
**Clarification:** Updated documentation to explicitly state that `WebSocketGoalListener` implements high-frequency polling (~10s) and that the class name is retained for legacy compatibility.
