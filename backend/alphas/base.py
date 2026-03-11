import json
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class BaseAlpha:
    """Base class for alpha trading strategies containing shared logic."""

    def __init__(self):
        self.event_log: List[Dict] = []

    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event to the internal event log."""
        self.event_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data,
            }
        )

    def export_event_log(self, filepath: str):
        """Exports the event log to a JSON file."""
        import os

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.event_log, f, indent=2, default=str)
        logger.info(f"Event log exported to {filepath}")
