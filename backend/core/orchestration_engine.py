
from .data_pipeline import DataAcquisitionLayer, PrimaryProviderUnavailableError
from .stream_processor import StreamProcessor
from .market_synthesizer import MarketMicrostructure
from .synthetic_data import SYNTHETIC_POSITIONS
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class OrchestrationEngine:
    """Coordinates data acquisition, enrichment, and aggregation for live feeds."""

    def __init__(self):
        """Initialize orchestration dependencies."""
        self._dal = DataAcquisitionLayer()
        self._sp = StreamProcessor()
        self._mm = MarketMicrostructure()

    async def get_live_feed(self) -> Dict:
        """Build a live feed payload from goals, markets, and computed statistics.

        Returns:
            A feed payload containing events, markets, statistics, timestamp, and optional errors.
        """
        errors: List[Dict[str, str]] = []
        try:
            raw_events = await self._dal.fetch_live_goals()
        except PrimaryProviderUnavailableError as exc:
            logger.warning("Provider unavailable for live goals.", extra={"source": exc.source})
            raw_events = []
            errors.append(
                {
                    "operation": exc.operation,
                    "source": exc.source,
                    "status": str(exc.status_code) if exc.status_code is not None else "unavailable",
                    "message": exc.message,
                }
            )

        try:
            market_data = await self._dal.fetch_market_data()
        except PrimaryProviderUnavailableError as exc:
            logger.warning("Provider unavailable for market data.", extra={"source": exc.source})
            market_data = {"markets": [], "count": 0}
            errors.append(
                {
                    "operation": exc.operation,
                    "source": exc.source,
                    "status": str(exc.status_code) if exc.status_code is not None else "unavailable",
                    "message": exc.message,
                }
            )

        enriched_events = await self._sp.enrich_events(raw_events, market_data)

        stats = await self._sp.aggregate_statistics(enriched_events)

        payload = {
            "events": enriched_events,
            "markets": market_data.get("markets", []),
            "statistics": stats,
            "timestamp": enriched_events[0]["timestamp"] if enriched_events else None,
        }
        if errors:
            payload["errors"] = errors

        return payload

    async def get_market_details(self, market_id: str) -> Dict:
        """Return synthetic orderbook and recent trades for a market."""
        orderbook = self._mm.synthesize_orderbook(market_id)
        trade_history = self._mm.generate_trade_history(market_id)

        return {
            "market_id": market_id,
            "orderbook": orderbook,
            "recent_trades": trade_history,
            "timestamp": trade_history[0]["timestamp"] if trade_history else None
        }

    async def get_portfolio_status(self) -> Dict:
        """Return synthetic portfolio metrics for demo views."""
        pnl_history = self._mm.generate_pnl_path()

        # Current positions (synthetic for demo)
        positions = SYNTHETIC_POSITIONS

        return {
            "pnl_history": pnl_history,
            "current_pnl": pnl_history[-1]["pnl"] if pnl_history else 1000,
            "positions": positions,
            "total_positions": len(positions)
        }

    async def cleanup(self):
        """Release orchestration resources."""
        await self._dal.close()
