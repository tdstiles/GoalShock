# Legacy Headless Engine

GoalShock originally shipped as a terminal-only "headless" engine that runs without the web UI or real-time API server. This mode is kept for users who want a lightweight, CLI-driven process that logs trading decisions to stdout and relies on environment variables for configuration.

The headless engine is **legacy** because the recommended entry point is the unified engine plus optional UI components. However, the command-line workflow is still useful for automation, servers without a browser, or lightweight testing.

## How It Works

The legacy headless mode runs the unified trading engine directly (`backend/engine_unified.py`). It:

- polls and/or listens for live match events,
- evaluates Alpha One (Underdog Momentum) and Alpha Two (Late-Stage Compression),
- places simulated or live trades based on configuration,
- prints all operational logs to your terminal.

## Running the Headless Engine

From the repository root:

```bash
cd backend
cp .env.example .env
# Edit .env and add your API_FOOTBALL_KEY and exchange keys (optional for simulation)
```

Run in simulation mode (safe):

```bash
python engine_unified.py --mode simulation
```

Run in live mode (real money):

```bash
python engine_unified.py --mode live
```

### Optional Environment Toggles

You can disable specific strategies or the goal listener with environment variables in `.env`:

```bash
ENABLE_ALPHA_ONE=false
ENABLE_ALPHA_TWO=false
ENABLE_WEBSOCKET=false
```

## Notes

- Simulation mode does not place live orders; it logs intended actions instead.
- Live mode requires valid API keys for the target exchange(s).
- For a more full-featured experience (real-time UI, API), use the unified engine with the front-end components.
