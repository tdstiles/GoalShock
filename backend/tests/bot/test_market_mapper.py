from __future__ import annotations
import pytest
from backend.models.schemas import LiveMatch

from typing import List
from unittest.mock import Mock, AsyncMock, patch, PropertyMock

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


@pytest.mark.asyncio
async def test_map_goal_to_markets_cache_hit() -> None:
    """Ensure map_goal_to_markets uses cached market mappings."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)

    goal = build_goal_event(team="Arsenal", player="Bukayo Saka")
    market1 = build_market_price("mkt-1", "Will Arsenal win the match?")

    # Pre-populate cache
    mapper.fixture_market_map[goal.fixture_id] = ["mkt-1"]
    mock_fetcher.get_market.return_value = market1

    relevant_markets = await mapper.map_goal_to_markets(goal)

    assert relevant_markets == [market1]
    mock_fetcher.get_market.assert_called_once_with("mkt-1")
    mock_fetcher.fetch_markets_for_fixture.assert_not_called()

@pytest.mark.asyncio
async def test_map_goal_to_markets_cache_miss() -> None:
    """Ensure map_goal_to_markets fetches markets on cache miss."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)

    goal = build_goal_event(team="Arsenal", player="Bukayo Saka")
    market1 = build_market_price("mkt-1", "Will Arsenal win the match?")

    # Empty cache, so fetch_markets_for_fixture should be called
    mock_fetcher.fetch_markets_for_fixture = AsyncMock(return_value=[market1])

    relevant_markets = await mapper.map_goal_to_markets(goal)

    assert relevant_markets == [market1]
    mock_fetcher.fetch_markets_for_fixture.assert_called_once_with(
        goal.fixture_id, goal.home_team, goal.away_team
    )
    assert mapper.fixture_market_map[goal.fixture_id] == ["mkt-1"]


def build_live_match(home_team: str, away_team: str) -> LiveMatch:
    return LiveMatch(
        fixture_id=101,
        league_id=39,
        league_name="Premier League",
        home_team=home_team,
        away_team=away_team,
        home_score=0,
        away_score=0,
        minute=10,
        status="live"
    )

@pytest.mark.asyncio
async def test_get_markets_for_match_cache_hit() -> None:
    """Ensure get_markets_for_match uses cached market mappings."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)

    match = build_live_match(home_team="Arsenal", away_team="Chelsea")
    market1 = build_market_price("mkt-1", "Will Arsenal win the match?")

    # Pre-populate cache
    mapper.fixture_market_map[match.fixture_id] = ["mkt-1"]
    mock_fetcher.get_market.return_value = market1

    markets = await mapper.get_markets_for_match(match)

    assert markets == [market1]
    mock_fetcher.get_market.assert_called_once_with("mkt-1")
    mock_fetcher.fetch_markets_for_fixture.assert_not_called()

@pytest.mark.asyncio
async def test_get_markets_for_match_cache_miss() -> None:
    """Ensure get_markets_for_match fetches markets on cache miss."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)

    match = build_live_match(home_team="Arsenal", away_team="Chelsea")
    market1 = build_market_price("mkt-1", "Will Arsenal win the match?")

    # Empty cache, so fetch_markets_for_fixture should be called
    mock_fetcher.fetch_markets_for_fixture = AsyncMock(return_value=[market1])

    markets = await mapper.get_markets_for_match(match)

    assert markets == [market1]
    mock_fetcher.fetch_markets_for_fixture.assert_called_once_with(
        match.fixture_id, match.home_team, match.away_team
    )
    assert mapper.fixture_market_map[match.fixture_id] == ["mkt-1"]

