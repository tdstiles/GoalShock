
import pytest
import time
from datetime import datetime
from backend.bot.market_mapper import MarketMapper
from backend.models.schemas import GoalEvent, MarketPrice
from backend.bot.market_fetcher import MarketFetcher

class MockMarketFetcher(MarketFetcher):
    def __init__(self):
        pass

@pytest.mark.benchmark
def test_filter_relevant_markets_performance():
    # Setup
    mapper = MarketMapper(MockMarketFetcher())

    # Create a goal event
    goal = GoalEvent(
        id="test_goal",
        fixture_id=123,
        league_id=39,
        league_name="Premier League",
        home_team="Manchester City",
        away_team="Liverpool",
        team="Liverpool",
        player="Mohamed Salah",
        minute=67,
        home_score=1,
        away_score=2,
        timestamp=datetime.now()
    )

    # Create a large list of markets (e.g., 10,000)
    markets = []
    for i in range(10000):
        # Mix of relevant and irrelevant markets
        question = f"Will Manchester City win vs Liverpool?" if i % 10 == 0 else f"Random Market {i}"
        markets.append(MarketPrice(
            market_id=f"m_{i}",
            fixture_id=123,
            question=question,
            yes_price=0.5,
            no_price=0.5,
            source="polymarket",
            home_team="Manchester City",
            away_team="Liverpool"
        ))

    # Measure execution time
    start_time = time.time()
    for _ in range(10):  # Run 10 times to get average
        mapper._filter_relevant_markets(goal, markets)
    end_time = time.time()

    duration = (end_time - start_time) / 10
    print(f"\nAverage execution time (10k markets): {duration:.6f} seconds")

    # Assert it's reasonable (baseline check)
    assert duration < 1.0
