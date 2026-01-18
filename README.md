# GoalShock v1.1.2

GoalShock is an autonomous sports trading engine designed for prediction markets like Polymarket and Kalshi. It leverages real-time data to execute high-probability trades based on match events.

For a deep technical dive into how the system works, please read [CODEBASE_WALKTHROUGH.md](CODEBASE_WALKTHROUGH.md).

---

## ⚡ Features

*   **Alpha One (Underdog Momentum):** Automatically bets on underdogs the moment they take the lead in a match.
*   **Alpha Two (Late-Stage Compression):** Identifies and trades on high-confidence outcomes ("sure things") in the final minutes of a game.
*   **Dual-Mode Operation:** Supports **Simulation** (paper trading) and **Live** (real money) modes.
*   **Real-Time Data:** Uses WebSockets for sub-second reaction times to goal events.

## 🚀 Quick Start

### 1. Prerequisites
*   Python 3.10+
*   [API-Football Key](https://rapidapi.com/api-sports/api/api-football) (Required for match data)
*   Polymarket or Kalshi account (for live trading)

### 2. Installation

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configuration
Copy the example environment file and add your keys:

```bash
cp .env.example .env
# Edit .env and add your API_FOOTBALL_KEY
```

### 4. Running the Engine

The recommended way to run GoalShock is using the **Unified Engine**:

```bash
# Run in Simulation Mode (Safe for testing)
python engine_unified.py --mode simulation

# Run in Live Mode (Real Money)
python engine_unified.py --mode live
```

---

## 📚 Documentation

*   **[CODEBASE_WALKTHROUGH.md](CODEBASE_WALKTHROUGH.md)**: Detailed explanation of strategies, architecture, and configuration.
*   **[SETUP-AND-RUN.md](SETUP-AND-RUN.md)**: Additional setup instructions.
*   **[HEADLESS-ENGINE.md](HEADLESS-ENGINE.md)**: Documentation for the legacy headless mode.

## ⚠️ Disclaimer
This software is for educational purposes only. Trading prediction markets involves significant risk. The authors are not responsible for financial losses incurred while using this software.
