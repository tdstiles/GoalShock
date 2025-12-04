# GoalShock Headless Trading Engine

## Architecture Overview

GoalShock is now a **fully autonomous headless trading engine** that runs independently without any frontend dependency.

### Key Design Principles

1. **Headless-First**: Engine runs 100% autonomously via CLI
2. **No Probability Calculations**: Prices from APIs ARE probabilities (0.35 = 35%)
3. **Underdog Must Lead**: Trade only when underdog is AHEAD, not just tied
4. **Real-Time Risk Management**: Continuous TP/SL monitoring

---

## Running the Engine

### Headless Mode (Default)

```bash
cd backend
python engine.py --mode headless
```

This runs the autonomous trading engine with:
- ✅ Real-time goal detection via API-Football
- ✅ Direct orderbook prices from Polymarket/Kalshi
- ✅ Automated trade execution
- ✅ Continuous TP/SL monitoring
- ✅ No frontend required

### With Dashboard (Optional)

```bash
python engine.py --mode dashboard
```

This runs the engine + optional monitoring dashboard:
- Engine runs in background
- Dashboard available at http://localhost:8000
- **Dashboard is for monitoring only - NOT required**

---

## How It Works

### 1. Goal Detection Loop

```
Every 10 seconds:
├─ Fetch live fixtures from API-Football
├─ Compare scores with previous state
├─ Detect new goals
└─ Process goal events
```

### 2. Trade Decision Logic

```
Goal Scored
    ↓
Is it the underdog that scored?
    ├─ NO → Skip
    └─ YES → Continue
        ↓
    Is underdog NOW LEADING?
        ├─ Tied (1-1) → ❌ NO TRADE
        ├─ Still Losing (1-2) → ❌ NO TRADE
        └─ LEADING (2-1) → ✅ EXECUTE
            ↓
        Get market price (YES price = raw probability)
            ↓
        Execute trade on Polymarket/Kalshi
```

### 3. Position Monitoring Loop

```
Every 10 seconds (while positions open):
├─ Fetch current market prices
├─ Calculate P&L for each position
├─ Check take-profit threshold (default 15%)
│   └─ If hit → Close position immediately
└─ Check stop-loss threshold (default 10%)
    └─ If hit → Close position immediately
```

---

## Market Data Integration

### CRITICAL: No Probability Calculations

```python
# ❌ WRONG - Don't do this:
implied_prob = 1 / decimal_odds  # NO!
prob = odds / (odds + 1)  # NO!

# ✅ CORRECT - Use prices directly:
orderbook = await polymarket.get_orderbook(token_id)
yes_price = orderbook["best_ask"]  # This IS the probability
# If yes_price = 0.42, that means 42% probability
```

### Polymarket Integration

```python
# Get orderbook
orderbook = await polymarket.get_orderbook(token_id)

# Prices ARE probabilities
yes_bid = 0.40  # 40% to buy YES
yes_ask = 0.42  # 42% to sell YES
mid = 0.41      # 41% mid-market

# NO CONVERSION NEEDED
```

### Kalshi Integration

```python
# Get orderbook (prices in cents)
orderbook = await kalshi.get_orderbook(ticker)

# Convert cents to decimal
yes_bid_cents = 40  # 40 cents
yes_bid = yes_bid_cents / 100  # = 0.40 = 40%

# Still no implied probability math - just unit conversion
```

---

## Trade Execution Examples

### Scenario 1: Underdog Tied ❌

```
Match: Man City (favorite) vs Liverpool (underdog)
Pre-match odds: City 0.65, Liverpool 0.35

Score: 1-0 (City leading)
Event: Liverpool scores → 1-1 (TIED)

Decision: NO TRADE
Reason: Underdog not leading (must be > not >=)
```

### Scenario 2: Underdog Takes Lead ✅

```
Match: Man City (favorite) vs Liverpool (underdog)
Score: 1-1 (Tied)
Event: Liverpool scores → 1-2 (Liverpool LEADING)

Decision: EXECUTE TRADE
├─ Fetch market price for Liverpool to win
├─ Market shows YES @ 0.48 (48% probability)
├─ Execute: BUY YES @ 0.48
└─ Monitor for TP (15%) or SL (10%)
```

