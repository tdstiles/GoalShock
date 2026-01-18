from __future__ import annotations

from datetime import datetime, timedelta
from typing import List
from unittest.mock import Mock

import pytest

from backend.bot.market_mapper import MarketMapper
from backend.models.schemas import GoalEvent, LiveMatch, MarketPrice


def build_goal_event(team: str, player: str) -> GoalEvent:
    """Build a GoalEvent for test scenarios.

    Args:
        team: The team that scored.
        player: The player who scored.

    Returns:
        A GoalEvent instance with default values.
    """
    return GoalEvent(
        id="evt-1",
        fixture_id=101,
        league_id=39,
        league_name="Premier League",
        home_team="Arsenal",
        away_team="Chelsea",
        team=team,
        player=player,
        minute=10,
        home_score=1,
        away_score=0,
    )


def build_market_price(
    market_id: str,
    question: str,
    *,
    last_updated: datetime | None = None,
) -> MarketPrice:
    """Build a MarketPrice for test scenarios.

    Args:
        market_id: The market identifier.
        question: The market question text.
        last_updated: Optional timestamp override for staleness tests.

    Returns:
        A MarketPrice instance with default values.
    """
    return MarketPrice(
        market_id=market_id,
        fixture_id=101,
        question=question,
        yes_price=0.55,
        no_price=0.45,
        source="polymarket",
        last_updated=last_updated or datetime.now(),
        home_team="Arsenal",
        away_team="Chelsea",
    )


def test_filter_relevant_markets_includes_expected_markets() -> None:
    """Ensure team, total-goals, and player markets are included.

    Returns:
        None.
    """
    mapper = MarketMapper(Mock())
    goal = build_goal_event(team="Arsenal", player="Bukayo Saka")
    markets: List[MarketPrice] = [
        build_market_price("mkt-1", "Will Arsenal win the match?"),
        build_market_price("mkt-2", "Total goals over 2.5?"),
        build_market_price(
            "mkt-3",
            "Will Bukayo Saka have a shot on target?",
        ),
    ]

    relevant_markets = mapper._filter_relevant_markets(goal, markets)

    assert relevant_markets == markets


def test_filter_relevant_markets_falls_back_when_no_keywords_match() -> None:
    """Ensure no keyword matches returns original markets list.

    Returns:
        None.
    """
    mapper = MarketMapper(Mock())
    goal = build_goal_event(team="Arsenal", player="Bukayo Saka")
    markets: List[MarketPrice] = [
        build_market_price("mkt-10", "Corner count in the match?"),
        build_market_price("mkt-11", "Bookings in the first half?"),
    ]

    relevant_markets = mapper._filter_relevant_markets(goal, markets)

    assert relevant_markets is markets


@pytest.mark.asyncio
async def test_map_goal_to_markets_ignores_stale_cached_markets() -> None:
    """Ensure stale cached markets are not used for goal mapping.

    Returns:
        None.
    """
    market_fetcher = Mock()
    mapper = MarketMapper(market_fetcher)
    goal = build_goal_event(team="Arsenal", player="Bukayo Saka")
    fresh_market = build_market_price("mkt-1", "Will Arsenal win the match?")
    stale_market = build_market_price(
        "mkt-2",
        "Total goals over 2.5?",
        last_updated=datetime.now() - timedelta(seconds=120),
    )

    mapper.fixture_market_map[goal.fixture_id] = [
        fresh_market.market_id,
        stale_market.market_id,
    ]
    market_fetcher.get_market.side_effect = [fresh_market, stale_market]

    markets = await mapper.map_goal_to_markets(goal)

    assert markets == [fresh_market]


@pytest.mark.asyncio
async def test_get_markets_for_match_ignores_stale_cached_markets() -> None:
    """Ensure stale cached markets are not used for match market retrieval.

    Returns:
        None.
    """
    market_fetcher = Mock()
    mapper = MarketMapper(market_fetcher)
    match = LiveMatch(
        fixture_id=101,
        league_id=39,
        league_name="Premier League",
        home_team="Arsenal",
        away_team="Chelsea",
        home_score=1,
        away_score=0,
        minute=10,
        status="1H",
    )
    fresh_market = build_market_price("mkt-1", "Will Arsenal win the match?")
    stale_market = build_market_price(
        "mkt-2",
        "Total goals over 2.5?",
        last_updated=datetime.now() - timedelta(seconds=120),
    )

    mapper.fixture_market_map[match.fixture_id] = [
        fresh_market.market_id,
        stale_market.market_id,
    ]
    market_fetcher.get_market.side_effect = [fresh_market, stale_market]

    markets = await mapper.get_markets_for_match(match)

    assert markets == [fresh_market]
