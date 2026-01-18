# 🔭 Scout: 5 Feature Proposals

### 1. Performance Analytics Hub
- **Concept:** A dedicated "Analytics" view in the dashboard visualizing P&L over time, win rates by strategy, and ROI per league.
- **Value:** Users need to know *where* they are winning to optimize settings. "Total P&L" is insufficient for tuning; they need trends.
- **Effort:** Medium
- **Tech:** React + `recharts` (standard, lightweight) consuming the existing JSON logs exported by the backend.

### 2. Notification Webhooks (Discord/Telegram)
- **Concept:** Add a "Webhooks" section to Settings where users can paste a Discord/Telegram URL to receive real-time alerts for executed trades.
- **Value:** "Set and forget." Users can trust the bot is working while away from the screen, reducing anxiety and the need to constantly check the dashboard.
- **Effort:** Low
- **Tech:** Python `requests` library in `backend/` to POST payloads to the webhook URL on trade events.

### 3. Session Activity Stream
- **Concept:** A scrolling, terminal-style "Activity Log" on the dashboard showing internal bot decisions (e.g., "Skipped match X: Odds too low", "Analyzing match Y").
- **Value:** Builds trust by showing the "brain" at work. Users currently only see *trades*, not the *opportunities rejected*, which is crucial for understanding strategy logic.
- **Effort:** Low
- **Tech:** WebSocket `status` message expansion to include log events, rendered in a scrollable `div` with monospace font.

### 4. CSV Data Export
- **Concept:** A "Download History" button in the Settings or Analytics view to export all trade execution data to CSV.
- **Value:** Enables external analysis in Excel/Python for tax reporting or deeper quantitative research that the UI cannot support.
- **Effort:** Low
- **Tech:** FastAPI endpoint generating a `StreamingResponse` of the Pandas/CSV formatted trade history.

### 5. Strategy Playbooks
- **Concept:** Upgrade "Settings" to support named profiles (e.g., "Aggressive Weekend", "Conservative Weekday") rather than a single global state.
- **Value:** Markets change (weekends have more games/volatility). Power users need to switch contexts instantly without manually re-typing 10 different parameters.
- **Effort:** Medium
- **Tech:** Extend `Settings` data structure to a dictionary of profiles stored in `settings.json`, with a UI dropdown to select the active one.
