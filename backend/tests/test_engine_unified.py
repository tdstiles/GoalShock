import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from engine_unified import (
    UnifiedTradingEngine,
    EngineConfig,
    parse_cli_args,
    build_engine_config_from_cli_args,
)
from bot.websocket_goal_listener import GoalEventWS
from alphas.alpha_one_underdog import TradingMode


@pytest.fixture
def mock_goal_event():
    return GoalEventWS(
        fixture_id=123,
        league_id=39,
        league_name="Premier League",
        home_team="Home Team",
        away_team="Away Team",
        team="Home Team",
        player="Player One",
        minute=30,
        home_score=1,
        away_score=0,
        goal_type="Normal",
        timestamp=datetime.now(),
    )


@pytest.fixture
def mock_dependencies():
    with patch("engine_unified.PolymarketClient") as mock_poly, patch(
        "engine_unified.KalshiClient"
    ) as mock_kalshi, patch("engine_unified.APIFootballClient") as mock_api, patch(
        "engine_unified.WebSocketGoalListener"
    ) as mock_ws, patch(
        "engine_unified.HybridGoalListener"
    ) as mock_hybrid, patch(
        "engine_unified.AlphaOneUnderdog"
    ) as mock_alpha1, patch(
        "engine_unified.AlphaTwoLateCompression"
    ) as mock_alpha2:

        # Setup AsyncMocks for async methods
        mock_alpha1.return_value.on_goal_event = AsyncMock(
            return_value=MagicMock(signal_id="sig1")
        )
        mock_alpha1.return_value.monitor_positions = AsyncMock()
        mock_alpha2.return_value.feed_live_fixture_update = AsyncMock()
        mock_alpha2.return_value.start = AsyncMock()
        mock_alpha2.return_value.stop = AsyncMock()
        mock_hybrid.return_value.start = AsyncMock()
        mock_hybrid.return_value.stop = AsyncMock()

        yield {
            "poly": mock_poly,
            "kalshi": mock_kalshi,
            "api": mock_api,
            "ws": mock_ws,
            "hybrid": mock_hybrid,
            "alpha1": mock_alpha1,
            "alpha2": mock_alpha2,
        }


def test_engine_config_defaults():
    config = EngineConfig()
    assert config.mode == TradingMode.SIMULATION
    assert config.enable_alpha_one is True
    assert config.enable_alpha_two is True


def test_engine_config_from_env():
    with patch.dict(
        "os.environ",
        {
            "TRADING_MODE": "live",
            "ENABLE_ALPHA_ONE": "false",
            "API_FOOTBALL_KEY": "test_key",
        },
    ):
        config = EngineConfig.from_env()
        assert config.mode == TradingMode.LIVE
        assert config.enable_alpha_one is False
        assert config.api_football_key == "test_key"


def test_cli_strategy_defaults_follow_environment():
    with patch.dict(
        "os.environ",
        {
            "ENABLE_ALPHA_ONE": "false",
            "ENABLE_ALPHA_TWO": "true",
            "ENABLE_WEBSOCKET": "false",
            "TRADING_MODE": "live",
        },
        clear=False,
    ):
        args = parse_cli_args([])
        config = build_engine_config_from_cli_args(args)

    assert config.enable_alpha_one is False
    assert config.enable_alpha_two is True
    assert config.enable_websocket is False
    assert config.mode == TradingMode.LIVE


def test_cli_can_explicitly_enable_and_disable_each_strategy():
    with patch.dict(
        "os.environ",
        {
            "ENABLE_ALPHA_ONE": "false",
            "ENABLE_ALPHA_TWO": "true",
        },
        clear=False,
    ):
        args = parse_cli_args(["--alpha-one", "--no-alpha-two"])
        config = build_engine_config_from_cli_args(args)

    assert config.enable_alpha_one is True
    assert config.enable_alpha_two is False


def test_cli_disable_alpha_one_and_enable_alpha_two_overrides_environment():
    with patch.dict(
        "os.environ",
        {
            "ENABLE_ALPHA_ONE": "true",
            "ENABLE_ALPHA_TWO": "false",
        },
        clear=False,
    ):
        args = parse_cli_args(["--no-alpha-one", "--alpha-two"])
        config = build_engine_config_from_cli_args(args)

    assert config.enable_alpha_one is False
    assert config.enable_alpha_two is True


@pytest.mark.asyncio
async def test_engine_initialization(mock_dependencies):
    config = EngineConfig(
        mode=TradingMode.SIMULATION,
        enable_alpha_one=True,
        enable_alpha_two=True,
        enable_websocket=True,
        api_football_key="key",
        polymarket_key="key",
    )

    engine = UnifiedTradingEngine(config)

    assert engine.polymarket is not None
    assert engine.alpha_one is not None
    assert engine.alpha_two is not None

    # Verify Alpha One initialized with correct clients
    mock_dependencies["alpha1"].assert_called_once()
    mock_dependencies["alpha2"].assert_called_once()


@pytest.mark.asyncio
async def test_on_goal_event_propagation(mock_dependencies, mock_goal_event):
    """
    Critical Test: Ensure goal events trigger alpha strategies.
    This protects the core reactor loop.
    """
    config = EngineConfig(
        mode=TradingMode.SIMULATION, enable_alpha_one=True, enable_alpha_two=True
    )
    engine = UnifiedTradingEngine(config)

    # Simulate a goal event
    await engine._on_goal_event(mock_goal_event)

    # Assertions
    assert engine.goals_processed == 1
    assert engine.signals_generated == 1

    # Check Alpha One received the event
    engine.alpha_one.on_goal_event.assert_awaited_once_with(mock_goal_event)

    # Check Alpha Two received the update
    # We verify the structure of the data passed to Alpha Two
    call_args = engine.alpha_two.feed_live_fixture_update.call_args
    assert call_args is not None
    fixture_data = call_args[0][0]

    assert fixture_data["fixture_id"] == 123
    assert fixture_data["home_team"] == "Home Team"
    assert fixture_data["home_score"] == 1
    assert fixture_data["status"] == "1H"  # Minute 30 is 1H


@pytest.mark.asyncio
async def test_engine_start_stop(mock_dependencies):
    """Test the main loop startup and shutdown sequences."""
    config = EngineConfig(
        enable_websocket=False
    )  # Disable WS to avoid needing that mock
    engine = UnifiedTradingEngine(config)

    # Use an Event to signal when the loop has started running
    loop_started = asyncio.Event()

    async def run_until_stopped(*args, **kwargs):
        loop_started.set()
        try:
            # Important: Check engine.running, just like the real loop would
            while engine.running:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    # Mock the infinite loops to return immediately or raise CancelledError
    with patch.object(
        engine, "_pre_match_odds_loop", new_callable=AsyncMock
    ) as mock_loop1, patch.object(
        engine, "_live_fixture_loop", new_callable=AsyncMock
    ) as mock_loop2, patch.object(
        engine, "_stats_reporter_loop", side_effect=run_until_stopped
    ) as mock_loop3:

        # We start the engine in a background task so we can stop it
        start_task = asyncio.create_task(engine.start())

        # Wait for the loop to start
        try:
            await asyncio.wait_for(loop_started.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("Engine failed to start loop in time")

        assert engine.running is True

        await engine.stop()

        # Wait for start task to finish
        try:
            await asyncio.wait_for(start_task, timeout=2.0)
        except asyncio.TimeoutError:
            start_task.cancel()
            pytest.fail("Engine start task failed to return after stop()")

        assert engine.running is False
