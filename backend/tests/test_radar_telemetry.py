from backend.engine_unified import UnifiedTradingEngine, EngineConfig, TradingMode
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from backend.bot.realtime_ingestor import RealtimeIngestor
from backend.bot.websocket_goal_listener import WebSocketGoalListener
from backend.bot.market_fetcher import MarketFetcher
from backend.data.api_football import APIFootballClient
from backend.main_realtime import websocket_live_feed


@pytest.mark.asyncio
async def test_main_realtime_websocket_logging_has_exc_info():
    with patch("backend.main_realtime.logger.error") as mock_logger:
        # Create a mock websocket that raises an exception when sending json
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("WS exception")

        await websocket_live_feed(mock_websocket)

        mock_logger.assert_called_with("WebSocket error: WS exception", exc_info=True)


@pytest.mark.asyncio
async def test_realtime_ingestor_logging_has_exc_info():
    ingestor = RealtimeIngestor()

    # Test _poll_live_matches error
    with patch("backend.bot.realtime_ingestor.logger.error") as mock_logger:
        with patch.object(ingestor, "_rate_limit", side_effect=Exception("Test error")):
            # Prevent infinite loop by setting running to False after exception
            async def patched_sleep(*args, **kwargs):
                ingestor.running = False

            with patch("asyncio.sleep", side_effect=patched_sleep):
                ingestor.running = True
                await ingestor._poll_live_matches()

        mock_logger.assert_called_with(
            "Error polling live matches: Test error", exc_info=True
        )

    # Test _fetch_live_fixtures error
    with patch("backend.bot.realtime_ingestor.logger.error") as mock_logger:
        ingestor.client.get = AsyncMock(side_effect=Exception("API error"))
        await ingestor._fetch_live_fixtures()
        mock_logger.assert_called_with(
            "Failed to fetch live fixtures: API error", exc_info=True
        )

    # Test _create_goal_event error
    with patch("backend.bot.realtime_ingestor.logger.error") as mock_logger:
        # Pass a mock that raises when .get() is called
        faulty_fixture_data = MagicMock()
        faulty_fixture_data.get.side_effect = Exception("Parse error")
        ingestor._create_goal_event(faulty_fixture_data, "Team A", "home")
        mock_logger.assert_called_with(
            "Failed to create goal event: Parse error", exc_info=True
        )

    # Test _notify_goal callback error
    with patch("backend.bot.realtime_ingestor.logger.error") as mock_logger:

        def failing_callback(goal):
            raise Exception("Callback failed")

        ingestor.register_goal_callback(failing_callback)

        # Mock goal
        mock_goal = MagicMock()
        mock_goal.player = "Player"
        mock_goal.team = "Team"
        mock_goal.minute = 10
        mock_goal.home_team = "Home"
        mock_goal.home_score = 1
        mock_goal.away_score = 0
        mock_goal.away_team = "Away"

        await ingestor._notify_goal(mock_goal)
        mock_logger.assert_called_with(
            "Goal callback error: Callback failed", exc_info=True
        )


@pytest.mark.asyncio
async def test_websocket_goal_listener_logging_has_exc_info():
    listener = WebSocketGoalListener()

    # Test _poll_cycle exception
    with patch("backend.bot.websocket_goal_listener.logger.error") as mock_logger:
        with patch.object(
            listener, "_poll_cycle", side_effect=Exception("Cycle error")
        ):
            # Break loop
            listener.running = True
            with patch(
                "asyncio.sleep",
                side_effect=lambda *a: setattr(listener, "running", False),
            ):
                await listener.start()
        mock_logger.assert_called_with(
            "Error in polling cycle: Cycle error", exc_info=True
        )

    # Test _notify_goal_callbacks exception
    with patch("backend.bot.websocket_goal_listener.logger.error") as mock_logger:

        def failing_callback(goal):
            raise Exception("Goal callback error")

        listener.register_goal_callback(failing_callback)
        await listener._notify_goal_callbacks(MagicMock())
        mock_logger.assert_called_with(
            "Goal callback error: Goal callback error", exc_info=True
        )

    # Test _notify_fixture_callbacks exception
    with patch("backend.bot.websocket_goal_listener.logger.error") as mock_logger:

        def failing_fixture_callback(fixtures):
            raise Exception("Fixture callback error")

        listener.register_fixture_callback(failing_fixture_callback)
        await listener._notify_fixture_callbacks([MagicMock()])
        mock_logger.assert_called_with(
            "Fixture callback error: Fixture callback error", exc_info=True
        )


@pytest.mark.asyncio
async def test_market_fetcher_logging_has_exc_info():
    fetcher = MarketFetcher()

    # Test _notify_update callback error
    with patch("backend.bot.market_fetcher.logger.error") as mock_logger:

        def failing_callback(update):
            raise Exception("Market callback failed")

        fetcher.register_update_callback(failing_callback)
        await fetcher._notify_update(MagicMock())
        mock_logger.assert_called_with(
            "Market callback error: Market callback failed", exc_info=True
        )


@pytest.mark.asyncio
async def test_api_football_logging_has_exc_info():
    client = APIFootballClient(api_key="test_key")

    # Test get_live_fixtures error
    with patch("backend.data.api_football.logger.error") as mock_logger:
        with patch("httpx.AsyncClient.get", side_effect=Exception("API GET error")):
            await client.get_live_fixtures()
        mock_logger.assert_called_with(
            "Error fetching live fixtures: API GET error", exc_info=True
        )

    # Test get_pre_match_odds error
    with patch("backend.data.api_football.logger.error") as mock_logger:
        with patch("httpx.AsyncClient.get", side_effect=Exception("Odds error")):
            await client.get_pre_match_odds(123)
        mock_logger.assert_called_with("Error fetching odds: Odds error", exc_info=True)

    # Test get_fixture_details error
    with patch("backend.data.api_football.logger.error") as mock_logger:
        with patch("httpx.AsyncClient.get", side_effect=Exception("Details error")):
            await client.get_fixture_details(123)
        mock_logger.assert_called_with(
            "Error fetching fixture details: Details error", exc_info=True
        )


@pytest.mark.asyncio
async def test_engine_unified_logging_has_exc_info():
    config = EngineConfig(mode=TradingMode.SIMULATION, enable_alpha_one=True, enable_alpha_two=True, enable_websocket=False, api_football_key="test", polymarket_key="test")
    engine = UnifiedTradingEngine(config)

    # Test _fetch_todays_fixtures error
    with patch("backend.engine_unified.logger.error") as mock_logger:
        engine.api_football = MagicMock()
        engine.api_football.get_live_fixtures = AsyncMock(side_effect=Exception("API error"))
        await engine._fetch_todays_fixtures()
        mock_logger.assert_called_with("Error fetching fixtures: API error", exc_info=True)

    # Test _pre_match_odds_loop error
    with patch("backend.engine_unified.logger.error") as mock_logger:
        with patch.object(engine, "_fetch_todays_fixtures", side_effect=Exception("Loop error")):
            # Break loop
            async def patched_sleep(*args, **kwargs):
                engine.running = False
            with patch("asyncio.sleep", side_effect=patched_sleep):
                engine.running = True
                await engine._pre_match_odds_loop()
        mock_logger.assert_called_with("Pre-match odds loop error: Loop error", exc_info=True)
