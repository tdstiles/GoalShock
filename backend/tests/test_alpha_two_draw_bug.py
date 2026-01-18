import pytest
import asyncio
from unittest.mock import MagicMock
from alphas.alpha_two_late_compression import AlphaTwoLateCompression, ClippingOpportunity

@pytest.fixture
def mock_clients():
    return {
        'poly': MagicMock(),
        'kalshi': MagicMock()
    }

@pytest.fixture
def alpha_two(mock_clients):
    return AlphaTwoLateCompression(
        polymarket_client=mock_clients['poly'],
        kalshi_client=mock_clients['kalshi'],
        simulation_mode=True
    )

@pytest.mark.asyncio
async def test_alpha_two_draw_resolution_failure(alpha_two):
    """
    Test that trades fail to resolve (or hang) when a fixture ends in a DRAW,
    because _predict_outcome returns None instead of "NO" for "Win" markets.
    """
    # 1. Setup a market where we bet on Home to Win
    market_id = "fixture_draw_1"
    fixture_active = {
        "fixture_id": 9999,
        "market_id": market_id,
        "minute": 88,
        "status": "2H",
        "home_score": 1,
        "away_score": 0,  # Home leading initially
        "home_team": "Home",
        "away_team": "Away",
        "question": "Will Home win?",
        "yes_price": 0.80,
        "no_price": 0.20
    }

    # Update state
    await alpha_two.feed_live_fixture_update(fixture_active)

    # 2. Force-execute a trade on YES (Home Win)
    opp = ClippingOpportunity(
        opportunity_id="opp_draw_1",
        market_id=market_id,
        market_question="Will Home win?",
        fixture_id=9999,
        yes_price=0.80,
        no_price=0.20,
        spread=0.6,
        expected_outcome="YES",
        confidence=0.90,
        expected_profit_pct=25.0,
        seconds_to_resolution=120,
        recommended_side="YES",
        recommended_price=0.80,
        recommended_size=10
    )

    await alpha_two._execute_clipping_trade(opp)

    # Verify trade exists
    assert len(alpha_two.trades) == 1
    trade = list(alpha_two.trades.values())[0]

    # 3. Simulate match ending in a DRAW (1-1)
    # Away team scores last minute
    fixture_ended = {
        "fixture_id": 9999,
        "market_id": market_id,
        "minute": 90,
        "status": "FT",
        "home_score": 1,
        "away_score": 1,  # DRAW
        "home_team": "Home",
        "away_team": "Away",
        "question": "Will Home win?"
    }

    await alpha_two.feed_live_fixture_update(fixture_ended)

    # 4. Attempt to resolve
    # The bug is here: _check_market_resolution calls _predict_outcome
    # _predict_outcome returns None for Draw
    # So resolution is None, and trade stays unresolved.
    resolution = await alpha_two._check_market_resolution(market_id)

    # ASSERTION FOR BUG REPRODUCTION:
    # If the bug exists, resolution will be None.
    # If the bug is fixed, resolution should be {"outcome": "NO", ...}

    # Uncomment to verify "Bug Present" state:
    # assert resolution is None

    # Assertion for "Desired State":
    assert resolution is not None
    assert resolution["outcome"] == "NO"
