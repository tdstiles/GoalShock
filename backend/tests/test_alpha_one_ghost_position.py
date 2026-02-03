
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog, TradeSignal, SimulatedPosition, TradingMode
from datetime import datetime

@pytest.fixture
def alpha_one():
    polymarket = AsyncMock()
    # Mock place_order to return an order ID
    polymarket.place_order.return_value = {"orderID": "test_order_123", "order_id": "test_order_123"}

    alpha = AlphaOneUnderdog(
        mode=TradingMode.LIVE,
        polymarket_client=polymarket
    )
    return alpha

@pytest.mark.asyncio
async def test_ghost_position_prevention(alpha_one):
    """
    Verifies that the new implementation PRESERVES the position if the order is not filled.
    It simulates placing a Limit order that stays OPEN (not matched).
    The bot should detect this, cancel the order, and keep the position in the 'positions' map
    (returning False from _execute_live_close).
    """
    # Setup a position
    signal = TradeSignal(
        signal_id="sig1", fixture_id=1, team="Underdog", side="YES",
        entry_price=0.5, target_price=0.8, stop_loss_price=0.2,
        size_usd=100, confidence=0.8, reason="Test"
    )
    position = SimulatedPosition(
        position_id="pos1", signal=signal, entry_time=datetime.now(),
        token_id="token123", quantity=200
    )
    alpha_one.positions["pos1"] = position

    # Mock Orderbook
    alpha_one.polymarket.get_orderbook.return_value = {"best_bid": 0.85}

    # Mock get_order to return OPEN status (stuck order)
    # The loop calls it multiple times. We can just return OPEN every time.
    alpha_one.polymarket.get_order.return_value = {"status": "OPEN", "orderID": "test_order_123"}

    # Mock cancel_order to succeed
    alpha_one.polymarket.cancel_order.return_value = True

    # Execute close logic
    await alpha_one._close_position(position, exit_price=0.85, reason="TAKE_PROFIT")

    # ASSERTION: The position MUST remain because the trade didn't happen
    assert "pos1" in alpha_one.positions
    assert position not in alpha_one.closed_positions

    # Verify we checked the order status
    assert alpha_one.polymarket.get_order.called, "Should have checked order status"

    # Verify we cancelled the stuck order
    alpha_one.polymarket.cancel_order.assert_called_with("test_order_123")
