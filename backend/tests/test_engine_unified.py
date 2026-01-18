import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.engine_unified import UnifiedTradingEngine, EngineConfig
from backend.alphas.alpha_one_underdog import TradingMode

@pytest.fixture
def mock_dependencies():
    with patch("backend.engine_unified.PolymarketClient") as mock_poly, \
         patch("backend.engine_unified.KalshiClient") as mock_kalshi, \
         patch("backend.engine_unified.APIFootballClient") as mock_football, \
         patch("backend.engine_unified.HybridGoalListener") as mock_listener, \
         patch("backend.engine_unified.AlphaOneUnderdog") as mock_alpha_one, \
         patch("backend.engine_unified.AlphaTwoLateCompression") as mock_alpha_two:

        mock_poly.return_value = MagicMock()
        mock_kalshi.return_value = MagicMock()
        mock_football.return_value = MagicMock()

        mock_listener_instance = AsyncMock()
        # Fix the RuntimeWarning by making register_goal_callback a proper Mock that returns something or is just a method
        mock_listener_instance.register_goal_callback = MagicMock()
        mock_listener.return_value = mock_listener_instance

        mock_alpha_one_instance = MagicMock()
        mock_alpha_one_instance.monitor_positions = AsyncMock()
        mock_alpha_one_instance.on_goal_event = AsyncMock()
        mock_alpha_one_instance.cache_pre_match_odds = AsyncMock()
        mock_alpha_one_instance.get_stats.return_value = MagicMock(total_trades=0, win_rate=0.0, total_pnl=0.0)
        mock_alpha_one.return_value = mock_alpha_one_instance

        mock_alpha_two_instance = MagicMock()
        mock_alpha_two_instance.start = AsyncMock()
        mock_alpha_two_instance.stop = AsyncMock()
        mock_alpha_two_instance.feed_live_fixture_update = AsyncMock()
        mock_alpha_two_instance.get_stats.return_value = MagicMock(trades_executed=0, win_rate=0.0, total_pnl=0.0)
        mock_alpha_two.return_value = mock_alpha_two_instance

        yield {
            "poly": mock_poly,
            "kalshi": mock_kalshi,
            "football": mock_football,
            "listener": mock_listener,
            "alpha_one": mock_alpha_one,
            "alpha_two": mock_alpha_two
        }

@pytest.mark.asyncio
async def test_engine_initialization(mock_dependencies):
    """Test that the engine initializes with correct configuration."""
    config = EngineConfig(
        mode=TradingMode.SIMULATION,
        enable_alpha_one=True,
        enable_alpha_two=True,
        enable_websocket=True,
        api_football_key="test_key"
    )

    engine = UnifiedTradingEngine(config)

    assert engine.config.mode == TradingMode.SIMULATION
    assert engine.config.enable_alpha_one is True
    assert engine.config.enable_alpha_two is True
    assert engine.config.enable_websocket is True

    assert engine.alpha_one is not None
    assert engine.alpha_two is not None
    assert engine.goal_listener is not None

@pytest.mark.asyncio
async def test_engine_start_stop(mock_dependencies):
    """Test that the engine starts and stops components correctly."""
    config = EngineConfig(
        mode=TradingMode.SIMULATION,
        enable_alpha_one=True,
        enable_alpha_two=True,
        enable_websocket=True,
        api_football_key="test_key"
    )

    engine = UnifiedTradingEngine(config)

    # Run start in a separate task and cancel it after a short delay
    task = asyncio.create_task(engine.start())

    await asyncio.sleep(0.1)
    await engine.stop()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_dependencies["listener"].return_value.start.assert_called()
    mock_dependencies["alpha_one"].return_value.monitor_positions.assert_called()
    mock_dependencies["alpha_two"].return_value.start.assert_called()
