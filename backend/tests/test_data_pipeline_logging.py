import pytest
from backend.core.data_pipeline import DataAcquisitionLayer, PrimaryProviderUnavailableError
from unittest.mock import MagicMock, patch
import logging

@pytest.mark.asyncio
async def test_fetch_verified_goals_slow_warning(caplog):
    # Ensure we capture logs
    caplog.set_level(logging.WARNING)

    # Mock httpx.AsyncClient.get to be slow
    async def slow_response(*args, **kwargs):
        # Simulate delay without actually waiting to speed up test
        # We'll patch time.time instead
        return MagicMock(status_code=200, json=lambda: {"response": []})

    with patch("httpx.AsyncClient.get", side_effect=slow_response):
        with patch("time.time") as mock_time:

            # Use an iterator to control specific return values for time.time()
            # The code calls time.time() twice:
            # 1. start_time = time.time()
            # 2. duration = time.time() - start_time
            # Any logging calls might also call time.time() internally (e.g. for creating the LogRecord),
            # but usually we can control the flow.
            # We want duration > 1.0.
            # So let's return [1000, 1002, 1003, 1004...]

            # Using side_effect with a list/iterator
            mock_time.side_effect = [1000.0, 1002.0, 1003.0, 1004.0, 1005.0]

            dal = DataAcquisitionLayer()
            dal._api_football_key = "valid_key_long_enough_to_trigger_primary_mode"
            dal._srvc_mode = "primary"

            await dal._fetch_verified_goals()

            assert "Slow API response from API-Football" in caplog.text

@pytest.mark.asyncio
async def test_fetch_market_data_primary_error_does_not_fallback(caplog):
    caplog.set_level(logging.INFO)
    dal = DataAcquisitionLayer()
    dal._api_football_key = "valid_key"
    dal._polymarket_key = "valid_key"
    dal._srvc_mode = "primary"

    # Mock primary source failing
    with patch.object(dal, "_fetch_polymarket_data", side_effect=Exception("API Error")):
        with patch.object(dal, "_generate_market_data") as mock_generate:
            with pytest.raises(PrimaryProviderUnavailableError):
                await dal.fetch_market_data()

            mock_generate.assert_not_called()
            assert "synthetic fallback blocked in primary mode" in caplog.text

@pytest.mark.asyncio
async def test_error_logging_includes_context(caplog):
    dal = DataAcquisitionLayer()
    dal._api_football_key = "valid_key_long_enough_to_trigger_primary_mode"
    dal._srvc_mode = "primary"

    # Mock 500 error
    async def error_response(*args, **kwargs):
        return MagicMock(status_code=500, text="Internal Server Error")

    with patch("httpx.AsyncClient.get", side_effect=error_response):
        try:
            await dal._fetch_verified_goals()
        except Exception:
            pass

        # Check logs
        assert "API-Football error 500" in caplog.text
        assert "Internal Server Error" in caplog.text


@pytest.mark.asyncio
async def test_auxiliary_mode_logs_synthetic_by_design(caplog):
    caplog.set_level(logging.INFO)
    dal = DataAcquisitionLayer()
    dal._srvc_mode = "auxiliary"

    await dal.fetch_market_data()

    assert "Using synthetic market data by design" in caplog.text
