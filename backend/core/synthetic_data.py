"""
Centralized definitions for synthetic/simulated market data.
Used when the system is running in demonstration or auxiliary mode without real API keys.
"""

from typing import List, Dict

# Synthetic Market Scenarios used in DataAcquisitionLayer
SYNTHETIC_MARKET_SCENARIOS: List[Dict[str, float | str]] = [
    {"question": "Will Manchester City win the Premier League?", "yes_price": 0.72},
    {"question": "Will Real Madrid beat Barcelona?", "yes_price": 0.58},
    {"question": "Will Haaland score 30+ goals this season?", "yes_price": 0.65},
    {"question": "Will Liverpool finish in top 4?", "yes_price": 0.81},
]

# Synthetic Positions used in OrchestrationEngine
# These correlate with the scenarios above (market_0, market_2)
SYNTHETIC_POSITIONS: List[Dict[str, float | str | int]] = [
    {
        "market_id": "market_0",
        "question": "Will Manchester City win the Premier League?",
        "side": "yes",
        "entry_price": 0.68,
        "current_price": 0.72,
        "size": 100,
        "pnl": 4.0
    },
    {
        "market_id": "market_2",
        "question": "Will Haaland score 30+ goals this season?",
        "side": "yes",
        "entry_price": 0.63,
        "current_price": 0.65,
        "size": 150,
        "pnl": 3.0
    }
]
