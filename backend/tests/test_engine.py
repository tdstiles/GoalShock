import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
try:
    from backend.engine import TradingEngine, GoalEvent, Position
    MODULE_PREFIX = "backend."
except ImportError:
    from engine import TradingEngine, GoalEvent, Position
    MODULE_PREFIX = ""

@pytest.fixture
def mock_dependencies():
    with patch(f"{MODULE_PREFIX}engine.PolymarketClient") as mock_poly, \
         patch(f"{MODULE_PREFIX}engine.KalshiClient") as mock_kalshi, \
         patch(f"{MODULE_PREFIX}engine.APIFootballClient") as mock_football:

        mock_poly.return_value = MagicMock()
        mock_kalshi.return_value = MagicMock()
        mock_football.return_value = MagicMock()

        yield {
            "poly": mock_poly,
            "kalshi": mock_kalshi,
            "football": mock_football
        }

@pytest.mark.asyncio
async def test_engine_initialization(mock_dependencies):
    """Test that the engine initializes with correct configuration."""
    engine = TradingEngine()

    assert engine.api_football is not None
    assert engine.polymarket is not None
    assert engine.kalshi is not None
    assert engine.running is False
    assert engine.positions == {}

@pytest.mark.asyncio
async def test_is_underdog_leading_validation(mock_dependencies):
    """Test the critical underdog leading validation logic."""
    engine = TradingEngine()

    # Mock fixture details
    mock_dependencies["football"].return_value.get_fixture_details = AsyncMock(return_value={
        "teams": {
            "home": {"name": "Underdog FC"},
            "away": {"name": "Favorite United"}
        }
    })

    # Case 1: Underdog Leading (1-0)
    goal_event_leading = GoalEvent(
        fixture_id=123,
        minute=85,
        team="Underdog FC",
        player="Striker",
        home_score=1,
        away_score=0,
        timestamp=None
    )

    assert await engine.is_underdog_leading(goal_event_leading, "Underdog FC") is True

    # Case 2: Tied (1-1)
    goal_event_tied = GoalEvent(
        fixture_id=123,
        minute=85,
        team="Underdog FC",
        player="Striker",
        home_score=1,
        away_score=1,
        timestamp=None
    )

    assert await engine.is_underdog_leading(goal_event_tied, "Underdog FC") is False

    # Case 3: Losing (1-2)
    goal_event_losing = GoalEvent(
        fixture_id=123,
        minute=85,
        team="Underdog FC",
        player="Striker",
        home_score=1,
        away_score=2,
        timestamp=None
    )

    assert await engine.is_underdog_leading(goal_event_losing, "Underdog FC") is False

@pytest.mark.asyncio
async def test_identify_pre_match_underdog(mock_dependencies):
    """Test underdog identification from odds."""
    engine = TradingEngine()

    # Mock fetch_pre_match_odds
    engine.fetch_pre_match_odds = AsyncMock(return_value={
        "Favorite United": 0.65,
        "Underdog FC": 0.35
    })

    underdog = await engine.identify_pre_match_underdog(123)
    assert underdog == "Underdog FC"
    assert engine.underdog_cache[123] == "Underdog FC"

    # Test cache hit
    engine.fetch_pre_match_odds.reset_mock()
    underdog_cached = await engine.identify_pre_match_underdog(123)
    assert underdog_cached == "Underdog FC"
    engine.fetch_pre_match_odds.assert_not_called()
