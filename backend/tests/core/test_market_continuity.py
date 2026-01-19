from backend.core.market_synthesizer import MarketMicrostructure
import pytest

def test_market_continuity():
    """
    Verifies that the MarketMicrostructure simulation maintains price continuity
    for a given market_id across multiple calls.
    """
    mm = MarketMicrostructure()
    market_id = "market_1"

    # First call
    ob1 = mm.synthesize_orderbook(market_id)
    price1 = ob1["mid_price"]

    # Second call
    ob2 = mm.synthesize_orderbook(market_id)
    price2 = ob2["mid_price"]

    # Third call
    ob3 = mm.synthesize_orderbook(market_id)
    price3 = ob3["mid_price"]

    print(f"Price 1: {price1}")
    print(f"Price 2: {price2}")
    print(f"Price 3: {price3}")

    # Calculate differences
    diff1 = abs(price2 - price1)
    diff2 = abs(price3 - price2)

    # With continuity, price changes should be driven by Brownian motion.
    # Sigma (volatility) is max 0.08. dt is 0.1.
    # Expected change ~ sigma * sqrt(dt) * price ~ 0.08 * 0.3 * 0.5 ~ 0.012
    # 3 std devs ~ 0.04.
    # Without continuity (random restart), prices jump in [0.3, 0.7].
    # Jumps > 0.1 are common.

    # We assert that jumps are reasonably small (< 0.1).
    assert diff1 < 0.1, f"Price discontinuity detected: {price1} -> {price2}"
    assert diff2 < 0.1, f"Price discontinuity detected: {price2} -> {price3}"
