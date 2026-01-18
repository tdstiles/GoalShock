# Scout's Product Roadmap Journal

## 2026-01-18 - Exploration Session

### 🗺️ MAP - The Territory
**Mission:** GoalShock is an autonomous, high-frequency sports trading engine maximizing edge in prediction markets (Polymarket, Kalshi) via real-time soccer data.
**State:**
- **Backend:** Robust Python/FastAPI engine with two strategies (Alpha One: Underdog, Alpha Two: Compression). Supports Live/Sim modes and WebSocket feeds.
- **Frontend:** Minimalist "Hacker UI" (React/Vite). Dashboard shows real-time status, live trades, and markets. Settings allows basic config.
- **Gap:** The system is "in the moment" only. It lacks historical perspective (analytics), human intervention tools (manual trade), and passive monitoring (notifications).

### 🧠 BRAINSTORMING
1.  **Backtest/Replay Lab:** Run simulation on past data to build trust.
2.  **Performance Analytics:** Visual charts of P&L over time/strategy.
3.  **Manual "Sniper" Mode:** Human override for specific trades.
4.  **Notifications:** Discord/Telegram webhooks.
5.  **Strategy Profiles:** Save/Load different risk configurations.
6.  **Data Export:** CSV download of logs.
7.  **Leaderboard:** Gamification (Rejected: this is a solo tool).
8.  **Dark Pool:** Hidden orders (Rejected: Hallucination, exchange dependent).

### 💎 REFINED PITCHES
1.  **Performance Analytics Hub** (Dashboard)
2.  **Notification Webhooks** (Integration)
3.  **Session Activity Log** (Quality of Life)
4.  **CSV Data Export** (Missing Piece)
5.  **Strategy Playbooks** (Power User)
