
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
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

@pytest.mark.asyncio
async def test_alpha_two_simulation_resolution(alpha_two):
    """
    Test that trades correctly resolve in simulation mode when a fixture ends.
    """

    # 1. Setup a market near the end (88th minute)
    market_id = "fixture_1001"
    fixture_active = {
        "fixture_id": 1001,
        "market_id": market_id,
        "minute": 88,
        "status": "2H",
        "home_score": 2,
        "away_score": 0,
        "home_team": "Home",
        "away_team": "Away",
        "question": "Will Home win?",
        "yes_price": 0.95,
        "no_price": 0.05
    }

    # Update state
    await alpha_two.feed_live_fixture_update(fixture_active)

    # 2. Force-execute a trade
    opp = ClippingOpportunity(
        opportunity_id="opp_1",
        market_id=market_id,
        market_question="Will Home win?",
        fixture_id=1001,
        yes_price=0.95,
        no_price=0.05,
        spread=0.9,
        expected_outcome="YES",
        confidence=0.99,
        expected_profit_pct=5.0,
        seconds_to_resolution=120,
        recommended_side="YES",
        recommended_price=0.95,
        recommended_size=10
    )

    await alpha_two._execute_clipping_trade(opp)

    # Verify trade is active
    assert len(alpha_two.trades) == 1
    trade = list(alpha_two.trades.values())[0]
    assert not trade.resolved

    # 3. Simulate match ending (FT)
    fixture_ended = {
        "fixture_id": 1001,
        "market_id": market_id,
        "minute": 90,
        "status": "FT",
        "home_score": 2,
        "away_score": 0,
        "home_team": "Home",
        "away_team": "Away",
        "question": "Will Home win?"
    }

    await alpha_two.feed_live_fixture_update(fixture_ended)

    # 4. Check resolution
    resolution = await alpha_two._check_market_resolution(market_id)

    # Expectation:
    # 1. Market should be marked resolved in internal state
    market_state = alpha_two.monitored_markets.get(market_id)
    assert market_state is not None
    assert market_state["status"] == "resolved"

    # 2. Resolution check should return valid outcome
    assert resolution is not None
    assert resolution["outcome"] == "YES"

    # 3. Process resolution
    await alpha_two._process_trade_resolution(trade, resolution)
    assert trade.resolved
    assert trade.pnl > 0
    assert alpha_two.stats.trades_won == 1


@pytest.mark.asyncio
async def test_execution_retries_on_failed_order(mock_clients):
    """Ensure failed executions remain queued with retry state for backoff."""
    alpha = AlphaTwoLateCompression(
        polymarket_client=mock_clients["poly"],
        kalshi_client=mock_clients["kalshi"],
        simulation_mode=False,
    )
    alpha._place_exchange_order = AsyncMock(return_value=False)

    opp = ClippingOpportunity(
        opportunity_id="opp_retry_1",
        market_id="market_retry_1",
        market_question="Will Home win?",
        fixture_id=1010,
        yes_price=0.85,
        no_price=0.15,
        spread=0.7,
        expected_outcome="YES",
        confidence=0.99,
        expected_profit_pct=10.0,
        seconds_to_resolution=180,
        recommended_side="YES",
        recommended_price=0.85,
        recommended_size=10,
    )

    alpha.active_opportunities[opp.opportunity_id] = opp

    await alpha._execute_opportunity_cycle()

    assert opp.opportunity_id in alpha.active_opportunities
    assert not alpha.trades
    retry_state = alpha.execution_retry_state[opp.opportunity_id]
    assert retry_state.attempts == 1
