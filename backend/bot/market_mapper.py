import logging
from typing import Dict, List

from ..models.schemas import GoalEvent, LiveMatch, MarketPrice
from .market_fetcher import MarketFetcher

logger = logging.getLogger(__name__)


class MarketMapper:
    """Map goal events and live matches to market data."""

    def __init__(self, market_fetcher: MarketFetcher):
        """Initialize the mapper with a market fetcher.

        Args:
            market_fetcher: Fetcher used to retrieve and cache markets.
        """
        self.market_fetcher = market_fetcher
        self.fixture_market_map: Dict[int, List[str]] = {}

    async def map_goal_to_markets(self, goal: GoalEvent) -> List[MarketPrice]:
        """Map a goal event to relevant markets.

        Args:
            goal: Goal event used to filter market relevance.

        Returns:
            A list of markets relevant to the goal event.
        """
        markets = self._get_cached_markets(goal.fixture_id)

        if not markets:
            markets = await self.market_fetcher.fetch_markets_for_fixture(
                goal.fixture_id,
                goal.home_team,
                goal.away_team,
            )

            self.fixture_market_map[goal.fixture_id] = [m.market_id for m in markets]

        relevant_markets = self._filter_relevant_markets(goal, markets)

        logger.info(
            "Mapped goal to %s markets for %s vs %s",
            len(relevant_markets),
            goal.home_team,
            goal.away_team,
        )
        return relevant_markets

    def _filter_relevant_markets(
        self,
        goal: GoalEvent,
        markets: List[MarketPrice],
    ) -> List[MarketPrice]:
        """Filter markets to those relevant to the goal event.

        Args:
            goal: Goal event context for relevance.
            markets: Markets to filter.

        Returns:
            A list of markets relevant to the goal event.
        """
        relevant = []

        for market in markets:
            question = market.question.lower()

            if any(
                keyword in question
                for keyword in ["win", "victory", "winner", "result"]
            ):
                if goal.team.lower() in question:
                    relevant.append(market)
                elif (
                    goal.home_team.lower() in question
                    or goal.away_team.lower() in question
                ):
                    relevant.append(market)

            elif any(keyword in question for keyword in ["goals", "score", "total"]):
                relevant.append(market)

            elif goal.player.lower() in question:
                relevant.append(market)

        return relevant or markets  # Return all if no specific matches

    async def get_markets_for_match(self, match: LiveMatch) -> List[MarketPrice]:
        """Get all markets for a live match.

        Args:
            match: Live match context for market retrieval.

        Returns:
            A list of markets associated with the match.
        """
        markets = self._get_cached_markets(match.fixture_id)
        if markets:
            return markets

        markets = await self.market_fetcher.fetch_markets_for_fixture(
            match.fixture_id,
            match.home_team,
            match.away_team,
        )

        self.fixture_market_map[match.fixture_id] = [m.market_id for m in markets]

        return markets

    def update_market_mapping(self, fixture_id: int, market_ids: List[str]):
        """Update the market mapping for a fixture.

        Args:
            fixture_id: The fixture identifier.
            market_ids: The list of market IDs to cache.
        """
        self.fixture_market_map[fixture_id] = market_ids

    def clear_stale_mappings(self):
        """Remove mappings when all cached markets are stale."""
        stale_fixtures = []

        for fixture_id, market_ids in self.fixture_market_map.items():
            markets = [self.market_fetcher.get_market(m_id) for m_id in market_ids]
            markets = [m for m in markets if m]

            if markets and all(m.is_stale for m in markets):
                stale_fixtures.append(fixture_id)

        for fixture_id in stale_fixtures:
            del self.fixture_market_map[fixture_id]

        if stale_fixtures:
            logger.info("Cleared %s stale fixture mappings", len(stale_fixtures))

    def _get_cached_markets(self, fixture_id: int) -> List[MarketPrice]:
        """Retrieve cached markets for a fixture, excluding stale entries.

        Args:
            fixture_id: The fixture identifier.

        Returns:
            A list of non-stale cached markets.
        """
        market_ids = self.fixture_market_map.get(fixture_id, [])
        markets: List[MarketPrice] = []
        for market_id in market_ids:
            market = self.market_fetcher.get_market(market_id)
            if market and not market.is_stale:
                markets.append(market)

        if markets:
            self.fixture_market_map[fixture_id] = [m.market_id for m in markets]

        return markets
