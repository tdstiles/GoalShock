
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.engine_unified import UnifiedTradingEngine, DEFAULT_MARKET_PRICE, KEY_YES, KEY_NO
from backend.exchanges.polymarket import PolymarketClient

# Mock LiveFixture
class MockLiveFixture:
    def __init__(self, home, away):
        self.home_team = home
        self.away_team = away
        self.fixture_id = 12345
        self.home_score = 0
        self.away_score = 0
        self.minute = 10
        self.status = "1H"

@pytest.fixture
def engine():
    eng = UnifiedTradingEngine()
    eng.polymarket = PolymarketClient()
    eng.polymarket.get_yes_price = AsyncMock(return_value=0.75) # Mock price fetch
    return eng

@pytest.mark.asyncio
async def test_search_primary_success(engine):
    """
    Case 1: Primary search "Home vs Away" succeeds.
    Verify that the API is called only once.
    """
    mock_markets = [{"id": "m1", "clobTokenIds": ["t1"]}]
    engine.polymarket.get_markets_by_event = AsyncMock(return_value=mock_markets)

    fixture = MockLiveFixture("Home", "Away")
    prices = await engine._get_fixture_market_prices(fixture)

    assert prices[KEY_YES] == 0.75
    assert engine.polymarket.get_markets_by_event.call_count == 1
    engine.polymarket.get_markets_by_event.assert_called_with("Home vs Away")

@pytest.mark.asyncio
async def test_search_fallback_success(engine):
    """
    Case 2: Primary search fails, Secondary "Away vs Home" succeeds.
    Verify that the API is called twice, and the second one works.
    """
    mock_markets = [{"id": "m1", "clobTokenIds": ["t1"]}]

    async def side_effect(event_name):
        if event_name == "Home vs Away":
            return []
        if event_name == "Away vs Home":
            return mock_markets
        return []

    engine.polymarket.get_markets_by_event = AsyncMock(side_effect=side_effect)

    fixture = MockLiveFixture("Home", "Away")
    prices = await engine._get_fixture_market_prices(fixture)

    assert prices[KEY_YES] == 0.75
    assert engine.polymarket.get_markets_by_event.call_count == 2
    # Check calls
    calls = engine.polymarket.get_markets_by_event.call_args_list
    assert calls[0][0][0] == "Home vs Away"
    assert calls[1][0][0] == "Away vs Home"

@pytest.mark.asyncio
async def test_search_both_fail(engine):
    """
    Case 3: Both searches fail.
    Verify that it returns default prices.
    """
    engine.polymarket.get_markets_by_event = AsyncMock(return_value=[])

    fixture = MockLiveFixture("Home", "Away")
    prices = await engine._get_fixture_market_prices(fixture)

    assert prices[KEY_YES] == DEFAULT_MARKET_PRICE
    assert prices[KEY_NO] == DEFAULT_MARKET_PRICE
    assert engine.polymarket.get_markets_by_event.call_count == 2
