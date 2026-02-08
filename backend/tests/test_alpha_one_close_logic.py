
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog, TradeSignal, SimulatedPosition, TradingMode

@pytest.fixture
def alpha_one():
    # Setup
    polymarket = AsyncMock()
    alpha = AlphaOneUnderdog(
        mode=TradingMode.LIVE,
        polymarket_client=polymarket
    )
    return alpha

@pytest.mark.asyncio
async def test_execute_live_close_with_zero_bid(alpha_one):
    # Setup Position
    signal = TradeSignal(
        signal_id="sig1", fixture_id=1, team="Underdog", side="YES",
        entry_price=0.5, target_price=0.8, stop_loss_price=0.2,
        size_usd=100, confidence=0.8, reason="Test"
    )
    position = SimulatedPosition(
        position_id="pos1", signal=signal, entry_time="2024-01-01",
        token_id="token123", quantity=200
    )

    # Mock Polymarket Orderbook returning "0"
    alpha_one.polymarket.get_markets_by_event.return_value = [{"clobTokenIds": ["token123"]}]
    alpha_one.polymarket.get_orderbook.return_value = {"best_bid": "0"}

    # Mock place_order_and_wait_for_fill returning success
    alpha_one.polymarket.place_order_and_wait_for_fill.return_value = {"order_id": "123", "status": "FILLED"}

    # Execute Close
    await alpha_one._execute_live_close(position, price=0.5)

    # Verify call
    # We expect it to fallback to trigger price (0.5) because "0" should be rejected/ignored?
    calls = alpha_one.polymarket.place_order_and_wait_for_fill.call_args_list
    assert len(calls) == 1

    args, kwargs = calls[0]
    price_arg = kwargs.get("price")

    print(f"Executed Price: {price_arg}")

    # Sherlock Fix: Expect aggressive price (0.001) for market sell behavior
    assert price_arg == 0.001, f"Fix Failed: Price {price_arg} should be 0.001"

@pytest.mark.asyncio
async def test_execute_live_close_with_valid_bid(alpha_one):
    # Setup Position
    signal = TradeSignal(
        signal_id="sig1", fixture_id=1, team="Underdog", side="YES",
        entry_price=0.5, target_price=0.8, stop_loss_price=0.2,
        size_usd=100, confidence=0.8, reason="Test"
    )
    position = SimulatedPosition(
        position_id="pos1", signal=signal, entry_time="2024-01-01",
        token_id="token123", quantity=200
    )

    # Mock Polymarket Orderbook returning "0.45"
    alpha_one.polymarket.get_markets_by_event.return_value = [{"clobTokenIds": ["token123"]}]
    alpha_one.polymarket.get_orderbook.return_value = {"best_bid": "0.45"}

    # Mock place_order_and_wait_for_fill returning success
    alpha_one.polymarket.place_order_and_wait_for_fill.return_value = {"order_id": "123", "status": "FILLED"}

    # Execute Close
    await alpha_one._execute_live_close(position, price=0.5)

    # Verify call
    calls = alpha_one.polymarket.place_order_and_wait_for_fill.call_args_list
    assert len(calls) == 1

    args, kwargs = calls[0]
    price_arg = kwargs.get("price")

    print(f"Executed Price: {price_arg}")

    assert price_arg == 0.001
