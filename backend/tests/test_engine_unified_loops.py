
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from engine_unified import UnifiedTradingEngine, EngineConfig

@pytest.fixture
def mock_dependencies():
    with patch('engine_unified.PolymarketClient') as mock_poly, \
         patch('engine_unified.KalshiClient') as mock_kalshi, \
         patch('engine_unified.APIFootballClient') as mock_api, \
         patch('engine_unified.AlphaOneUnderdog') as mock_alpha1, \
         patch('engine_unified.AlphaTwoLateCompression') as mock_alpha2:

        # Setup basic async mocks
        mock_api.return_value.get_live_fixtures = AsyncMock(return_value=[])
        mock_api.return_value.get_pre_match_odds = AsyncMock(return_value={})

        mock_alpha1.return_value.cache_pre_match_odds = AsyncMock()
        mock_alpha2.return_value.feed_live_fixture_update = AsyncMock()

        yield {
            'api': mock_api,
            'alpha1': mock_alpha1,
            'alpha2': mock_alpha2,
            'poly': mock_poly
        }

@pytest.mark.asyncio
async def test_pre_match_odds_loop_happy_path(mock_dependencies):
    """
    Test that _pre_match_odds_loop fetches fixtures and caches odds.
    Verifies the data flow from API -> Engine -> Alpha One.
    """
    api = mock_dependencies['api'].return_value
    alpha1 = mock_dependencies['alpha1'].return_value

    # Setup mock data (Fixtures are objects, not dicts, coming from API client)
    mock_fixture = MagicMock()
    mock_fixture.fixture_id = 100
    api.get_live_fixtures.return_value = [mock_fixture]

    # Setup odds response
    api.get_pre_match_odds.return_value = {"TeamA": 0.5, "TeamB": 0.5}

    config = EngineConfig(enable_alpha_one=True, api_football_key="test_key")
    engine = UnifiedTradingEngine(config)
    engine.running = True

    # We want the loop to run exactly once, then stop.
    # We patch asyncio.sleep to set running=False as a side effect.
    async def side_effect_sleep(*args, **kwargs):
        engine.running = False
        return None

    with patch('asyncio.sleep', side_effect=side_effect_sleep):
        await engine._pre_match_odds_loop()

    # Verification
    api.get_live_fixtures.assert_awaited_once()
    # It should call get_pre_match_odds for fixture 100
    api.get_pre_match_odds.assert_awaited_once_with(100)
    # It should cache the odds in Alpha One
    alpha1.cache_pre_match_odds.assert_awaited_once_with(100, {"TeamA": 0.5, "TeamB": 0.5})

@pytest.mark.asyncio
async def test_pre_match_odds_loop_error_handling(mock_dependencies):
    """
    Test that the loop catches exceptions from the API and continues execution
    (does not crash the engine). This simulates a network failure.
    """
    api = mock_dependencies['api'].return_value

    # Setup error: API raises an exception
    api.get_live_fixtures.side_effect = Exception("API Connection Failed")

    config = EngineConfig(enable_alpha_one=True, api_football_key="test_key")
    engine = UnifiedTradingEngine(config)
    engine.running = True

    # Run once then stop
    async def side_effect_sleep(*args, **kwargs):
        engine.running = False
        return None

    with patch('asyncio.sleep', side_effect=side_effect_sleep), \
         patch('engine_unified.logger') as mock_logger:

        await engine._pre_match_odds_loop()

        # Should have logged an error
        mock_logger.error.assert_called()
        # Should NOT have crashed (test finishes successfully)

