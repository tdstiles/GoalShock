
import pytest
from datetime import datetime, timedelta
from backend.alphas.alpha_one_underdog import AlphaOneUnderdog, SimulatedPosition, TradeSignal

@pytest.mark.asyncio
async def test_simulate_price_movement_drift_sanity():
    """
    Verifies that the price simulation drift is reasonable and not excessive.
    Reproduces a bug where using seconds instead of fraction of day for drift
    caused massive price decay (e.g. 6% in 50 seconds).
    """
    alpha = AlphaOneUnderdog()

    # Create a signal and position at high price (to trigger downward drift)
    signal = TradeSignal(
        signal_id="test_signal",
        fixture_id=1,
        team="Test Team",
        side="YES",
        entry_price=0.95,
        target_price=1.0,
        stop_loss_price=0.5,
        size_usd=100,
        confidence=0.9,
        reason="Test"
    )

    position = SimulatedPosition(
        position_id="test_pos",
        signal=signal,
        entry_time=datetime.now(),
        last_price=0.95,
        last_update_time=datetime.now(),
        token_id="test_token",
        quantity=100
    )

    # Simulate 50 seconds of movement (10 steps of 5s)
    for _ in range(10):
        # Move last_update_time back by 5s to simulate 5s elapsed
        position.last_update_time = datetime.now() - timedelta(seconds=5)
        alpha._simulate_price_movement(position)

    final_price = position.last_price
    drop = 0.95 - final_price

    print(f"Final Price: {final_price}, Drop: {drop}")

    # In a stable simulation, drift should be minimal (fraction of a percent).
    # If bug exists, drop is ~0.05 (5%).
    # We assert drop is less than 0.01 (1%).
    assert drop < 0.01, f"Price dropped too fast: {drop:.4f} in 50s"
