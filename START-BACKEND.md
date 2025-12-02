# How to Start GoalShock Backend

## Quick Start

### Option 1: Using Python directly (Recommended)
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Using the setup script
```bash
cd backend
setup.bat  # This installs dependencies
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## What You Should See

When backend starts successfully:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Test Backend is Running

Open browser to: http://localhost:8000

You should see:
```json
{
  "status": "online",
  "service": "goalshock",
  "version": "2.0.0",
  "bot_running": false
}
```

## Now Start Frontend

In a NEW terminal:
```bash
cd app
npm run dev
```

Open: http://localhost:5173

## Expected Behavior

1. **Header shows "● Online"** (green) - WebSocket connected
2. **Click "Start Bot"** button
3. Button changes to **"Stop Bot"**
4. After 15-45 seconds, **live trades appear** in the feed
5. **Prediction Markets** section shows 4 markets with prices
6. **Live Soccer Matches** section shows 3 matches with scores

## Troubleshooting

### "○ Offline" in header
- Backend is not running
- Run `python -m uvicorn main:app --reload` in backend folder

### "Start Bot" doesn't change to "Stop Bot"
- Backend not responding
- Check backend terminal for errors
- Try restarting backend

### No trades appearing after clicking "Start Bot"
- Wait 15-45 seconds (random interval)
- Check backend terminal logs
- Bot generates trades randomly with 30% probability

### Port 8000 already in use
```bash
# Windows: Find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Then restart backend
```

## Backend Endpoints

- `GET /` - Health check
- `GET /api/status` - Bot status
- `POST /api/bot/start` - Start bot
- `POST /api/bot/stop` - Stop bot
- `GET /api/trades` - Get trades
- `GET /api/markets` - Get prediction markets
- `GET /api/markets/live` - Get live matches
- `WS /ws` - WebSocket for real-time updates

## Production Checklist

Before deploying to production:
- [ ] Update `.env` with real API keys
- [ ] Set `DEMO_MODE=false`
- [ ] Configure proper `MAX_TRADE_SIZE_USD`
- [ ] Add authentication layer
- [ ] Enable HTTPS
- [ ] Set up monitoring