### Scenario 3: Take-Profit Hit 🎯

```
Position opened: YES @ 0.48
Current price: 0.56
P&L: (0.56 - 0.48) / 0.48 = +16.7%

TP Threshold: 15%
Decision: CLOSE POSITION
Profit: +$167 on $1000 trade
```

### Scenario 4: Stop-Loss Hit 🛑

```
Position opened: YES @ 0.48
Current price: 0.42
P&L: (0.42 - 0.48) / 0.48 = -12.5%

SL Threshold: 10%
Decision: CLOSE POSITION
Loss: -$125 on $1000 trade
```

---

## Configuration

All parameters in `.env`:

```bash
# Risk Management
MAX_TRADE_SIZE_USD=1000      # Max $ per trade
MAX_POSITIONS=10             # Max concurrent positions
MAX_DAILY_LOSS_USD=5000      # Daily loss limit

# Trading Criteria
UNDERDOG_THRESHOLD=0.50      # Pre-match odds < 50%

# Exit Rules
TAKE_PROFIT_PERCENT=15       # Exit at +15%
STOP_LOSS_PERCENT=10         # Exit at -10%
```

---

## Logging

Engine provides detailed real-time logs:

```
2025-12-01 14:23:15 | INFO | 🤖 GoalShock Trading Engine Initialized
2025-12-01 14:23:15 | INFO |    Max Trade Size: $1000.0
2025-12-01 14:23:15 | INFO |    Take-Profit: 15.0%
2025-12-01 14:23:15 | INFO |    Stop-Loss: 10.0%
2025-12-01 14:23:20 | INFO | ⚽ GOAL DETECTED: Salah (Liverpool) - 67'
2025-12-01 14:23:20 | INFO |    Score: 1-2
2025-12-01 14:23:20 | INFO | 🎯 Underdog Liverpool scored!
2025-12-01 14:23:20 | INFO |    ✅ LEADING: Liverpool 2 - 1
2025-12-01 14:23:21 | INFO | 💰 TRADE EXECUTED:
2025-12-01 14:23:21 | INFO |    Team: Liverpool
2025-12-01 14:23:21 | INFO |    Entry Price: 0.48 (48.0%)
2025-12-01 14:23:21 | INFO |    Size: $1000.00
```

---

## Production Deployment

### Requirements

- Python 3.10+
- API Keys:
  - API-Football (RapidAPI)
  - Polymarket (wallet address + private key)
  - Kalshi (email + password)

### Deploy to Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run with systemd (Linux)
sudo systemctl enable goalshock
sudo systemctl start goalshock

# Run with screen (any OS)
screen -S goalshock
python engine.py --mode headless
# Ctrl+A, D to detach

# Run with Docker
docker build -t goalshock .
docker run -d --env-file .env goalshock
```

---

## Monitoring

### Health Checks

```python
# Check if engine is running
ps aux | grep engine.py

# Check logs
tail -f engine.log

# Check positions
# (Engine logs active positions count)
```

### Metrics to Track

- Total trades executed
- Win rate
- Average profit per trade
- Max drawdown
- Active positions
- TP/SL hit rate

---

## FAQ

**Q: Do I need the dashboard?**
A: No. The engine runs completely independently. Dashboard is optional for monitoring.

**Q: Where do the probabilities come from?**
A: Directly from Polymarket/Kalshi orderbooks. A YES price of 0.42 means 42% probability. No calculations needed.

**Q: What if underdog scores but is tied?**
A: NO TRADE. Underdog must be LEADING (score > opponent score).

**Q: How often are positions checked for TP/SL?**
A: Every 10 seconds while positions are open.

**Q: Can I change TP/SL thresholds?**
A: Yes, update `TAKE_PROFIT_PERCENT` and `STOP_LOSS_PERCENT` in `.env`.

---

## Success Criteria

Engine is working correctly if you see:

✅ Live fixtures fetched every 10 seconds
✅ Goals detected with score comparison
✅ Underdog identification from pre-match odds
✅ Leading validation (not just tied)
✅ Market prices fetched from real APIs
✅ Trades executed only when conditions met
✅ Positions monitored for TP/SL
✅ No probability calculation formulas anywhere

---

**Built for autonomous operation. Zero frontend dependency. Production-ready.**
