
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from backend.alphas.alpha_two_late_compression import AlphaTwoLateCompression, ClippingOpportunity

@pytest.mark.asyncio
async def test_alpha_two_live_execution_explicit_mapping():
    """
    Verifies that _place_exchange_order correctly maps token IDs when
    'tokens' list is provided in the market response.
    """
    # Setup
    mock_poly = MagicMock()
    # Mock get_market returning tokens with outcomes
    mock_poly.get_market = AsyncMock(return_value={
        "tokens": [
            {"outcome": "YES", "token_id": "explicit_yes_token"},
            {"outcome": "NO", "token_id": "explicit_no_token"}
        ]
    })
    mock_poly.place_order = AsyncMock(return_value={"orderID": "order_789"})
    # Mock get_order returning FILLED status
    mock_poly.get_order = AsyncMock(return_value={"status": "FILLED", "orderID": "order_789"})

    alpha = AlphaTwoLateCompression(
        polymarket_client=mock_poly,
        simulation_mode=False
    )

    opportunity = ClippingOpportunity(
        opportunity_id="opp_1",
        market_id="mkt_explicit",
        market_question="Q?",
        fixture_id=1,
        yes_price=0.5,
        no_price=0.5,
        spread=0.1,
        expected_outcome="YES",
        confidence=0.99,
        expected_profit_pct=10.0,
        seconds_to_resolution=60,
        recommended_side="YES",
        recommended_price=0.5,
        recommended_size=50.0 # USD
    )

    # Act
    result = await alpha._place_exchange_order(opportunity)

    # Assert
    assert result is True
    mock_poly.get_market.assert_called_with("mkt_explicit")

    # Verify mapping to 'explicit_yes_token'
    # Size shares = 50.0 / 0.5 = 100.0
    mock_poly.place_order.assert_called_with(
        token_id="explicit_yes_token",
        side="BUY",
        price=0.5,
        size=100.0
    )


@pytest.mark.asyncio
async def test_alpha_two_live_execution_fallback_mapping():
    """
    Verifies that _place_exchange_order falls back to clobTokenIds index
    when 'tokens' list is missing/empty.
    """
    # Setup
    mock_poly = MagicMock()
    # Mock get_market returning only clobTokenIds
    mock_poly.get_market = AsyncMock(return_value={
        "clobTokenIds": ["fallback_yes_token", "fallback_no_token"]
    })
    mock_poly.place_order = AsyncMock(return_value={"orderID": "order_789"})
    # Mock get_order returning FILLED status
    mock_poly.get_order = AsyncMock(return_value={"status": "FILLED", "orderID": "order_789"})

    alpha = AlphaTwoLateCompression(
        polymarket_client=mock_poly,
        simulation_mode=False
    )

    opportunity = ClippingOpportunity(
        opportunity_id="opp_2",
        market_id="mkt_fallback",
        market_question="Q?",
        fixture_id=2,
        yes_price=0.5,
        no_price=0.5,
        spread=0.1,
        expected_outcome="NO", # Test NO side
        confidence=0.99,
        expected_profit_pct=10.0,
        seconds_to_resolution=60,
        recommended_side="NO",
        recommended_price=0.4,
        recommended_size=40.0 # USD
    )

    # Act
    result = await alpha._place_exchange_order(opportunity)

    # Assert
    assert result is True

    # Verify mapping to index 1 (NO)
    # Size shares = 40.0 / 0.4 = 100.0
    mock_poly.place_order.assert_called_with(
        token_id="fallback_no_token",
        side="BUY",
        price=0.4,
        size=100.0
    )

@pytest.mark.asyncio
async def test_alpha_two_live_execution_failure():
    """
    Verifies graceful failure when token cannot be resolved.
    """
    mock_poly = MagicMock()
    mock_poly.get_market = AsyncMock(return_value={}) # Empty market

    alpha = AlphaTwoLateCompression(
        polymarket_client=mock_poly,
        simulation_mode=False
    )

    opportunity = ClippingOpportunity(
        opportunity_id="opp_3",
        market_id="mkt_fail",
        market_question="Q?",
        fixture_id=3,
        yes_price=0.5,
        no_price=0.5,
        spread=0.1,
        expected_outcome="YES",
        confidence=0.99,
        expected_profit_pct=10.0,
        seconds_to_resolution=60,
        recommended_side="YES",
        recommended_price=0.5,
        recommended_size=50.0
    )

    result = await alpha._place_exchange_order(opportunity)
    assert result is False
