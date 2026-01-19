# Radar's Journal

## 2026-01-19 - Silent Failures in Data Acquisition
**Blindspot:** The `DataAcquisitionLayer` silently swallowed exceptions in `fetch_live_goals` and `fetch_market_data` when the primary data source failed, immediately falling back to synthetic data without any indication.
**Instrument:** Added structured logging (`logger.error` with `exc_info=True`) to the `except Exception` blocks in `backend/core/data_pipeline.py`.
**Metric:** Error logs now capture the specific exception and context when primary data fetching fails, allowing distinction between network errors, auth failures, and API changes.

## 2025-02-23 - Silent Failures in Market Price Fetching
**Blindspot:** The `UnifiedTradingEngine` silently swallows exceptions and returns default/fallback values when fetching market prices or pre-match odds from Polymarket and API-Football. This occurs in `_get_fixture_market_prices` (returns 0.5/0.5 on error) and `_fetch_pre_match_odds` (returns None on error).
**Instrument:** Added structured logging to catch `Exception` blocks in these methods. Logs will now report:
- Specific exceptions when API calls fail.
- Warnings when markets are not found or prices are missing (instead of just returning 0.5).
**Metric:** New logs with `logger.error` and `logger.warning` containing context (fixture info) will signal connectivity or data integrity issues that were previously invisible.

## 2026-01-19 - Latency Visibility in Data Acquisition
**Blindspot:** We had no visibility into how long external API calls to RapidAPI, Polymarket, or Kalshi were taking, nor specific details on failure status codes beyond "Exception".
**Instrument:** Wrapped `_fetch_verified_goals`, `_fetch_polymarket_data`, and `_fetch_kalshi_data` in `backend/core/data_pipeline.py` with timing logic and enhanced try/catch blocks.
**Metric:** Logs now include:
- `logger.warning` if an API call takes > 1.0 second.
- `logger.error` with specific HTTP status codes and response text snippets (first 200 chars) on failure.
- `logger.error` with total duration if a request raises an exception.