@pytest.mark.asyncio
async def test_get_markets_for_match_cache_hit_returns_none() -> None:
    """Ensure get_markets_for_match fetches markets on cache hit if fetched markets evaluate to falsey."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)

    match = build_live_match(home_team="Arsenal", away_team="Chelsea")
    market1 = build_market_price("mkt-1", "Will Arsenal win the match?")

    # Pre-populate cache, but get_market returns None
    mapper.fixture_market_map[match.fixture_id] = ["mkt-1"]
    mock_fetcher.get_market.return_value = None

    mock_fetcher.fetch_markets_for_fixture = AsyncMock(return_value=[market1])

    markets = await mapper.get_markets_for_match(match)

    assert markets == [market1]
    mock_fetcher.get_market.assert_called_once_with("mkt-1")
    mock_fetcher.fetch_markets_for_fixture.assert_called_once_with(
        match.fixture_id, match.home_team, match.away_team
    )
    assert mapper.fixture_market_map[match.fixture_id] == ["mkt-1"]


def test_update_market_mapping() -> None:
    """Ensure update_market_mapping updates the mapping cache."""
    mapper = MarketMapper(Mock())

    assert 101 not in mapper.fixture_market_map
    mapper.update_market_mapping(101, ["mkt-1", "mkt-2"])

    assert mapper.fixture_market_map[101] == ["mkt-1", "mkt-2"]

    mapper.update_market_mapping(101, ["mkt-3"])
    assert mapper.fixture_market_map[101] == ["mkt-3"]




def test_clear_stale_mappings() -> None:
    """Ensure clear_stale_mappings correctly removes stale mappings."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)

    mapper.fixture_market_map = {
        101: ["mkt-1", "mkt-2"], # All stale
        102: ["mkt-3"],          # Fresh
        103: ["mkt-4", "mkt-5"], # Mixed
        104: ["mkt-6"],          # Not found (None)
    }

    # Mock markets
    mkt1 = Mock(spec=MarketPrice)
    type(mkt1).is_stale = PropertyMock(return_value=True)
    mkt2 = Mock(spec=MarketPrice)
    type(mkt2).is_stale = PropertyMock(return_value=True)

    mkt3 = Mock(spec=MarketPrice)
    type(mkt3).is_stale = PropertyMock(return_value=False)

    mkt4 = Mock(spec=MarketPrice)
    type(mkt4).is_stale = PropertyMock(return_value=True)
    mkt5 = Mock(spec=MarketPrice)
    type(mkt5).is_stale = PropertyMock(return_value=False)

    def side_effect(market_id: str):
        if market_id == "mkt-1": return mkt1
        if market_id == "mkt-2": return mkt2
        if market_id == "mkt-3": return mkt3
        if market_id == "mkt-4": return mkt4
        if market_id == "mkt-5": return mkt5
        if market_id == "mkt-6": return None
        return None

    mock_fetcher.get_market.side_effect = side_effect

    mapper.clear_stale_mappings()

    assert 101 not in mapper.fixture_market_map # Was stale
    assert 102 in mapper.fixture_market_map     # Fresh
    assert 103 in mapper.fixture_market_map     # Mixed, should not be deleted because not ALL are stale
    assert 104 in mapper.fixture_market_map     # Markets were falsey so skip deletion

    assert mapper.fixture_market_map[102] == ["mkt-3"]

def test_clear_stale_mappings_empty_map() -> None:
    """Ensure clear_stale_mappings handles an empty map correctly."""
    mock_fetcher = Mock()
    mapper = MarketMapper(mock_fetcher)
    mapper.fixture_market_map = {}
    mapper.clear_stale_mappings()
    assert mapper.fixture_market_map == {}


def test_filter_relevant_markets_includes_team_names_for_win_market() -> None:
    """Ensure filter_relevant_markets includes markets that mention home or away teams in a win market."""
    mapper = MarketMapper(Mock())
    goal = build_goal_event(team="Arsenal", player="Bukayo Saka")
    markets: List[MarketPrice] = [
        build_market_price("mkt-1", "Will Chelsea win the match?"), # away team
        build_market_price("mkt-2", "Will Manchester United win?"), # irrelevant team
    ]

    relevant_markets = mapper._filter_relevant_markets(goal, markets)

    assert relevant_markets == [markets[0]]
