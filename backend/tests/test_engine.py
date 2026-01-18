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
