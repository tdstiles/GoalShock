import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from alphas.alpha_one_underdog import AlphaOneUnderdog, TradeSignal, TradingMode
from bot.websocket_goal_listener import GoalEventWS

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

@pytest.fixture
def goal_event_template():
    return GoalEventWS(
        fixture_id=1001,
        league_id=39,
        league_name="Premier League",
        home_team="Underdog FC",
        away_team="Favorite United",
        team="Underdog FC",
        player="Striker",
        minute=15,
        home_score=0,
        away_score=0,
        goal_type="Normal",
        timestamp=datetime.now()
    )

@pytest.mark.asyncio
async def test_underdog_takes_lead_generates_signal(alpha_one, goal_event_template):
    """
    Test Happy Path: Underdog scores and takes the lead (1-0).
    Should generate a TradeSignal.
    """
    fixture_id = 1001
    # Setup pre-match odds: Underdog FC @ 0.35 (Underdog), Favorite United @ 0.65
    odds = {"Underdog FC": 0.35, "Favorite United": 0.65}
    await alpha_one.cache_pre_match_odds(fixture_id, odds)

    # Goal event: Underdog FC scores, making it 1-0
    goal_event = goal_event_template
    goal_event.team = "Underdog FC"
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
    assert signal.fixture_id == fixture_id
    assert signal.team == "Underdog FC"
    assert signal.side == "YES"
    assert signal.entry_price == 0.42
    assert signal.confidence > 0
    assert signal.size_usd > 0

    # Verify signal was logged in stats
    assert alpha_one.stats.total_signals == 1
    assert len(alpha_one.positions) == 1

@pytest.mark.asyncio
async def test_favorite_scores_no_signal(alpha_one, goal_event_template):
    """
    Test Sad Path: Favorite scores.
    Should NOT generate a signal.
    """
    fixture_id = 1001
    odds = {"Underdog FC": 0.35, "Favorite United": 0.65}
    await alpha_one.cache_pre_match_odds(fixture_id, odds)

    # Goal event: Favorite United scores, making it 0-1
    goal_event = goal_event_template
    goal_event.team = "Favorite United"
    goal_event.home_score = 0
    goal_event.away_score = 1

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None
    assert alpha_one.stats.total_signals == 0
    assert len(alpha_one.positions) == 0

@pytest.mark.asyncio
async def test_underdog_scores_but_losing_no_signal(alpha_one, goal_event_template):
    """
    Test Sad Path: Underdog scores but is still losing (e.g. 1-2).
    Should NOT generate a signal.
    """
    fixture_id = 1001
    odds = {"Underdog FC": 0.35, "Favorite United": 0.65}
    await alpha_one.cache_pre_match_odds(fixture_id, odds)

    # Goal event: Underdog FC scores, but score becomes 1-2 (still losing)
    goal_event = goal_event_template
    goal_event.team = "Underdog FC"
    goal_event.home_score = 1
    goal_event.away_score = 2

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None
    assert alpha_one.stats.total_signals == 0

@pytest.mark.asyncio
async def test_underdog_scores_equalizer_no_signal(alpha_one, goal_event_template):
    """
    Test Sad Path: Underdog scores to equalize (1-1).
    Should NOT generate a signal (must be LEADING).
    """
    fixture_id = 1001
    odds = {"Underdog FC": 0.35, "Favorite United": 0.65}
    await alpha_one.cache_pre_match_odds(fixture_id, odds)

    # Goal event: Underdog FC scores, making it 1-1
    goal_event = goal_event_template
    goal_event.team = "Underdog FC"
    goal_event.home_score = 1
    goal_event.away_score = 1

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None

@pytest.mark.asyncio
async def test_no_pre_match_odds_no_signal(alpha_one, goal_event_template):
    """
    Test Sad Path: No pre-match odds cached for this fixture.
    Should NOT generate a signal.
    """
    # Act - Don't cache odds
    goal_event = goal_event_template
    goal_event.team = "Underdog FC"
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
    fixture_id = 1001
    # Threshold is 0.45. Set odds to 0.48 (still technically underdog if other is 0.52, but above threshold)
    odds = {"Underdog FC": 0.48, "Favorite United": 0.52}
    await alpha_one.cache_pre_match_odds(fixture_id, odds)

    goal_event = goal_event_template
    goal_event.team = "Underdog FC"
    goal_event.home_score = 1
    goal_event.away_score = 0

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None

@pytest.mark.asyncio
async def test_max_positions_reached(alpha_one, goal_event_template):
    """
    Test Sad Path: Max positions reached.
    Should NOT generate a signal.
    """
    fixture_id = 1001
    odds = {"Underdog FC": 0.35, "Favorite United": 0.65}
    await alpha_one.cache_pre_match_odds(fixture_id, odds)
    alpha_one._get_current_market_price = AsyncMock(return_value=0.42)

    # Fill positions
    alpha_one.max_positions = 1

    # Create a dummy position
    from alphas.alpha_one_underdog import SimulatedPosition
    dummy_signal = TradeSignal("dummy", 999, "Team", "YES", 0.5, 0.6, 0.4, 10, 0.8, "test")
    alpha_one.positions["dummy"] = SimulatedPosition("dummy", dummy_signal, datetime.now())

    goal_event = goal_event_template
    goal_event.team = "Underdog FC"
    goal_event.home_score = 1
    goal_event.away_score = 0

    # Act
    signal = await alpha_one.on_goal_event(goal_event)

    # Assert
    assert signal is None
