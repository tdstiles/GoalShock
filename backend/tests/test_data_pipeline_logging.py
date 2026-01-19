
import pytest
import logging
from unittest.mock import Mock, patch, AsyncMock
from backend.core.data_pipeline import DataAcquisitionLayer

# Helper to capture logs
@pytest.fixture
def caplog_records(caplog):
    caplog.set_level(logging.INFO)
    return caplog.records

@pytest.mark.asyncio
async def test_fetch_verified_goals_logging(caplog):
    """Test that fetch_verified_goals logs warnings on slow requests."""

    with patch("backend.core.data_pipeline.httpx.AsyncClient") as MockClient:
        # Mock the client instance and its get method
        mock_client_instance = MockClient.return_value
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": []}

        # Simulate a slow response by sleeping inside the side_effect
        async def delayed_response(*args, **kwargs):
            import time
            time.sleep(1.1)
            return mock_response

        mock_client_instance.get = AsyncMock(side_effect=delayed_response)

        dal = DataAcquisitionLayer()
        # Force operational mode to primary to trigger the fetch
        dal._srvc_mode = "primary"

        caplog.set_level(logging.WARNING)

        await dal._fetch_verified_goals()

        # Check for the slow response warning
        assert any("Slow API response from API-Football" in record.message for record in caplog.records)

@pytest.mark.asyncio
async def test_fetch_verified_goals_error_logging(caplog):
    """Test that fetch_verified_goals logs errors with context."""

    with patch("backend.core.data_pipeline.httpx.AsyncClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client_instance.get = AsyncMock(return_value=mock_response)

        dal = DataAcquisitionLayer()
        caplog.set_level(logging.ERROR)

        with pytest.raises(Exception):
            await dal._fetch_verified_goals()

        # Check for the error log
        assert any("API-Football error 500" in record.message for record in caplog.records)
