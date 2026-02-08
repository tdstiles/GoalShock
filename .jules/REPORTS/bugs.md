# 🐕 Hound: Bug Recon <2026-02-05>

## 1. Critical: Primary-data failures silently fall back to synthetic events and markets (FIXED)
- **Location:** `backend/core/data_pipeline.py` (`fetch_live_goals`, `fetch_market_data`)
- **Impact:** **High**
- **Likelihood:** **High**
- **Why this is a bug:**
  In `primary` mode, both methods catch all exceptions from real providers and unconditionally return generated synthetic data. This creates a silent data-integrity failure: consumers cannot distinguish real failures from healthy data flow, and downstream logic may trade or report analytics on fabricated inputs.
- **How to reproduce (if known):**
  Configure valid provider keys so `_srvc_mode == "primary"`, then force API failures (bad DNS/network outage). Calls to `fetch_live_goals()` / `fetch_market_data()` still succeed with synthetic payloads instead of surfacing an error state.
- **Suggested owner:** Sentinel
- **Resolution:** Validated via `backend/tests/core/test_data_pipeline.py`. Code now raises `PrimaryProviderUnavailableError` correctly.

## 2. High: Kalshi client continues API calls after failed login and sends `Bearer None` (FIXED)
- **Location:** `backend/exchanges/kalshi.py` (`get_markets`, `get_orderbook`, `place_order`)
- **Impact:** **High**
- **Likelihood:** **Medium**
- **Why this is a bug:**
  These methods call `await self.login()` when no token exists, but they ignore the boolean result. If auth fails, execution continues and sends requests with `Authorization: Bearer None`, causing noisy unauthorized traffic and masking root cause. It also prevents clean retry/backoff behavior.
- **How to reproduce (if known):**
  Set invalid `KALSHI_API_KEY` / `KALSHI_API_SECRET` and call `get_orderbook()`. `login()` returns `False`, but request is still sent with a null token header.
- **Suggested owner:** Bolt
- **Resolution:** Validated via `backend/tests/exchanges/test_kalshi_client.py`. Code now checks `if not await self._ensure_authenticated(): return` and handles failed login gracefully.

## 3. Medium: Valid `yes_price=0.0` is treated as missing market data (FIXED)
- **Location:** `backend/engine_unified.py` (`_get_fixture_market_prices`, `if yes_price:`)
- **Impact:** **Medium**
- **Likelihood:** **Low**
- **Why this is a bug:**
  The code checks truthiness (`if yes_price`) instead of explicit `None`/range validation. A legitimate edge price of `0.0` is falsy, so it is discarded and replaced with invalid defaults. This can suppress valid signals near market resolution.
- **How to reproduce (if known):**
  Stub `polymarket.get_yes_price()` to return `0.0`. `_get_fixture_market_prices()` returns `{yes: -1.0, no: -1.0}` instead of `{yes: 0.0, no: 1.0}`.
- **Suggested owner:** Sherlock

## 4. Medium: CLI flags cannot disable Alpha strategies (FIXED)
- **Location:** `backend/engine_unified.py` (`argparse` config for `--alpha-one` and `--alpha-two`)
- **Impact:** **Medium**
- **Likelihood:** **High**
- **Why this is a bug:**
  Both flags are declared with `action="store_true"` and `default=True`. That means they are always `True`, whether the flag is passed or not. Operators cannot disable either strategy via CLI, and env-driven config gets overwritten.
- **How to reproduce (if known):**
  Run with no strategy flags (or with environment variable `ENABLE_ALPHA_ONE=false`): parsed args still set `alpha_one=True` and `alpha_two=True`.
- **Suggested owner:** Sherlock
- **Resolution:** Validated via `backend/tests/test_engine_unified.py`. Code now uses `argparse.BooleanOptionalAction` with `default=None`, correctly respecting environment variables and allowing CLI overrides (`--no-alpha-one`).
