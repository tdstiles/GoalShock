
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog, TradingMode, TradeSignal, SimulatedPosition

@pytest.mark.asyncio
async def test_alpha_one_exit_price_uses_bid_not_ask():
    # Setup
    mock_poly = MagicMock()

    # Create the strategy in SIMULATION mode (but relying on mocked client data "Shadow Mode")
    strategy = AlphaOneUnderdog(mode=TradingMode.SIMULATION, polymarket_client=mock_poly)

    # Mock token map to ensure it finds a token
    strategy.token_map = {
        (123, "Team Underdog"): "token_123"
    }

    # Setup a position
    # Entry: 0.40, Target: 0.55
    signal = TradeSignal(
        signal_id="sig_1",
        fixture_id=123,
        team="Team Underdog",
        side="YES",
        entry_price=0.40,
        target_price=0.55,
        stop_loss_price=0.30,
        size_usd=100,
        confidence=0.8,
        reason="Test"
    )

    position = SimulatedPosition(
        position_id="pos_1",
        signal=signal,
        entry_time=datetime.now(),
        last_price=0.40,
        token_id="token_123",
        quantity=250
    )

    strategy.positions["pos_1"] = position

    # Mock Market Data
    # Scenario:
    #   Best Bid: 0.50 (We can SELL at 0.50)
    #   Best Ask: 0.60 (We can BUY at 0.60)
    #   Target is 0.55.
    #
    #   Current Buggy Behavior: Uses Ask (0.60) >= Target (0.55) -> Trigger TAKE PROFIT (Incorrect)
    #   Correct Behavior: Uses Bid (0.50) < Target (0.55) -> HOLD (Correct)

    mock_orderbook = {
        "token_id": "token_123",
        "best_bid": 0.50,
        "best_ask": 0.60,
        "mid_price": 0.55,
        "spread": 0.10,
        "timestamp": datetime.now().isoformat()
    }

    # Mock get_orderbook (used by get_yes_price and potentially new get_bid_price)
    mock_poly.get_orderbook = AsyncMock(return_value=mock_orderbook)

    # Mock get_yes_price (used by current buggy implementation)
    # It returns best_ask
    mock_poly.get_yes_price = AsyncMock(return_value=0.60)

    # Mock get_bid_price (used by new fix)
    mock_poly.get_bid_price = AsyncMock(return_value=0.50)

    # Mock place_order just in case
    mock_poly.place_order = AsyncMock(return_value={"order_id": "sell_1"})

    # Run one iteration of monitor_positions
    with patch("asyncio.sleep", side_effect=InterruptedError):
        try:
            await strategy.monitor_positions()
        except InterruptedError:
            pass

    # Assert
    assert "pos_1" in strategy.positions, "Position should not be closed yet (Bid 0.50 < Target 0.55)"
    assert strategy.positions["pos_1"].status == "open", f"Position status is {strategy.positions['pos_1'].status}, expected 'open'"


@pytest.mark.asyncio
async def test_alpha_one_exit_price_triggers_on_bid_hit():
    # Setup
    mock_poly = MagicMock()
    strategy = AlphaOneUnderdog(mode=TradingMode.SIMULATION, polymarket_client=mock_poly)
    strategy.token_map = {(123, "Team Underdog"): "token_123"}

    signal = TradeSignal(
        signal_id="sig_2",
        fixture_id=123,
        team="Team Underdog",
        side="YES",
        entry_price=0.40,
        target_price=0.55,
        stop_loss_price=0.30,
        size_usd=100,
        confidence=0.8,
        reason="Test"
    )
    position = SimulatedPosition(
        position_id="pos_2",
        signal=signal,
        entry_time=datetime.now(),
        last_price=0.40,
        token_id="token_123",
        quantity=250
    )
    strategy.positions["pos_2"] = position

    # Scenario: Bid is 0.56 (>= Target 0.55). Should Close.
    mock_orderbook = {
        "token_id": "token_123",
        "best_bid": 0.56,
        "best_ask": 0.66,
        "mid_price": 0.61,
        "spread": 0.10,
        "timestamp": datetime.now().isoformat()
    }
    mock_poly.get_orderbook = AsyncMock(return_value=mock_orderbook)
    mock_poly.get_bid_price = AsyncMock(return_value=0.56)

    with patch("asyncio.sleep", side_effect=InterruptedError):
        try:
            await strategy.monitor_positions()
        except InterruptedError:
            pass

    assert "pos_2" not in strategy.positions, "Position should be closed (Bid 0.56 >= Target 0.55)"
    assert len(strategy.closed_positions) == 1
    assert strategy.closed_positions[0].position_id == "pos_2"
    assert strategy.closed_positions[0].status == "closed_take_profit"
