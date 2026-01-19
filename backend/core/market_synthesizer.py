
import random
import math
from typing import Dict, List
from datetime import datetime, timedelta

# Market Simulation Constants
ORDER_FLOW_IMBALANCE_STD = 0.3
MICROSTRUCTURE_NOISE_STD = 0.0005

# Orderbook Generation
BASE_PRICE_MIN = 0.3
BASE_PRICE_MAX = 0.7
VOLATILITY_MIN = 0.02
VOLATILITY_MAX = 0.08
VOLATILITY_SHOCK_STD = 0.01
VOLATILITY_DECAY = 0.9
VOLATILITY_SHOCK_WEIGHT = 0.1
DRIFT_DT = 0.1
PRICE_MIN = 0.01
PRICE_MAX = 0.99
VOLATILITY_FLOOR = 0.01
BASE_SPREAD = 0.02
ORDERBOOK_DEPTH = 5
TICK_SIZE = 0.01
ORDER_SIZE_MIN = 100
ORDER_SIZE_MAX = 5000
VOLUME_MIN = 50000
VOLUME_MAX = 500000

# Trade History
TRADE_PRICE_NOISE_STD = 0.001
TRADE_SIZE_MIN = 10
TRADE_SIZE_MAX = 1000
TRADE_INTERVAL_MIN = 1
TRADE_INTERVAL_MAX = 5

# PnL Simulation
PNL_WIN_RATE = 0.58
PNL_AVG_WIN = 0.02
PNL_WIN_STD = 0.01
PNL_AVG_LOSS_RET = -0.015
PNL_LOSS_STD = 0.008

class MarketMicrostructure:
    def __init__(self):
        self._vol_state = {}
        self._flow_imbalance = {}
        self._price_state = {}

    def _brownian_drift(self, current: float, volatility: float, dt: float = 1.0) -> float:
        mu = 0.0 
        sigma = volatility
        dW = random.gauss(0, math.sqrt(dt))
        return current * math.exp((mu - 0.5 * sigma**2) * dt + sigma * dW)

    def _order_flow_imbalance(self) -> float:
        """Simulate order flow imbalance (-1 to 1)"""
        return random.gauss(0, ORDER_FLOW_IMBALANCE_STD)

    def _microstructure_noise(self) -> float:
        """High-frequency tick noise"""
        return random.gauss(0, MICROSTRUCTURE_NOISE_STD)

    def synthesize_orderbook(self, market_id: str, base_price: float = None) -> Dict:
        """Generate realistic limit order book"""
        if base_price is None:
            # Check for existing state to ensure continuity
            if market_id in self._price_state:
                base_price = self._price_state[market_id]
            else:
                base_price = random.uniform(BASE_PRICE_MIN, BASE_PRICE_MAX)

        if market_id not in self._vol_state:
            self._vol_state[market_id] = random.uniform(VOLATILITY_MIN, VOLATILITY_MAX)

        current_vol = self._vol_state[market_id]
        vol_shock = random.gauss(0, VOLATILITY_SHOCK_STD)
        self._vol_state[market_id] = max(VOLATILITY_FLOOR, current_vol * VOLATILITY_DECAY + abs(vol_shock) * VOLATILITY_SHOCK_WEIGHT)

        mid_price = self._brownian_drift(base_price, current_vol, DRIFT_DT)
        mid_price = max(PRICE_MIN, min(PRICE_MAX, mid_price))

        mid_price += self._microstructure_noise()

        # Update price state for continuity
        self._price_state[market_id] = mid_price

        spread = BASE_SPREAD * (1 + abs(self._order_flow_imbalance()))

        bids = []
        asks = []

        for i in range(ORDERBOOK_DEPTH):
            bid_price = mid_price - spread / 2 - i * TICK_SIZE
            bid_size = random.randint(ORDER_SIZE_MIN, ORDER_SIZE_MAX) * (1 + random.random())
            bids.append({"price": round(bid_price, 4), "size": int(bid_size)})

            ask_price = mid_price + spread / 2 + i * TICK_SIZE
            ask_size = random.randint(ORDER_SIZE_MIN, ORDER_SIZE_MAX) * (1 + random.random())
            asks.append({"price": round(ask_price, 4), "size": int(ask_size)})

        total_volume = random.randint(VOLUME_MIN, VOLUME_MAX)

        return {
            "mid_price": round(mid_price, 4),
            "spread": round(spread, 4),
            "bids": sorted(bids, key=lambda x: x["price"], reverse=True),
            "asks": sorted(asks, key=lambda x: x["price"]),
            "total_volume": total_volume,
            "volatility": round(current_vol, 4)
        }

    def generate_trade_history(self, market_id: str, num_trades: int = 20) -> List[Dict]:
        """Generate realistic trade history"""
        trades = []
        current_time = datetime.now()

        orderbook = self.synthesize_orderbook(market_id)

        # Unused variable: current_price = orderbook["mid_price"]

        current_offset_minutes = 0
        for i in range(num_trades):
            is_buy = random.random() > 0.5
            if is_buy:
                price = random.choice(orderbook["asks"])["price"]
                price += random.gauss(0, TRADE_PRICE_NOISE_STD)
            else:
                price = random.choice(orderbook["bids"])["price"]
                price -= random.gauss(0, TRADE_PRICE_NOISE_STD)

            size = random.randint(TRADE_SIZE_MIN, TRADE_SIZE_MAX)

            # Sherlock Fix: Accumulate time offsets to ensure consistent intervals
            current_offset_minutes += random.randint(TRADE_INTERVAL_MIN, TRADE_INTERVAL_MAX)
            timestamp = current_time - timedelta(minutes=current_offset_minutes)

            trades.append({
                "price": round(price, 4),
                "size": size,
                "side": "buy" if is_buy else "sell",
                "timestamp": timestamp.isoformat()
            })

        # Optimization: Trades are generated in chronological reverse order (newest first)
        # by the loop structure above, so explicit sorting is redundant.
        # Removing sorted() converts O(N log N) to O(N).
        return trades

    def generate_pnl_path(self, initial_value: float = 1000, num_points: int = 100) -> List[Dict]:
        """Generate realistic P&L path with proper risk characteristics"""
        pnl_history = []
        current_pnl = initial_value

        for i in range(num_points):
            if random.random() < PNL_WIN_RATE:
                change_pct = random.gauss(PNL_AVG_WIN, PNL_WIN_STD)
            else:
                change_pct = random.gauss(PNL_AVG_LOSS_RET, PNL_LOSS_STD)

            current_pnl *= (1 + change_pct)

            timestamp = datetime.now() - timedelta(hours=num_points - i)
            pnl_history.append({
                "timestamp": timestamp.isoformat(),
                "pnl": round(current_pnl, 2),
                "change_pct": round(change_pct * 100, 2)
            })

        return pnl_history
