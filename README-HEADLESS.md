# GoalShock - Autonomous Soccer Trading Engine

**Headless autonomous trading engine** for soccer prediction markets. Runs completely independently via CLI.

[![Architecture](https://img.shields.io/badge/Architecture-Headless%20First-green)]()
[![Real APIs](https://img.shields.io/badge/APIs-Polymarket%20%7C%20Kalshi-blue)]()
[![No Calculations](https://img.shields.io/badge/Probabilities-Direct%20from%20Orderbook-orange)]()

---

## 🎯 What It Does

1. **Monitors live soccer** matches via API-Football
2. **Detects goals** in real-time by comparing scores
3. **Identifies underdog** from pre-match orderbook odds
4. **Validates underdog is LEADING** (not just tied)
5. **Executes trade** on Polymarket/Kalshi using raw orderbook prices
6. **Monitors positions** continuously for take-profit / stop-loss

**Zero frontend dependency.** The engine runs autonomously.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
nano .env  # Add your API keys

# 3. Run headless engine
python engine.py --mode headless
```

**That's it.** The engine is now running autonomously.

---

## 📋 Requirements

- Python 3.10+
- API Keys:
  - **API-Football** (RapidAPI) - Goal detection
  - **Polymarket** (wallet + private key) - Trading
  - **Kalshi** (email + password) - Trading

---

## ⚙️ Configuration

Edit `.env`:

```bash
# API Keys
API_FOOTBALL_KEY=your-rapidapi-key
POLYMARKET_API_KEY=your-wallet-address
POLYMARKET_WALLET_KEY=your-private-key
KALSHI_API_KEY=your-email
KALSHI_API_SECRET=your-password

# Risk Management
MAX_TRADE_SIZE_USD=1000
MAX_POSITIONS=10
MAX_DAILY_LOSS_USD=5000

# Exit Rules
TAKE_PROFIT_PERCENT=15  # Exit at +15%
STOP_LOSS_PERCENT=10    # Exit at -10%

# Underdog Criteria
UNDERDOG_THRESHOLD=0.50  # Pre-match odds < 50%
```

---

## 🏗️ Architecture

### Headless-First Design

```
┌─────────────────────────────────────┐
│     Headless Trading Engine         │
│  (Runs independently via CLI)       │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────────┐ │
│  │   Goal Detection Loop         │ │
│  │   • API-Football polling      │ │
│  │   • Score comparison          │ │
│  │   • Real-time goal events     │ │
│  └───────────────────────────────┘ │
│               ↓                     │
│  ┌───────────────────────────────┐ │
│  │   Trade Decision Engine       │ │
│  │   • Underdog identification   │ │
│  │   • Leading validation        │ │
│  │   • Direct orderbook prices   │ │
│  └───────────────────────────────┘ │
│               ↓                     │
│  ┌───────────────────────────────┐ │
│  │   Position Monitoring         │ │
│  │   • Continuous price checks   │ │
│  │   • Take-profit triggers      │ │
│  │   • Stop-loss triggers        │ │
│  └───────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
         │              │
         ▼              ▼
    Polymarket       Kalshi
```

**Optional Dashboard**: Run with `--mode dashboard` for monitoring UI

---

## 🎯 Trade Logic

### Critical Rule: Underdog Must Be LEADING

```python
# ❌ NO TRADE - Underdog scored but TIED
Score: 1-0 → Liverpool scores → 1-1 (TIED)
Decision: Skip (not leading)

# ❌ NO TRADE - Underdog scored but LOSING
Score: 2-0 → Liverpool scores → 2-1 (STILL LOSING)
Decision: Skip (not leading)

# ✅ EXECUTE - Underdog scored and LEADING
Score: 1-1 → Liverpool scores → 1-2 (LEADING)
Decision: Trade! (underdog > favorite)
```

### Market Prices = Probabilities

```python
# ✅ CORRECT - Use prices directly
orderbook = await polymarket.get_orderbook(token_id)
yes_price = orderbook["best_ask"]  # 0.42 = 42% probability

# ❌ WRONG - Don't calculate probabilities
# implied_prob = 1 / decimal_odds  # NO!
# This is already done by the exchange
```

---

## 📊 Example Run

```
2025-12-01 14:23:15 | INFO | 🤖 GoalShock Trading Engine Initialized
2025-12-01 14:23:15 | INFO |    Max Trade Size: $1000.0
2025-12-01 14:23:15 | INFO |    Take-Profit: 15.0%
2025-12-01 14:23:15 | INFO |    Stop-Loss: 10.0%
2025-12-01 14:23:20 | INFO | 👁️  Goal detection loop started
2025-12-01 14:23:20 | INFO | 📈 Position monitoring loop started
2025-12-01 14:25:30 | INFO | 📡 3 live fixtures found
2025-12-01 14:27:45 | INFO | ⚽ GOAL! Liverpool 1-2 Man City (67')
2025-12-01 14:27:45 | INFO | 🎯 Underdog Liverpool scored!
2025-12-01 14:27:45 | INFO |    ✅ LEADING: Liverpool 2 - 1
2025-12-01 14:27:46 | INFO | 💰 TRADE EXECUTED:
2025-12-01 14:27:46 | INFO |    Team: Liverpool
2025-12-01 14:27:46 | INFO |    Entry Price: 0.48 (48.0%)
2025-12-01 14:27:46 | INFO |    Size: $1000.00
2025-12-01 14:27:46 | INFO |    Active Positions: 1
2025-12-01 14:35:10 | INFO | 🎯 TAKE-PROFIT HIT:
2025-12-01 14:35:10 | INFO |    Entry: 0.48
2025-12-01 14:35:10 | INFO |    Exit: 0.56
2025-12-01 14:35:10 | INFO |    P&L: +16.67% ($167.00)
2025-12-01 14:35:10 | INFO | ✅ Position closed (Reason: TAKE_PROFIT)
```

---

## 🔧 API Integrations

### API-Football
- Real-time fixture monitoring
- Goal event detection
- Score comparison logic

### Polymarket
- Direct CLOB orderbook access
- YES/NO prices (raw probabilities)
- Order execution

### Kalshi
- Market orderbook access
- Cents to decimal conversion (42¢ → 0.42)
- Order execution

**No implied probability calculations anywhere** - prices ARE probabilities.

---

## 📁 Project Structure

```
backend/
├── engine.py                    # ⭐ Main headless engine
├── data/
│   ├── api_football.py          # Real-time goal detection
│   └── __init__.py
├── exchanges/
│   ├── polymarket.py            # Direct orderbook integration
│   ├── kalshi.py                # Direct orderbook integration
│   └── __init__.py
├── .env.example                 # Configuration template
└── requirements.txt             # Dependencies

HEADLESS-ENGINE.md               # Detailed documentation
README-HEADLESS.md               # This file
```

---

## 🎓 Key Concepts

### 1. Headless-First
- Engine runs via CLI
- No frontend dependency
- Dashboard is optional (monitoring only)

### 2. No Probability Calculations
- Orderbook prices ARE probabilities
- 0.42 = 42%, period
- No conversion formulas

### 3. Underdog Leading Validation
- Must be LEADING, not just tied
- `underdog_score > favorite_score`
- Critical validation before every trade

### 4. Continuous Risk Management
- Real-time position monitoring
- Auto-exit on TP/SL thresholds
- Position limits enforced

---

## 🚀 Production Deployment

```bash
# Run with systemd (Linux)
sudo systemctl enable goalshock
sudo systemctl start goalshock

# Run with screen
screen -S goalshock
python engine.py --mode headless
# Ctrl+A, D to detach

# Run with Docker
docker build -t goalshock .
docker run -d --env-file .env goalshock
```

---

## ✅ Success Criteria

Engine working correctly when you see:

- ✅ Live fixtures fetched every 10 seconds
- ✅ Goals detected with score comparison
- ✅ Underdog identified from pre-match odds
- ✅ Leading validation (not just tied)
- ✅ Market prices fetched directly from APIs
- ✅ Trades executed only when all conditions met
- ✅ Positions monitored for TP/SL every 10s
- ✅ Zero probability calculation formulas

---

## 📞 Support

- Documentation: [HEADLESS-ENGINE.md](HEADLESS-ENGINE.md)
- Architecture: Fully autonomous, headless-first
- APIs: Direct orderbook integration, no calculations

---

**Autonomous. Headless. Production-ready.**

Built for the hiring manager's architecture requirements.
