
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
    The bot should detect this (via place_order_and_wait_for_fill returning None),
    cancel the order (handled inside helper), and keep the position in the 'positions' map.
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

    # Mock place_order_and_wait_for_fill to return None (Timeout/Failure)
    alpha_one.polymarket.place_order_and_wait_for_fill.return_value = None

    # Execute close logic
    success = await alpha_one._close_position(position, exit_price=0.85, reason="TAKE_PROFIT")

    # Wait, _close_position doesn't return value, it just executes.
    # But internally it calls _execute_live_close.

    # If _execute_live_close returns False (which it should if place_order_and_wait_for_fill returns None),
    # then _close_position should LOG an error and RETURN without removing position.

    # ASSERTION: The position MUST remain because the trade didn't happen
    assert "pos1" in alpha_one.positions
    assert position not in alpha_one.closed_positions

    # Verify we attempted to place and verify order
    assert alpha_one.polymarket.place_order_and_wait_for_fill.called
