import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from alphas.alpha_one_underdog import AlphaOneUnderdog, TradeSignal, TradingMode
from bot.websocket_goal_listener import GoalEventWS

# --- Constants ---
FIXTURE_ID = 1001
UNDERDOG_TEAM = "Underdog FC"
FAVORITE_TEAM = "Favorite United"
LEAGUE_ID = 39
LEAGUE_NAME = "Premier League"
# Default odds: Underdog @ 0.35, Favorite @ 0.65
DEFAULT_ODDS = {UNDERDOG_TEAM: 0.35, FAVORITE_TEAM: 0.65}

@pytest.fixture
def mock_clients():
    poly = MagicMock()
    poly.get_markets_by_event = AsyncMock(return_value=[])
    poly.get_yes_price = AsyncMock(return_value=0.40)
    poly.place_order = AsyncMock(return_value={"order_id": "12345"})

    kalshi = MagicMock()

    return poly, kalshi

@pytest.fixture
def alpha_one(mock_clients):
    poly, kalshi = mock_clients
    alpha = AlphaOneUnderdog(
        mode=TradingMode.SIMULATION,
        polymarket_client=poly,
        kalshi_client=kalshi
    )
    # Set default configuration for tests
    alpha.underdog_threshold = 0.45
    return alpha

@pytest_asyncio.fixture
async def setup_odds(alpha_one):
    """Fixture to cache default odds for the test fixture."""
    await alpha_one.cache_pre_match_odds(FIXTURE_ID, DEFAULT_ODDS)
    return alpha_one

@pytest.fixture
def goal_event_template():
    return GoalEventWS(
        fixture_id=FIXTURE_ID,
        league_id=LEAGUE_ID,
        league_name=LEAGUE_NAME,
        home_team=UNDERDOG_TEAM,
        away_team=FAVORITE_TEAM,
        team=UNDERDOG_TEAM,
        player="Striker",
        minute=15,
        home_score=0,
        away_score=0,
        goal_type="Normal",
        timestamp=datetime.now()
    )

@pytest.mark.asyncio
async def test_underdog_takes_lead_generates_signal(alpha_one, setup_odds, goal_event_template):
    """
    Test Happy Path: Underdog scores and takes the lead (1-0).
    Should generate a TradeSignal.
    """
    # Goal event: Underdog FC scores, making it 1-0
    goal_event = goal_event_template
    goal_event.team = UNDERDOG_TEAM
    goal_event.home_score = 1
    goal_event.away_score = 0
    goal_event.minute = 20

    # Mock current market price check to return valid price
    alpha_one._get_current_market_price = AsyncMock(return_value=0.42)

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is not None
    assert isinstance(signal, TradeSignal)
    assert signal.fixture_id == FIXTURE_ID
    assert signal.team == UNDERDOG_TEAM
    assert signal.side == "YES"
    assert signal.entry_price == 0.42
    assert signal.confidence > 0
    assert signal.size_usd > 0

    # Verify signal was logged in stats
    assert alpha_one.stats.total_signals == 1
    assert len(alpha_one.positions) == 1

@pytest.mark.parametrize("scenario_team, home_score, away_score, desc", [
    (FAVORITE_TEAM, 0, 1, "Favorite scores (0-1)"),
    (UNDERDOG_TEAM, 1, 2, "Underdog scores but losing (1-2)"),
    (UNDERDOG_TEAM, 1, 1, "Underdog scores equalizer (1-1)"),
])
@pytest.mark.asyncio
async def test_goal_scenarios_no_signal(alpha_one, setup_odds, goal_event_template, scenario_team, home_score, away_score, desc):
    """
    Test various goal scenarios where NO signal should be generated.
    """
    # Setup event
    goal_event = goal_event_template
    goal_event.team = scenario_team
    goal_event.home_score = home_score
    goal_event.away_score = away_score

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None, f"Signal generated incorrectly for scenario: {desc}"
    assert alpha_one.stats.total_signals == 0
    assert len(alpha_one.positions) == 0

@pytest.mark.asyncio
async def test_no_pre_match_odds_no_signal(alpha_one, goal_event_template):
    """
    Test Sad Path: No pre-match odds cached for this fixture.
    Should NOT generate a signal.
    """
    # Act - Don't cache odds (do not use setup_odds fixture)
    goal_event = goal_event_template
    goal_event.team = UNDERDOG_TEAM
    goal_event.home_score = 1
    goal_event.away_score = 0

    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None

@pytest.mark.asyncio
async def test_underdog_odds_too_high_no_signal(alpha_one, goal_event_template):
    """
    Test Sad Path: Underdog odds > threshold (not enough of an underdog).
    Should NOT generate a signal.
    """
    # Threshold is 0.45. Set odds to 0.48 (still technically underdog if other is 0.52, but above threshold)
    odds = {UNDERDOG_TEAM: 0.48, FAVORITE_TEAM: 0.52}
    await alpha_one.cache_pre_match_odds(FIXTURE_ID, odds)

    goal_event = goal_event_template
    goal_event.team = UNDERDOG_TEAM
    goal_event.home_score = 1
    goal_event.away_score = 0

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None

@pytest.mark.asyncio
async def test_max_positions_reached(alpha_one, setup_odds, goal_event_template):
    """
    Test Sad Path: Max positions reached.
    Should NOT generate a signal.
    """
    alpha_one._get_current_market_price = AsyncMock(return_value=0.42)

    # Fill positions
    alpha_one.max_positions = 1

    # Create a dummy position
    from alphas.alpha_one_underdog import SimulatedPosition
    dummy_signal = TradeSignal("dummy", 999, "Team", "YES", 0.5, 0.6, 0.4, 10, 0.8, "test")
    alpha_one.positions["dummy"] = SimulatedPosition("dummy", dummy_signal, datetime.now())

    goal_event = goal_event_template
    goal_event.team = UNDERDOG_TEAM
    goal_event.home_score = 1
    goal_event.away_score = 0

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None
