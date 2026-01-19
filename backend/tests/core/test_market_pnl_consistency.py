from backend.core.market_synthesizer import MarketMicrostructure
import pytest

def test_pnl_path_mathematical_consistency():
    market = MarketMicrostructure()

    # Generate a path
    pnl_history = market.generate_pnl_path(initial_value=1000.0, num_points=100)

    prev_pnl = 1000.0

    for entry in pnl_history:
        current_pnl = entry["pnl"]
        change_pct = entry["change_pct"]

        # Recalculate expected PnL based on the recorded previous value and percentage change
        expected_pnl = prev_pnl * (1 + change_pct / 100.0)

        # The stored 'current_pnl' is rounded to 2 decimals.
        # The 'change_pct' is also rounded to 2 decimals.
        # We verify that the stored current_pnl is mathematically consistent with
        # the stored previous value and percentage change.

        diff = abs(current_pnl - expected_pnl)

        # We assert that the value is consistent with the calculation.
        # Since we rounded internally at each step, there should be almost zero error
        # beyond the immediate rounding of the operation itself.
        assert diff < 0.02, f"PnL consistency mismatch: Prev={prev_pnl}, Pct={change_pct}%, Expected={expected_pnl:.4f}, Got={current_pnl}, Diff={diff:.4f}"

        prev_pnl = current_pnl
