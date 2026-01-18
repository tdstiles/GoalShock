from __future__ import annotations

from typing import List
from unittest.mock import Mock

from backend.bot import market_mapper
from backend.bot.market_mapper import MarketMapper
from backend.models.schemas import GoalEvent, MarketPrice


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


def build_market_price(market_id: str, question: str) -> MarketPrice:
    """Build a MarketPrice for test scenarios.

    Args:
        market_id: The market identifier.
        question: The market question text.

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


def test_keyword_helpers_detect_win_and_goal_markets() -> None:
    """Ensure helper functions detect win and total-goals markets.

    Returns:
        None.
    """
    assert market_mapper._is_win_market("Will Arsenal win the match?")
    assert not market_mapper._is_win_market("Total goals over 2.5?")
    assert market_mapper._is_total_goals_market("Total goals over 2.5?")
    assert not market_mapper._is_total_goals_market("Will Arsenal win the match?")


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
