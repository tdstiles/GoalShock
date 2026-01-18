"""Tests for the headless TradingEngine behavior."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from engine import GoalEvent, TradingEngine


@pytest.fixture
def trading_engine() -> TradingEngine:
    """Create a TradingEngine with mocked external clients.

    Returns:
        TradingEngine: Trading engine instance with mocked dependencies.
    """
    with patch("engine.APIFootballClient"), patch("engine.PolymarketClient"), patch(
        "engine.KalshiClient"
    ):
        return TradingEngine()


@pytest.fixture
def goal_event() -> GoalEvent:
    """Return a sample GoalEvent where the underdog scores.

    Returns:
        GoalEvent: Sample goal event payload.
    """
    return GoalEvent(
        fixture_id=42,
        minute=55,
        team="Underdog FC",
        player="A. Striker",
        home_score=1,
        away_score=1,
        timestamp=datetime.now(),
    )


@pytest.fixture
def fixture_details() -> dict:
    """Return fixture details with known home and away teams.

    Returns:
        dict: Fixture details payload with home and away teams.
    """
    return {
        "teams": {"home": {"name": "Home FC"}, "away": {"name": "Away FC"}},
    }


@pytest.mark.asyncio
async def test_is_underdog_leading_returns_false_when_underdog_not_in_fixture(
    trading_engine: TradingEngine, fixture_details: dict
) -> None:
    """Return False when the underdog team is not part of the fixture.

    Args:
        trading_engine: Trading engine under test.
        fixture_details: Fixture details payload with home and away teams.
    """
    trading_engine.api_football.get_fixture_details = AsyncMock(
        return_value=fixture_details
    )
    goal = GoalEvent(
        fixture_id=99,
        minute=12,
        team="Other FC",
        player="Striker",
        home_score=1,
        away_score=0,
        timestamp=datetime.now(),
    )

    result = await trading_engine.is_underdog_leading(goal, "Underdog FC")

    assert result is False


@pytest.mark.asyncio
async def test_is_underdog_leading_returns_false_when_tied(
    trading_engine: TradingEngine, fixture_details: dict
) -> None:
    """Return False when the underdog has only tied the match.

    Args:
        trading_engine: Trading engine under test.
        fixture_details: Fixture details payload with home and away teams.
    """
    trading_engine.api_football.get_fixture_details = AsyncMock(
        return_value=fixture_details
    )
    goal = GoalEvent(
        fixture_id=100,
        minute=30,
        team="Home FC",
        player="Equalizer",
        home_score=1,
        away_score=1,
        timestamp=datetime.now(),
    )

    result = await trading_engine.is_underdog_leading(goal, "Home FC")

    assert result is False


@pytest.mark.asyncio
async def test_is_underdog_leading_returns_false_when_still_losing(
    trading_engine: TradingEngine, fixture_details: dict
) -> None:
    """Return False when the underdog remains behind after scoring.

    Args:
        trading_engine: Trading engine under test.
        fixture_details: Fixture details payload with home and away teams.
    """
    trading_engine.api_football.get_fixture_details = AsyncMock(
        return_value=fixture_details
    )
    goal = GoalEvent(
        fixture_id=101,
        minute=44,
        team="Home FC",
        player="Consolation",
        home_score=1,
        away_score=2,
        timestamp=datetime.now(),
    )

    result = await trading_engine.is_underdog_leading(goal, "Home FC")

    assert result is False


@pytest.mark.asyncio
async def test_is_underdog_leading_returns_true_when_leading(
    trading_engine: TradingEngine, fixture_details: dict
) -> None:
    """Return True when the underdog moves ahead after scoring.

    Args:
        trading_engine: Trading engine under test.
        fixture_details: Fixture details payload with home and away teams.
    """
    trading_engine.api_football.get_fixture_details = AsyncMock(
        return_value=fixture_details
    )
    goal = GoalEvent(
        fixture_id=102,
        minute=67,
        team="Away FC",
        player="Winner",
        home_score=1,
        away_score=2,
        timestamp=datetime.now(),
    )

    result = await trading_engine.is_underdog_leading(goal, "Away FC")

    assert result is True


def test_process_goal_event_skips_trade_when_underdog_not_leading(
    trading_engine: TradingEngine, goal_event: GoalEvent
) -> None:
    """Ensure trades are skipped when the underdog is not leading after scoring.

    Args:
        trading_engine: Trading engine under test.
        goal_event: Goal event payload where the underdog scored.
    """
    # Arrange
    trading_engine.identify_pre_match_underdog = AsyncMock(return_value="Underdog FC")
    trading_engine.is_underdog_leading = AsyncMock(return_value=False)
    trading_engine.get_market_price = AsyncMock(return_value=0.42)
    trading_engine.execute_trade = AsyncMock()

    # Act
    asyncio.run(trading_engine.process_goal_event(goal_event))

    # Assert
    trading_engine.identify_pre_match_underdog.assert_awaited_once_with(42)
    trading_engine.is_underdog_leading.assert_awaited_once_with(
        goal_event, "Underdog FC"
    )
    trading_engine.get_market_price.assert_not_awaited()
    trading_engine.execute_trade.assert_not_awaited()


def test_identify_pre_match_underdog_uses_cache(
    trading_engine: TradingEngine,
) -> None:
    """Ensure identify_pre_match_underdog caches and returns the lowest-odds team.

    Args:
        trading_engine: Trading engine under test.
    """
    trading_engine.fetch_pre_match_odds = AsyncMock(
        return_value={"Favorite FC": 0.65, "Underdog FC": 0.35}
    )

    first_result = asyncio.run(trading_engine.identify_pre_match_underdog(101))
    second_result = asyncio.run(trading_engine.identify_pre_match_underdog(101))

    trading_engine.fetch_pre_match_odds.assert_awaited_once_with(101)
    assert first_result == "Underdog FC"
    assert second_result == "Underdog FC"
    assert trading_engine.underdog_cache[101] == "Underdog FC"
