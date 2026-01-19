
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from engine_unified import UnifiedTradingEngine, EngineConfig, KEY_YES, KEY_NO, DEFAULT_MARKET_PRICE
from alphas.alpha_one_underdog import TradingMode

@pytest.fixture
def mock_dependencies():
    with patch('engine_unified.PolymarketClient') as mock_poly:
        yield {'poly': mock_poly}

@pytest.mark.asyncio
async def test_get_fixture_market_prices(mock_dependencies):
    config = EngineConfig(polymarket_key="test")
    # Patch the classes inside EngineConfig or UnifiedTradingEngine if needed,
    # but here we rely on mock_dependencies patching PolymarketClient at module level

    engine = UnifiedTradingEngine(config)
    # Ensure polymarket client is our mock (it should be since we patched the class init)
    engine.polymarket = mock_dependencies['poly'].return_value

    # Mock fixture object
    mock_fixture = MagicMock()
    mock_fixture.home_team = "TeamA"
    mock_fixture.away_team = "TeamB"
    mock_fixture.fixture_id = 100

    # Case 1: Success path
    mock_market = {"clobTokenIds": ["token123"], "id": "mkt1"}
    engine.polymarket.get_markets_by_event = AsyncMock(return_value=[mock_market])
    engine.polymarket.get_yes_price = AsyncMock(return_value=0.6)

    prices = await engine._get_fixture_market_prices(mock_fixture)
    assert prices[KEY_YES] == 0.6
    assert prices[KEY_NO] == pytest.approx(0.4)

    # Case 2: No markets found
    engine.polymarket.get_markets_by_event = AsyncMock(return_value=[])
    prices = await engine._get_fixture_market_prices(mock_fixture)
    assert prices[KEY_YES] == DEFAULT_MARKET_PRICE
    assert prices[KEY_NO] == DEFAULT_MARKET_PRICE

    # Case 3: Market found but no token ID
    mock_market_no_token = {"clobTokenIds": [None], "id": "mkt2"}
    engine.polymarket.get_markets_by_event = AsyncMock(return_value=[mock_market_no_token])
    prices = await engine._get_fixture_market_prices(mock_fixture)
    assert prices[KEY_YES] == DEFAULT_MARKET_PRICE

    # Case 4: Token ID found but no price
    engine.polymarket.get_markets_by_event = AsyncMock(return_value=[mock_market])
    engine.polymarket.get_yes_price = AsyncMock(return_value=None)
    prices = await engine._get_fixture_market_prices(mock_fixture)
    assert prices[KEY_YES] == DEFAULT_MARKET_PRICE

    # Case 5: Exception handling
    engine.polymarket.get_markets_by_event = AsyncMock(side_effect=Exception("API Error"))
    prices = await engine._get_fixture_market_prices(mock_fixture)
    assert prices[KEY_YES] == DEFAULT_MARKET_PRICE

    # Case 6: Polymarket not configured
    engine.polymarket = None
    prices = await engine._get_fixture_market_prices(mock_fixture)
    assert prices[KEY_YES] == DEFAULT_MARKET_PRICE
