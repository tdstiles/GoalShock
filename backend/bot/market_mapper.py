import logging
from typing import Dict, List, Tuple
from ..models.schemas import GoalEvent, MarketPrice, LiveMatch
from .market_fetcher import MarketFetcher

logger = logging.getLogger(__name__)

WIN_KEYWORDS: Tuple[str, ...] = ("win", "victory", "winner", "result")
GOAL_KEYWORDS: Tuple[str, ...] = ("goals", "score", "total")


def _is_win_market(question: str) -> bool:
    """Check whether a market question describes a win/result market.

    Args:
        question: The market question text.

    Returns:
        True if the question contains win-related keywords.
    """
    normalized = question.lower()
    return any(keyword in normalized for keyword in WIN_KEYWORDS)


def _is_total_goals_market(question: str) -> bool:
    """Check whether a market question describes a total-goals market.

    Args:
        question: The market question text.

    Returns:
        True if the question contains total-goals keywords.
    """
    normalized = question.lower()
    return any(keyword in normalized for keyword in GOAL_KEYWORDS)


class MarketMapper:
    """Map goal events to relevant betting markets."""

    def __init__(self, market_fetcher: MarketFetcher) -> None:
        """Initialize the mapper with a market fetcher.

        Args:
            market_fetcher: The market fetcher used to retrieve market data.
        """
        self.market_fetcher = market_fetcher
        self.fixture_market_map: Dict[int, List[str]] = {}

    async def map_goal_to_markets(self, goal: GoalEvent) -> List[MarketPrice]:
        """Map a goal event to relevant market prices.

        Args:
            goal: The goal event to map.

        Returns:
            A list of relevant market prices for the goal.
        """
        markets = []

        if goal.fixture_id in self.fixture_market_map:
            market_ids = self.fixture_market_map[goal.fixture_id]
            for market_id in market_ids:
                market = self.market_fetcher.get_market(market_id)
                if market and not market.is_stale:
                    markets.append(market)

        if not markets:
            markets = await self.market_fetcher.fetch_markets_for_fixture(
                goal.fixture_id, goal.home_team, goal.away_team
            )

            self.fixture_market_map[goal.fixture_id] = [m.market_id for m in markets]

        relevant_markets = self._filter_relevant_markets(goal, markets)

        logger.info(
            f"Mapped goal to {len(relevant_markets)} markets for {goal.home_team} vs {goal.away_team}"
        )
        return relevant_markets

    def _filter_relevant_markets(
        self, goal: GoalEvent, markets: List[MarketPrice]
    ) -> List[MarketPrice]:
        """Filter markets to those relevant to the goal event.

        Args:
            goal: The goal event to match against markets.
            markets: Candidate market prices for the fixture.

        Returns:
            A filtered list of relevant markets, or the original list if none match.
        """
        relevant = []

        for market in markets:
            question = market.question.lower()

            if _is_win_market(question):
                if goal.team.lower() in question:
                    relevant.append(market)
                elif (
                    goal.home_team.lower() in question
                    or goal.away_team.lower() in question
                ):
                    relevant.append(market)

            elif _is_total_goals_market(question):
                relevant.append(market)

            elif goal.player.lower() in question:
                relevant.append(market)

        return relevant or markets  # Return all if no specific matches

    async def get_markets_for_match(self, match: LiveMatch) -> List[MarketPrice]:
        """Get all markets for a live match.

        Args:
            match: The live match to fetch markets for.

        Returns:
            A list of markets for the match.
        """
        if match.fixture_id in self.fixture_market_map:
            market_ids = self.fixture_market_map[match.fixture_id]
            markets = []
            for market_id in market_ids:
                market = self.market_fetcher.get_market(market_id)
                if market:
                    markets.append(market)

            if markets:
                return markets

        markets = await self.market_fetcher.fetch_markets_for_fixture(
            match.fixture_id, match.home_team, match.away_team
        )

        self.fixture_market_map[match.fixture_id] = [m.market_id for m in markets]

        return markets

    def update_market_mapping(self, fixture_id: int, market_ids: List[str]) -> None:
        """Update the cached market IDs for a fixture.

        Args:
            fixture_id: The fixture identifier.
            market_ids: The list of market IDs for the fixture.
        """
        self.fixture_market_map[fixture_id] = market_ids

    def clear_stale_mappings(self) -> None:
        """Clear fixture mappings when all markets are stale.

        Returns:
            None.
        """
        stale_fixtures = []

        for fixture_id, market_ids in self.fixture_market_map.items():
            markets = [self.market_fetcher.get_market(m_id) for m_id in market_ids]
            markets = [m for m in markets if m]

            if markets and all(m.is_stale for m in markets):
                stale_fixtures.append(fixture_id)

        for fixture_id in stale_fixtures:
            del self.fixture_market_map[fixture_id]

        if stale_fixtures:
            logger.info(f"Cleared {len(stale_fixtures)} stale fixture mappings")
