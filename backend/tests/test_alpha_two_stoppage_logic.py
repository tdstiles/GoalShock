import pytest
import asyncio
from backend.alphas.alpha_two_late_compression import AlphaTwoLateCompression

@pytest.mark.asyncio
async def test_stoppage_time_discontinuity():
    alpha = AlphaTwoLateCompression(simulation_mode=True)
    market_id = "test_market"

    # 1. Minute 45, Playing (1H Regular)
    # The strategy logic assumes 90 mins + 8 mins buffer = 98 mins total duration base
    # At min 45: (98 - 45) * 60 = 53 * 60 = 3180s
    await alpha.feed_live_fixture_update({
        "market_id": market_id,
        "status": "1H",
        "minute": 45,
        "home_score": 0, "away_score": 0,
        "fixture_id": 123
    })
    market = alpha.monitored_markets[market_id]
    time_45_play = market["seconds_to_close"]

    # We expect 3180s based on current logic
    assert time_45_play == 3180

    # 2. Minute 47, Playing (1H Stoppage)
    # The API reports minute 47.
    # Logic: (98 - 47) * 60 = 51 * 60 = 3060s
    await alpha.feed_live_fixture_update({
        "market_id": market_id,
        "status": "1H",
        "minute": 47,
        "home_score": 0, "away_score": 0,
        "fixture_id": 123
    })
    market = alpha.monitored_markets[market_id]
    time_47_play = market["seconds_to_close"]
    assert time_47_play == 3060

    # 3. HT (Half Time)
    # The game enters Halftime.
    # Current Buggy Logic: (90 - 45) * 60 = 45 * 60 = 2700s
    # This represents a drop of 360 seconds (6 minutes) instantly.
    # Expected Logic: Should preserve the buffer notion.
    # Remaining should be 45 mins (2nd half) + 8 mins (buffer) = 53 mins = 3180s
    # Or at least shouldn't be less than what we had at min 47.

    await alpha.feed_live_fixture_update({
        "market_id": market_id,
        "status": "HT",
        "minute": 45, # API usually reports 45 during HT
        "home_score": 0, "away_score": 0,
        "fixture_id": 123
    })
    market = alpha.monitored_markets[market_id]
    time_ht = market["seconds_to_close"]

    print(f"Time 45 Play: {time_45_play}")
    print(f"Time 47 Play: {time_47_play}")
    print(f"Time HT: {time_ht}")

    # Assert that we don't have a massive discontinuity
    # 3060 - 2700 = 360 drop.
    # We want time_ht to be consistent with "45 minutes + buffer left".
    # So we expect ~3180s.

    assert time_ht >= 3000, f"Discontinuity detected at HT! Dropped from {time_47_play} to {time_ht}"
