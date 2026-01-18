# GoalShock - Codebase Walkthrough & Guide

This document provides a detailed technical explanation of the GoalShock autonomous trading system as it exists in the codebase today (v1.1.2).

## 🎯 System Overview

GoalShock is an automated trading engine designed for sports prediction markets (Polymarket and Kalshi). It uses real-time match data to execute trades based on two specific alpha strategies:

1.  **Alpha One: Underdog Momentum** - Bets on underdogs immediately after they take the lead.
2.  **Alpha Two: Late-Stage Compression** - Bets on high-confidence outcomes as a match nears its end ("clipping").

The system is designed to run in **Simulation Mode** (paper trading) or **Live Mode** (real money).

---

## 🧠 Alpha Strategies Explained

### Alpha One: Underdog Momentum (`backend/alphas/alpha_one_underdog.py`)

**The Logic:**
Markets often underreact to an underdog taking the lead. This strategy identifies when a pre-match underdog scores a goal to take the lead (e.g., Liverpool leads 2-1 against a favorite).

**How it works:**
1.  **Pre-Match Scan:** Loads odds for all daily matches to identify the underdog (higher payout).
2.  **Goal Detection:** Listens for real-time goal events via WebSocket or polling.
3.  **Condition Check:**
    *   Did the underdog score?
    *   Is the underdog now **LEADING**? (Ties do not trigger trades).
    *   Is the confidence score high enough? (Calculated based on time remaining and lead margin).
4.  **Execution:** Buys "YES" shares on the underdog team to win.
5.  **Exit Management:**
    *   **Take Profit:** +15% (Configurable)
    *   **Stop Loss:** -10% (Configurable)

### Alpha Two: Late-Stage Compression (`backend/alphas/alpha_two_late_compression.py`)

**The Logic:**
As a game ends, the probability of the leading team winning approaches 100% ($1.00). This strategy attempts to capture the final few cents of profit (e.g., buying at $0.95 to sell at $1.00) when the outcome is statistically certain.

**How it works:**
1.  **Scanning:** Monitors active matches entering their final minutes.
2.  **Confidence Calculation:** Uses time remaining and score difference to calculate a "Confidence Score" (e.g., 2-goal lead with 5 mins left = 99% confidence).
3.  **Opportunity Detection:**
    *   If Confidence > 95% AND
    *   Projected Profit > 3% (Meaning the market price is still cheap enough).
4.  **Execution:** Buys shares of the leading team.
5.  **Exit:** Holds until market resolution (payout $1.00).

---

## 🏗️ Architecture & Entry Points

The codebase provides two main ways to run the engine:

### 1. Unified Engine (`backend/engine_unified.py`) - **RECOMMENDED**
This is the modern, feature-rich entry point that runs both strategies simultaneously.
*   **Features:** WebSockets for faster data, dual-strategy support, detailed stats logging.
*   **Usage:** Best for production and serious simulation.

### 2. Simple Headless Engine (`backend/engine.py`)
A lighter, simpler version of the engine that focuses primarily on the Underdog strategy.
*   **Features:** Polling-based (slower), simple logic, easy to debug.
*   **Usage:** Good for testing basic connectivity or running on low-resource environments.

### 3. Real-Time Dashboard API (`backend/main_realtime.py`)
A FastAPI backend designed to power a frontend dashboard (if one exists). It streams match data and trade signals via WebSockets to a UI.

---

## 🚀 How to Run GoalShock

### Prerequisites

1.  **Python 3.10+**
2.  **API Keys:**
    *   **API-Football (Required):** For live scores (`https://rapidapi.com/api-sports/api/api-football`).
    *   **Polymarket (Optional):** For live trading on Polygon chain.
    *   **Kalshi (Optional):** For live trading on Kalshi US regulated markets.

### 1. Installation

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Create a `.env` file in the `backend/` directory:

```env
# API Keys
API_FOOTBALL_KEY=your_rapidapi_key
POLYMARKET_API_KEY=your_wallet_address  # For Polymarket
POLYMARKET_WALLET_KEY=your_private_key  # For Polymarket signing
KALSHI_API_KEY=your_email
KALSHI_API_SECRET=your_password

# Trading Settings
TRADING_MODE=simulation        # or 'live'
MAX_TRADE_SIZE_USD=100
MAX_POSITIONS=5

# Strategy Settings
ENABLE_ALPHA_ONE=true          # Underdog Strategy
ENABLE_ALPHA_TWO=true          # Compression Strategy
UNDERDOG_THRESHOLD=0.45        # Max odds to be considered underdog
TAKE_PROFIT_PERCENT=15
STOP_LOSS_PERCENT=10
```

### 3. Running the Engine

**Option A: Run the Unified Engine (Simulation)**
This runs the full system with both strategies in paper-trading mode.
```bash
python engine_unified.py --mode simulation
```

**Option B: Run in Live Mode**
⚠️ **WARNING:** This will execute real trades with real money.
```bash
python engine_unified.py --mode live
```

**Option C: Run Specific Strategies**
You can toggle strategies using flags:
```bash
# Only run the Underdog strategy
python engine_unified.py --alpha-one --no-websocket
```

---

## 📂 File Structure Guide

*   `backend/engine_unified.py`: Main entry point for the bot.
*   `backend/engine.py`: Alternative simple entry point.
*   `backend/alphas/`: Contains the strategy logic.
    *   `alpha_one_underdog.py`: Logic for betting on upsets.
    *   `alpha_two_late_compression.py`: Logic for "sure thing" late bets.
*   `backend/bot/`: Core infrastructure.
    *   `websocket_goal_listener.py`: Handles real-time data feeds.
*   `backend/data/`: API Clients.
    *   `api_football.py`: wrapper for the sports data provider.
*   `backend/exchanges/`: Exchange integrations (Polymarket/Kalshi).

---

## 🔧 Troubleshooting

*   **`ModuleNotFoundError`**: Ensure you are running the command from the `backend/` directory, or that your `PYTHONPATH` includes it.
*   **"No live fixtures currently"**: The bot only runs when real soccer matches are happening. Check the API-Football schedule.
*   **WebSocket Errors**: If WebSockets fail, the bot automatically falls back to polling (slower but reliable). Use `--no-websocket` to force this.