@pytest.mark.asyncio
async def test_on_fixture_update_logic(mock_dependencies):
    """
    Test the core logic of processing fixture updates via the new callback method.
    """
    alpha2 = mock_dependencies['alpha2'].return_value

    mock_fixture = MagicMock()
    mock_fixture.fixture_id = 200
    mock_fixture.home_team = "Home FC"
    mock_fixture.away_team = "Away FC"
    mock_fixture.home_score = 1
    mock_fixture.away_score = 0
    mock_fixture.minute = 88
    mock_fixture.status = "2H"

    config = EngineConfig(enable_alpha_two=True, api_football_key="test_key", polymarket_key="poly_key")
    engine = UnifiedTradingEngine(config)

    mock_prices = {"yes": 0.8, "no": 0.2}

    with patch.object(engine, '_get_fixture_market_prices', new_callable=AsyncMock) as mock_get_prices:
        mock_get_prices.return_value = mock_prices

        # Call the method directly with a list of fixtures
        await engine._on_fixture_update([mock_fixture])

        # Verify Interactions
        mock_get_prices.assert_awaited_once_with(mock_fixture)

        # Check that alpha_two feed was called with enriched data
        alpha2.feed_live_fixture_update.assert_awaited_once()
        call_args = alpha2.feed_live_fixture_update.call_args[0][0]

        assert call_args['fixture_id'] == 200
        assert call_args['yes_price'] == 0.8
        assert call_args['minute'] == 88
        assert call_args['home_team'] == "Home FC"

@pytest.mark.asyncio
async def test_live_fixture_loop_fallback(mock_dependencies):
    """
    Test the fallback loop logic when goal_listener is disabled.
    """
    api = mock_dependencies['api'].return_value
    alpha2 = mock_dependencies['alpha2'].return_value

    mock_fixture = MagicMock()
    mock_fixture.fixture_id = 300
    api.get_live_fixtures.return_value = [mock_fixture]

    # Initialize with NO websocket to trigger fallback logic if we were testing start()
    # But here we test the loop method directly.
    config = EngineConfig(enable_alpha_two=True, api_football_key="test_key", polymarket_key="poly_key", enable_websocket=False)
    engine = UnifiedTradingEngine(config)
    engine.running = True

    mock_prices = {"yes": 0.5, "no": 0.5}

    async def side_effect_sleep(*args, **kwargs):
        engine.running = False
        return None

    with patch.object(engine, '_get_fixture_market_prices', new_callable=AsyncMock) as mock_get_prices, \
         patch('asyncio.sleep', side_effect=side_effect_sleep):

        mock_get_prices.return_value = mock_prices

        await engine._live_fixture_loop()

        # Verify Interactions
        api.get_live_fixtures.assert_awaited_once()
        # Ensure it called the update handler (which calls get_prices)
        mock_get_prices.assert_awaited_once_with(mock_fixture)
        alpha2.feed_live_fixture_update.assert_awaited_once()

@pytest.mark.asyncio
async def test_on_fixture_update_partial_failure(mock_dependencies):
    """
    Test resilience: If one fixture fails to process (e.g., pricing error),
    the method should continue to the next one (if implemented with inner try/except).
    """
    # Create two fixtures
    fixture1 = MagicMock()
    fixture1.fixture_id = 301
    fixture2 = MagicMock()
    fixture2.fixture_id = 302

    fixtures = [fixture1, fixture2]

    config = EngineConfig(enable_alpha_two=True, api_football_key="test_key")
    engine = UnifiedTradingEngine(config)

    # Make the first one fail, second one succeed
    async def get_prices_side_effect(fixture):
        if fixture.fixture_id == 301:
            raise Exception("Price Error")
        return {"yes": 0.5, "no": 0.5}

    with patch.object(engine, '_get_fixture_market_prices', side_effect=get_prices_side_effect), \
         patch('engine_unified.logger') as mock_logger:

        # Logic under test: _on_fixture_update iterates fixtures
        await engine._on_fixture_update(fixtures)

        # First failure should be logged
        assert mock_logger.error.call_count >= 1

        # Second fixture should still be processed (implied if we reach here and check calls,
        # but only if _on_fixture_update has inner try/except block inside the loop)

        # Verify alpha2 received update for fixture2 only
        alpha2 = mock_dependencies['alpha2'].return_value
        alpha2.feed_live_fixture_update.assert_awaited_once()
        call_args = alpha2.feed_live_fixture_update.call_args[0][0]
        assert call_args['fixture_id'] == 302
