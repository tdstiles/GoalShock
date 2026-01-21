import pytest
from backend.core.stream_processor import StreamProcessor
from datetime import datetime

class MockEvent:
    def __init__(self, match_id, team, player, minute, timestamp):
        self.match_id = match_id
        self.team = team
        self.player = player
        self.minute = minute
        self.timestamp = timestamp

@pytest.mark.asyncio
async def test_enrich_events_synthetic():
    sp = StreamProcessor()

    # Create raw events
    raw_events = [
        MockEvent("m1", "Team A", "Player 1", 10, datetime.now()),
        MockEvent("m2", "Team B", "Player 2", 20, datetime.now())
    ]

    # Empty market data
    market_data = {"markets": []}

    enriched = await sp.enrich_events(raw_events, market_data)

    assert len(enriched) == 2
    assert enriched[0]["team"] == "Team A"
    assert "market_context" in enriched[0]

    # Check synthetic market context structure
    ctx = enriched[0]["market_context"]
    assert ctx["market_id"].startswith("synth_")
    assert 0.4 <= ctx["current_price"] <= 0.8
    assert 10000 <= ctx["volume"] <= 100000

@pytest.mark.asyncio
async def test_aggregate_statistics():
    sp = StreamProcessor()

    events = [
        {"match_id": "m1", "minute": 10, "player": "P1"},
        {"match_id": "m1", "minute": 20, "player": "P2"},
        {"match_id": "m2", "minute": 30, "player": "P1"}
    ]

    stats = await sp.aggregate_statistics(events)

    assert stats["total_goals"] == 3
    assert stats["unique_matches"] == 2
    assert stats["avg_minute"] == 20.0
    assert len(stats["top_scorers"]) == 2
    assert stats["top_scorers"][0]["player"] == "P1"
    assert stats["top_scorers"][0]["goals"] == 2
