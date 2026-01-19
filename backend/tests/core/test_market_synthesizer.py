
import pytest
from backend.core.market_synthesizer import MarketMicrostructure

@pytest.fixture
def market_microstructure():
    return MarketMicrostructure()

def test_synthesize_orderbook_structure(market_microstructure):
    market_id = "test_market"
    orderbook = market_microstructure.synthesize_orderbook(market_id)

    assert "mid_price" in orderbook
    assert "spread" in orderbook
    assert "bids" in orderbook
    assert "asks" in orderbook
    assert "total_volume" in orderbook
    assert "volatility" in orderbook

    assert isinstance(orderbook["mid_price"], float)
    assert 0.0 < orderbook["mid_price"] < 1.0

    assert len(orderbook["bids"]) == 5
    assert len(orderbook["asks"]) == 5

    # Check bid sorting (descending)
    prices = [b["price"] for b in orderbook["bids"]]
    assert prices == sorted(prices, reverse=True)

    # Check ask sorting (ascending)
    prices = [a["price"] for a in orderbook["asks"]]
    assert prices == sorted(prices)

def test_generate_trade_history_structure(market_microstructure):
    market_id = "test_market"
    num_trades = 10
    trades = market_microstructure.generate_trade_history(market_id, num_trades)

    assert len(trades) == num_trades

    trade = trades[0]
    assert "price" in trade
    assert "size" in trade
    assert "side" in trade
    assert "timestamp" in trade

    assert trade["side"] in ["buy", "sell"]

    # Check sorting (descending by timestamp)
    # Timestamps are strings, so we can compare them directly in ISO format
    timestamps = [t["timestamp"] for t in trades]
    assert timestamps == sorted(timestamps, reverse=True)

def test_generate_pnl_path_structure(market_microstructure):
    initial_value = 1000
    num_points = 50
    pnl_history = market_microstructure.generate_pnl_path(initial_value, num_points)

    assert len(pnl_history) == num_points

    entry = pnl_history[0]
    assert "timestamp" in entry
    assert "pnl" in entry
    assert "change_pct" in entry

    # PnL should drift but stay somewhat reasonable (not checking exact values due to randomness)
    # Just checking it's a number
    assert isinstance(entry["pnl"], (int, float))
