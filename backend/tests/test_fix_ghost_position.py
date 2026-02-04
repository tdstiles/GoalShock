
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog, TradingMode, TradeSignal
from backend.alphas.alpha_two_late_compression import AlphaTwoLateCompression, ClippingOpportunity

@pytest.mark.asyncio
async def test_alpha_one_ghost_position_prevented():
    """
    Verifies that AlphaOne DOES NOT create a position if the order is not filled within timeout.
    """
    mock_poly = MagicMock()
    mock_poly.place_order = AsyncMock(return_value={"order_id": "0x123", "orderID": "0x123"})
    mock_poly.get_markets_by_event = AsyncMock(return_value=[{
        "clobTokenIds": ["0xYES", "0xNO"],
        "tokens": [{"outcome": "YES", "token_id": "0xYES"}]
    }])
    # Always OPEN (never fills)
    mock_poly.get_order = AsyncMock(return_value={"status": "OPEN", "order_id": "0x123"})
    mock_poly.cancel_order = AsyncMock(return_value=True)

    alpha = AlphaOneUnderdog(mode=TradingMode.LIVE, polymarket_client=mock_poly)
    signal = TradeSignal(
        signal_id="sig_1", fixture_id=100, team="Test", side="YES",
        entry_price=0.5, target_price=0.8, stop_loss_price=0.4,
        size_usd=10.0, confidence=0.8, reason="Test"
    )

    await alpha._execute_live_trade(signal)

    # Verify NO position created
    assert len(alpha.positions) == 0
    # Verify cancellation was attempted
    mock_poly.cancel_order.assert_called_with("0x123")

@pytest.mark.asyncio
async def test_alpha_one_position_created_when_filled():
    """
    Verifies that AlphaOne creates a position ONLY when the order is filled.
    """
    mock_poly = MagicMock()
    mock_poly.place_order = AsyncMock(return_value={"order_id": "0xFILLED", "orderID": "0xFILLED"})
    mock_poly.get_markets_by_event = AsyncMock(return_value=[{
        "clobTokenIds": ["0xYES", "0xNO"],
        "tokens": [{"outcome": "YES", "token_id": "0xYES"}]
    }])
    # FILLED immediately
    mock_poly.get_order = AsyncMock(return_value={"status": "FILLED", "order_id": "0xFILLED"})
    mock_poly.cancel_order = AsyncMock(return_value=True)

    alpha = AlphaOneUnderdog(mode=TradingMode.LIVE, polymarket_client=mock_poly)
    signal = TradeSignal(
        signal_id="sig_2", fixture_id=101, team="Test2", side="YES",
        entry_price=0.5, target_price=0.8, stop_loss_price=0.4,
        size_usd=10.0, confidence=0.8, reason="Test"
    )

    await alpha._execute_live_trade(signal)

    # Verify position CREATED
    assert len(alpha.positions) == 1
    assert alpha.positions["0xFILLED"].position_id == "0xFILLED"
    # Verify cancellation was NOT called
    mock_poly.cancel_order.assert_not_called()

@pytest.mark.asyncio
async def test_alpha_two_ghost_trade_prevented():
    """
    Verifies that AlphaTwo returns False and does not track trade if order is not filled.
    """
    mock_poly = MagicMock()
    mock_poly.place_order = AsyncMock(return_value={"order_id": "0x999", "orderID": "0x999"})
    mock_poly.get_market = AsyncMock(return_value={
        "clobTokenIds": ["0xYES", "0xNO"],
        "tokens": [{"outcome": "YES", "token_id": "0xYES"}]
    })
    # Always OPEN (never fills)
    mock_poly.get_order = AsyncMock(return_value={"status": "OPEN", "order_id": "0x999"})
    mock_poly.cancel_order = AsyncMock(return_value=True)

    alpha = AlphaTwoLateCompression(polymarket_client=mock_poly, simulation_mode=False)

    opportunity = ClippingOpportunity(
        opportunity_id="clip_1", market_id="mkt_1", market_question="?", fixture_id=99,
        yes_price=0.5, no_price=0.5, spread=0, expected_outcome="YES", confidence=0.9,
        expected_profit_pct=10, seconds_to_resolution=60, recommended_side="YES",
        recommended_price=0.5, recommended_size=10
    )

    # We test _place_exchange_order directly as it returns the boolean
    result = await alpha._place_exchange_order(opportunity)

    assert result is False
    mock_poly.cancel_order.assert_called_with("0x999")

@pytest.mark.asyncio
async def test_alpha_two_trade_success_when_filled():
    """
    Verifies that AlphaTwo returns True when filled.
    """
    mock_poly = MagicMock()
    mock_poly.place_order = AsyncMock(return_value={"order_id": "0xGOOD", "orderID": "0xGOOD"})
    mock_poly.get_market = AsyncMock(return_value={
        "clobTokenIds": ["0xYES", "0xNO"],
        "tokens": [{"outcome": "YES", "token_id": "0xYES"}]
    })
    # FILLED
    mock_poly.get_order = AsyncMock(return_value={"status": "FILLED", "order_id": "0xGOOD"})
    mock_poly.cancel_order = AsyncMock(return_value=True)

    alpha = AlphaTwoLateCompression(polymarket_client=mock_poly, simulation_mode=False)

    opportunity = ClippingOpportunity(
        opportunity_id="clip_2", market_id="mkt_2", market_question="?", fixture_id=99,
        yes_price=0.5, no_price=0.5, spread=0, expected_outcome="YES", confidence=0.9,
        expected_profit_pct=10, seconds_to_resolution=60, recommended_side="YES",
        recommended_price=0.5, recommended_size=10
    )

    result = await alpha._place_exchange_order(opportunity)

    assert result is True
    mock_poly.cancel_order.assert_not_called()
