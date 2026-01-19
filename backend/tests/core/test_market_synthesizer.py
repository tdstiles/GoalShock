from backend.core.market_synthesizer import MarketMicrostructure
import pytest
from datetime import datetime

def test_generate_trade_history_order():
    market = MarketMicrostructure()
    trades = market.generate_trade_history("test_market", num_trades=5)

    # Verify trades are in reverse chronological order (newest first)
    # The loop subtracts increasing time offsets from 'now'
    # offset_1 < offset_2 < offset_3 ...
    # time_1 > time_2 > time_3 ...

    assert len(trades) == 5

    # Parse timestamps
    timestamps = [datetime.fromisoformat(t["timestamp"]) for t in trades]

    # Check if strictly descending
    for i in range(len(timestamps) - 1):
        assert timestamps[i] > timestamps[i+1], f"Trades not in descending order at index {i}"

def test_synthesize_orderbook_prices_valid():
    market = MarketMicrostructure()
    ob = market.synthesize_orderbook("test_market")

    assert ob["mid_price"] > 0
    assert len(ob["bids"]) > 0
    assert len(ob["asks"]) > 0

    # Verify bid < ask (simplistic check for non-crossed book)
    best_bid = ob["bids"][0]["price"]
    best_ask = ob["asks"][0]["price"]

    # Spread should be positive
    assert best_ask > best_bid
