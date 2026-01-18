
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
async def test_analyze_market_for_clipping_valid_opportunity(alpha_two):
    """
    Test that _analyze_market_for_clipping correctly identifies a valid clipping opportunity.
    Scenario: Soccer match, Home leads 2-0, 4 minutes left (240s).
    Expected: High confidence (0.98), returns Opportunity.
    """

    # 1. Arrange
    market_data = {
        "market_id": "market_123",
        "question": "Will Home Team win?",
        "fixture_id": 1001,
        "type": "soccer",
        "home_team": "Home Team",
        "away_team": "Away Team",
        "current_score": {
            "home": 2,
            "away": 0
        },
        "seconds_to_close": 240, # 4 minutes
        "yes_price": 0.90,       # 90 cents
        "no_price": 0.10,
        "status": "active"
    }

    # 2. Act
    opportunity = await alpha_two._analyze_market_for_clipping(market_data)

    # 3. Assert
    assert opportunity is not None
    assert isinstance(opportunity, ClippingOpportunity)
    assert opportunity.market_id == "market_123"
    assert opportunity.expected_outcome == "YES"
    assert opportunity.confidence >= 0.95 # Should be 0.98 for 2 goal lead < 300s
    assert opportunity.recommended_side == "YES"

    # Expected profit: (1.0 - 0.90) / 0.90 = 0.111... -> 11.1%
    assert opportunity.expected_profit_pct > 10.0

    # Verify confidence calculation logic matches expectation
    # 2 goal lead, < 300s -> 0.98
    assert opportunity.confidence == 0.98

@pytest.mark.asyncio
async def test_analyze_market_ignores_low_confidence(alpha_two):
    """
    Test that low confidence scenarios are ignored.
    Scenario: Soccer match, Home leads 1-0, 10 minutes left (600s).
    Expected: Confidence too low, returns None.
    """
    market_data = {
        "market_id": "market_low_conf",
        "question": "Will Home Team win?",
        "fixture_id": 1002,
        "type": "soccer",
        "home_team": "Home Team",
        "away_team": "Away Team",
        "current_score": {
            "home": 1,
            "away": 0
        },
        "seconds_to_close": 600, # 10 minutes
        "yes_price": 0.80,
        "no_price": 0.20,
        "status": "active"
    }

    opportunity = await alpha_two._analyze_market_for_clipping(market_data)
    assert opportunity is None

@pytest.mark.asyncio
async def test_analyze_market_ignores_low_profit(alpha_two):
    """
    Test that low profit scenarios are ignored even if confidence is high.
    Scenario: Soccer match, Home leads 3-0 (Confidence 0.99), Price is 0.98.
    Profit: (1.0 - 0.98)/0.98 = 2.04% < 3% threshold.
    """
    market_data = {
        "market_id": "market_low_profit",
        "question": "Will Home Team win?",
        "fixture_id": 1003,
        "type": "soccer",
        "home_team": "Home Team",
        "away_team": "Away Team",
        "current_score": {
            "home": 3,
            "away": 0
        },
        "seconds_to_close": 600,
        "yes_price": 0.98,
        "no_price": 0.02,
        "status": "active"
    }

    opportunity = await alpha_two._analyze_market_for_clipping(market_data)
    assert opportunity is None
