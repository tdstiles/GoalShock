# WebSocket Connection Debugging Guide

## Issue: ERR_UNKNOWN_URL_SCHEME

This error occurs when the browser tries to navigate to a `ws://` URL as a link instead of establishing a WebSocket connection.

---

## Quick Diagnosis Steps

### Step 1: Test Backend is Running

```bash
# Check if backend is up
curl http://localhost:8000/health
```

**Expected**: `{"status": "healthy"}`

If this fails, backend is not running. Start it:
```bash
cd backend
python main.py
```

---

### Step 2: Use the WebSocket Test Page

Open `WS-TEST.html` in your browser:

```bash
# Open in browser
start WS-TEST.html   # Windows
open WS-TEST.html    # Mac
```

Click **"Connect"** button and watch for:
- ✅ **Connected** - WebSocket works! Issue is in React app
- ❌ **Connection failed** - Backend WebSocket endpoint has issues

---

### Step 3: Check Browser Console

1. Open React app: `http://localhost:5173`
2. Press **F12** to open DevTools
3. Go to **Console** tab
4. Look for WebSocket logs:
   - `[WebSocket] Attempting connection to: ws://localhost:8000/ws`
   - `[WebSocket] ✅ Connected successfully`
   - `[WebSocket] Message received: status`

---

### Step 4: Check Network Tab

1. In DevTools, go to **Network** tab
2. Filter by **WS** (WebSocket)
3. Reload the page
4. Look for `ws` connection:
   - **Status 101** = Success
   - **Status 4xx/5xx** = Error

---

## Common Causes & Fixes

### Cause 1: Backend Not Running

**Symptom**: Connection refused, network error

**Fix**:
```bash
cd backend
python main.py
```

Verify backend is running:
```bash
curl http://localhost:8000/health
```

---

### Cause 2: Wrong WebSocket URL

**Symptom**: 404 Not Found, or connection immediately closes

**Check**: `app/App.tsx` line 25
```typescript
const WS_URL = 'ws://localhost:8000/ws';  // ✅ Correct
```

**Common mistakes**:
- `ws://localhost:8000` (missing `/ws`)
- `http://localhost:8000/ws` (http instead of ws)
- `wss://localhost:8000/ws` (wss for HTTPS only)

---

### Cause 3: CORS Issues

**Symptom**: Connection fails silently

**Check**: `backend/main.py` around line 166

Should have:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Verify CORS origins** in `backend/config/settings.py`:
```python
cors_origins: List[str] = [
    "http://localhost:3000",
    "http://localhost:5173",  # ✅ Must include Vite dev server
    "http://localhost:8080",
]
```

---

### Cause 4: Firewall/Antivirus Blocking

**Symptom**: Connection timeout

**Fix**:
1. Temporarily disable firewall
2. Add Python to allowed apps
3. Allow port 8000 inbound/outbound

**Windows Firewall**:
```bash
# Run as Administrator
netsh advfirewall firewall add rule name="Python 8000" dir=in action=allow protocol=TCP localport=8000
```

---

### Cause 5: Port Already in Use

**Symptom**: Backend fails to start, "Address already in use"

**Fix**:
```bash
# Windows - Find process on port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Then restart backend
python main.py
```

---

### Cause 6: Browser Clicking WS Link

**Symptom**: ERR_UNKNOWN_URL_SCHEME when clicking something

**Check**: Make sure there are no `<a href="ws://...">` links in your HTML

**Fix**: WebSocket URLs should only be used in JavaScript `new WebSocket(url)`, never in HTML links

---

## Updated Frontend Code

The WebSocket connection code has been improved with:

✅ **Better error handling**
✅ **Detailed console logging**
✅ **Component unmount protection**
✅ **Proper cleanup**

Check `app/App.tsx` lines 167-274 for the updated `useTradingEngine` hook.

---

## Verification Checklist

- [ ] Backend running: `curl http://localhost:8000/health`
- [ ] Frontend running: `http://localhost:5173` loads
- [ ] WS-TEST.html connects successfully
- [ ] Browser console shows `[WebSocket] ✅ Connected`
- [ ] Network tab shows WS connection with Status 101
- [ ] WebSocket connection status in UI shows "Connected" (green dot)

---

## Testing Commands

### Test 1: Backend Health
```bash
curl http://localhost:8000/health
```

### Test 2: Backend WebSocket (using Python)
```python
import asyncio
import websockets

async def test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        # Receive initial status
        msg = await ws.recv()
        print(f"Received: {msg}")

asyncio.run(test())
```

Save as `test_ws.py` and run:
```bash
cd backend
python test_ws.py
```

### Test 3: Start Bot via API
```bash
curl -X POST http://localhost:8000/api/bot/start
```

Then watch WebSocket messages in browser console!

---

## Backend Logs

Check backend logs for WebSocket activity:

```bash
# Real-time log watching (if backend is running)
tail -f backend/logs/goalshock.log

# Windows equivalent
Get-Content backend\logs\goalshock.log -Wait -Tail 50
```

Look for:
```
WebSocket client connected | active_connections=1
```

---

## Still Not Working?

### Check Backend Startup

When you run `python main.py`, you should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Check Frontend Build

```bash
cd app
npm run dev
```

Should show:
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### Nuclear Option: Clean Restart

```bash
# Stop everything
# Kill all Python and Node processes

# Backend
cd backend
rm -rf __pycache__ logs/*
python main.py

# Frontend (new terminal)
cd app
rm -rf node_modules .vite
npm install
npm run dev
```

---

## Expected Behavior (When Working)

1. **Backend starts**: Shows "Uvicorn running" message
2. **Frontend loads**: Vite dev server at localhost:5173
3. **Page loads**: Landing page appears
4. **Click "Launch Dashboard"**: Enters dashboard
5. **WebSocket connects automatically**: Within 1-2 seconds
6. **Console shows**: `[WebSocket] ✅ Connected successfully`
7. **UI shows**: Green dot next to "WebSocket: Connected"
8. **Click "Start Bot"**: Events start flowing
9. **Dashboard updates**: Real-time events appear

---

## Success Indicators

✅ Browser console: No red errors
✅ WebSocket status: Green "Connected"
✅ Network tab: WS connection with Status 101
✅ Backend logs: "WebSocket client connected"
✅ Events flowing when bot starts

---

## Getting Help

If none of the above works:

1. **Capture screenshots** of:
   - Browser console (F12)
   - Network tab (WS filter)
   - Backend terminal output

2. **Run WS-TEST.html** and capture result

3. **Check versions**:
   ```bash
   python --version  # Should be 3.10+
   node --version    # Should be 18+
   npm --version
   ```

4. **Share logs**:
   - `backend/logs/goalshock.log`
   - Browser console output
   - Backend terminal output

---

**Status**: Both cursor and WebSocket issues have been fixed!

**Next**: Test by running both backend and frontend, then check browser console for WebSocket connection logs.
