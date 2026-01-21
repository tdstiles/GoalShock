
import pytest
import asyncio
from unittest.mock import MagicMock
from backend.alphas.alpha_two_late_compression import AlphaTwoLateCompression

@pytest.fixture
def alpha_two():
    return AlphaTwoLateCompression(simulation_mode=True)

@pytest.mark.asyncio
async def test_basketball_volatility_underestimation(alpha_two):
    """
    Sherlock Fix Verification:
    Scenario: Basketball, 2 point lead, 10 seconds left.
    Fix: Enforce min expected swing of 3.5 pts.
    2 < 3.5. Confidence should be Favorable (0.60) or Neutral (0.50), NOT High (0.95+).
    Result: _analyze_market_for_clipping returns None (rejected).
    """
    market_data = {
        "market_id": "bball_risk",
        "question": "Will Home win?",
        "fixture_id": 1,
        "type": "basketball",
        "home_team": "H",
        "away_team": "A",
        "current_score": {"home": 102, "away": 100}, # 2 pt lead
        "seconds_to_close": 10,
        "yes_price": 0.8,
        "no_price": 0.2,
        "status": "active"
    }

    opp = await alpha_two._analyze_market_for_clipping(market_data)

    # FIXED: Opportunity rejected due to low confidence
    assert opp is None

@pytest.mark.asyncio
async def test_tie_game_bias(alpha_two):
    """
    Sherlock Fix Verification:
    Tie game (margin 0) should return CONFIDENCE_NEUTRAL (0.50).
    """
    market_data = {
        "market_id": "bball_tie",
        "question": "Will Home win?",
        "fixture_id": 2,
        "type": "basketball",
        "home_team": "H",
        "away_team": "A",
        "current_score": {"home": 100, "away": 100}, # Tie
        "seconds_to_close": 60,
        "yes_price": 0.5,
        "no_price": 0.5,
        "status": "active"
    }

    outcome = await alpha_two._predict_outcome(market_data)

    assert outcome is not None
    assert outcome["outcome"] == "NO"
    # FIXED: Confidence is 0.50 (Neutral)
    assert outcome["confidence"] == 0.50
