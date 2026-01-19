
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from backend.core.orchestration_engine import OrchestrationEngine
from backend.core.data_pipeline import GoalEvent

# Define a fixture for the engine with mocked dependencies
@pytest.fixture
def orchestration_engine():
    # Patch the dependencies where they are imported in orchestration_engine.py
    # or patch the class instantiation inside __init__

    with patch("backend.core.orchestration_engine.DataAcquisitionLayer") as MockDAL, \
         patch("backend.core.orchestration_engine.StreamProcessor") as MockSP, \
         patch("backend.core.orchestration_engine.MarketMicrostructure") as MockMM:

        # Setup the mock instances
        mock_dal = MockDAL.return_value
        mock_sp = MockSP.return_value
        mock_mm = MockMM.return_value

        # Instantiate the engine
        engine = OrchestrationEngine()

        # Return the engine and the mocks for configuration/assertion in tests
        yield engine, mock_dal, mock_sp, mock_mm

@pytest.mark.asyncio
async def test_get_live_feed_success(orchestration_engine):
    engine, mock_dal, mock_sp, mock_mm = orchestration_engine

    # Arrange
    # 1. Mock fetch_live_goals
    mock_goals = [
        GoalEvent("match_1", "Team A", "Player 1", 10, datetime.now())
    ]
    mock_dal.fetch_live_goals = AsyncMock(return_value=mock_goals)

    # 2. Mock fetch_market_data
    mock_market_data = {
        "markets": [{"id": "m1", "question": "Q1"}]
    }
    mock_dal.fetch_market_data = AsyncMock(return_value=mock_market_data)

    # 3. Mock enrich_events
    mock_enriched_events = [
        {"id": "evt_1", "match_id": "match_1", "timestamp": "2024-01-01T12:00:00"}
    ]
    mock_sp.enrich_events = AsyncMock(return_value=mock_enriched_events)

    # 4. Mock aggregate_statistics
    mock_stats = {"total_goals": 1}
    mock_sp.aggregate_statistics = AsyncMock(return_value=mock_stats)

    # Act
    result = await engine.get_live_feed()

    # Assert
    assert result["events"] == mock_enriched_events
    assert result["markets"] == mock_market_data["markets"]
    assert result["statistics"] == mock_stats
    assert result["timestamp"] == "2024-01-01T12:00:00"

    mock_dal.fetch_live_goals.assert_awaited_once()
    mock_dal.fetch_market_data.assert_awaited_once()
    mock_sp.enrich_events.assert_awaited_once_with(mock_goals, mock_market_data)
    mock_sp.aggregate_statistics.assert_awaited_once_with(mock_enriched_events)

@pytest.mark.asyncio
async def test_get_live_feed_empty_events(orchestration_engine):
    engine, mock_dal, mock_sp, mock_mm = orchestration_engine

    # Arrange: No goals found
    mock_dal.fetch_live_goals = AsyncMock(return_value=[])
    mock_dal.fetch_market_data = AsyncMock(return_value={"markets": []})
    mock_sp.enrich_events = AsyncMock(return_value=[])
    mock_sp.aggregate_statistics = AsyncMock(return_value={"total_goals": 0})

    # Act
    result = await engine.get_live_feed()

    # Assert
    assert result["events"] == []
    assert result["timestamp"] is None

@pytest.mark.asyncio
async def test_get_market_details(orchestration_engine):
    engine, mock_dal, mock_sp, mock_mm = orchestration_engine

    # Arrange
    market_id = "market_123"
    mock_orderbook = {"mid_price": 0.5}
    # Using a list with one item to verify timestamp extraction logic
    mock_trade_history = [{"price": 0.5, "timestamp": "2024-01-01T12:00:00"}]

    mock_mm.synthesize_orderbook.return_value = mock_orderbook
    mock_mm.generate_trade_history.return_value = mock_trade_history

    # Act
    result = await engine.get_market_details(market_id)

    # Assert
    assert result["market_id"] == market_id
    assert result["orderbook"] == mock_orderbook
    assert result["recent_trades"] == mock_trade_history
    assert result["timestamp"] == "2024-01-01T12:00:00"

    mock_mm.synthesize_orderbook.assert_called_once_with(market_id)
    mock_mm.generate_trade_history.assert_called_once_with(market_id)

@pytest.mark.asyncio
async def test_get_portfolio_status(orchestration_engine):
    """
    Test get_portfolio_status.

    Note: The 'positions' and 'total_positions' are currently hardcoded in the implementation
    as synthetic demo data. This test verifies that the hardcoded data is returned correctly.
    If the implementation changes to fetch real positions, this test will need to be updated
    to mock that source.
    """
    engine, mock_dal, mock_sp, mock_mm = orchestration_engine

    # Arrange
    mock_pnl_history = [{"pnl": 1050.0}]
    mock_mm.generate_pnl_path.return_value = mock_pnl_history

    # Act
    result = await engine.get_portfolio_status()

    # Assert
    assert result["pnl_history"] == mock_pnl_history
    assert result["current_pnl"] == 1050.0

    # Verification of the hardcoded demo data
    assert "positions" in result
    assert len(result["positions"]) == 2
    assert result["total_positions"] == 2
    assert result["positions"][0]["market_id"] == "market_0"

    mock_mm.generate_pnl_path.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup(orchestration_engine):
    engine, mock_dal, mock_sp, mock_mm = orchestration_engine

    # Arrange
    mock_dal.close = AsyncMock()

    # Act
    await engine.cleanup()

    # Assert
    mock_dal.close.assert_awaited_once()
