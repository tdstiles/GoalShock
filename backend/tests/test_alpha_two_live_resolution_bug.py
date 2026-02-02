
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from backend.alphas.alpha_two_late_compression import AlphaTwoLateCompression

@pytest.mark.asyncio
async def test_alpha_two_live_resolution_missing_bug():
    """
    Reproduction test for Bug: AlphaTwo Live Resolution Missing.
    Verifies that _check_market_resolution correctly queries the exchange
    in live mode (simulation_mode=False) and returns resolution details.
    """

    # 1. Setup Mock Client
    mock_poly = MagicMock()
    # We expect the strategy to call get_market
    mock_poly.get_market = AsyncMock()

    # Setup the mock return value for get_market
    # Simulating a resolved market response where "YES" won
    mock_poly.get_market.return_value = {
        "id": "market_123",
        "question": "Will Home Win?",
        "closed": True,
        "resolved": True,
        "outcome": "YES" # Assuming get_market returns a processed outcome
    }

    # 2. Initialize AlphaTwo in LIVE mode
    alpha = AlphaTwoLateCompression(
        polymarket_client=mock_poly,
        simulation_mode=False
    )

    # 3. Act: Check resolution for a market
    market_id = "market_123"

    resolution = await alpha._check_market_resolution(market_id)

    # 4. Assert
    # The bug is that resolution is None because the live branch is empty
    assert resolution is not None, "Resolution should not be None in Live Mode"
    assert resolution["outcome"] == "YES"

    # Verify the client was called
    mock_poly.get_market.assert_called_once_with(market_id)
