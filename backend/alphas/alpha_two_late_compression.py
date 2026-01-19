
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

# --- SOCCER CONSTANTS ---
SOCCER_EXPECTED_GOALS_FACTOR = 2.7
SOCCER_GAME_DURATION_SECONDS = 5400  # 90 minutes

# --- CONFIDENCE CONSTANTS ---
CONFIDENCE_MAX = 0.99
CONFIDENCE_VERY_HIGH = 0.98
CONFIDENCE_HIGH = 0.95
CONFIDENCE_MEDIUM = 0.90
CONFIDENCE_MODERATE = 0.85
CONFIDENCE_LOW = 0.70
CONFIDENCE_NEUTRAL = 0.50

# --- TIME THRESHOLDS (Seconds) ---
TIME_THRESHOLD_LATE = 600  # 10 minutes
TIME_THRESHOLD_VERY_LATE = 300  # 5 minutes
TIME_THRESHOLD_CRITICAL = 120  # 2 minutes

class MarketStatus(Enum):
    ACTIVE = "active"
    CLOSING_SOON = "closing_soon" 
    FINAL_SECONDS = "final_seconds"  
    RESOLVED = "resolved"


@dataclass
class ClippingOpportunity:
    opportunity_id: str
    market_id: str
    market_question: str
    fixture_id: int
    
    # Current state
    yes_price: float
    no_price: float
    spread: float
    
    expected_outcome: str  
    confidence: float 
    expected_profit_pct: float
    
    
    seconds_to_resolution: int
    recommended_side: str
    recommended_price: float
    recommended_size: float

    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "opportunity_id": self.opportunity_id,
            "market_id": self.market_id,
            "market_question": self.market_question,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "expected_outcome": self.expected_outcome,
            "confidence": self.confidence,
            "expected_profit_pct": self.expected_profit_pct,
            "seconds_to_resolution": self.seconds_to_resolution,
            "recommended_side": self.recommended_side,
            "recommended_price": self.recommended_price,
            "recommended_size": self.recommended_size
        }


@dataclass
class ClippingTrade:
    trade_id: str
    opportunity: ClippingOpportunity
    entry_time: datetime
    entry_price: float
    size_usd: float
    
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    actual_outcome: Optional[str] = None
    pnl: float = 0.0


@dataclass
class AlphaTwoStats:
    opportunities_detected: int = 0
    trades_executed: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    false_positives: int = 0  


class AlphaTwoLateCompression:
  
    
    # Markets to avoid (high dispute risk)
    AVOIDED_MARKET_TYPES = [
        "political",
        "crypto",
        "weather",
        "entertainment"
    ]
    
    def __init__(
        self,
        polymarket_client=None,
        kalshi_client=None,
        simulation_mode: bool = True
    ):
        self.polymarket = polymarket_client
        self.kalshi = kalshi_client
        self.simulation_mode = simulation_mode
        
        self.min_confidence = float(os.getenv("CLIP_MIN_CONFIDENCE", "0.95"))
        self.max_trade_size = float(os.getenv("CLIP_MAX_SIZE_USD", "50"))
        self.min_profit_threshold = float(os.getenv("CLIP_MIN_PROFIT_PCT", "3"))  
        self.max_seconds_to_close = int(os.getenv("CLIP_MAX_SECONDS", "300")) 
        self.monitored_markets: Dict[str, Dict] = {} 
        self.active_opportunities: Dict[str, ClippingOpportunity] = {}
        self.trades: Dict[str, ClippingTrade] = {}
        self.active_trade_market_ids: Set[str] = set()
        self.pending_orders: Set[str] = set()
        self.closed_trades: List[ClippingTrade] = []
        self.stats = AlphaTwoStats()
        
        self.event_log: List[Dict] = []
        
        self.running = False
        
        logger.info(f"Alpha Two initialized (simulation={simulation_mode})")
        logger.info(f"  Min confidence: {self.min_confidence}")
        logger.info(f"  Max trade size: ${self.max_trade_size}")
        logger.info(f"  Min profit threshold: {self.min_profit_threshold}%")

    async def start(self):
        self.running = True
        logger.info("Starting Alpha Two - Late Compression Strategy")
        
        tasks = [
            asyncio.create_task(self._market_scanner_loop()),
            asyncio.create_task(self._opportunity_detector_loop()),
            asyncio.create_task(self._execution_loop()),
            asyncio.create_task(self._resolution_monitor_loop())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        self.running = False
        logger.info("Alpha Two stopped")

    async def _market_scanner_loop(self):
        while self.running:
            try:
                closing_markets = await self._fetch_closing_markets()
                
                for market in closing_markets:
                    market_id = market.get("market_id")
                    seconds_to_close = market.get("seconds_to_close", 999999)
                    
                    if seconds_to_close <= self.max_seconds_to_close:
                        self.monitored_markets[market_id] = market
                        logger.debug(f"Monitoring market {market_id}: {seconds_to_close}s to close")
                
                resolved = [
                    mid for mid, m in self.monitored_markets.items()
                    if m.get("status") == "resolved"
                ]

                # Check for active trades on these markets
                for mid in resolved:
                    if mid not in self.active_trade_market_ids:
                        del self.monitored_markets[mid]
                
                await asyncio.sleep(10)  
                
            except Exception as e:
                logger.error(f"Market scanner error: {e}")
                await asyncio.sleep(10)

    async def _opportunity_detector_loop(self):
        
        while self.running:
            try:
                for market_id, market in list(self.monitored_markets.items()):
                    opportunity = await self._analyze_market_for_clipping(market)
                    
                    if opportunity:
                        self.active_opportunities[opportunity.opportunity_id] = opportunity
                        self.stats.opportunities_detected += 1
                        
                        self._log_event("opportunity_detected", opportunity.to_dict())
                        
                        logger.info(f"CLIPPING OPPORTUNITY: {opportunity.opportunity_id}")
                        logger.info(f"  Market: {opportunity.market_question}")
                        logger.info(f"  Expected: {opportunity.expected_outcome}")
                        logger.info(f"  Current price: {opportunity.yes_price:.4f}")
                        logger.info(f"  Confidence: {opportunity.confidence:.2f}")
                        logger.info(f"  Expected profit: {opportunity.expected_profit_pct:.1f}%")
                        logger.info(f"  Seconds to resolution: {opportunity.seconds_to_resolution}")
                
                await asyncio.sleep(2)  
                
            except Exception as e:
                logger.error(f"Opportunity detector error: {e}")
                await asyncio.sleep(2)

    async def _execution_loop(self):
        while self.running:
            try:
                for opp_id, opportunity in list(self.active_opportunities.items()):
                    if opportunity.confidence < self.min_confidence:
                        continue
                    
                    if opportunity.expected_profit_pct < self.min_profit_threshold:
                        continue
                    
                    if opp_id in self.trades:
                        continue
                    
                    await self._execute_clipping_trade(opportunity)
                    
                    
                    del self.active_opportunities[opp_id]
                
                await asyncio.sleep(0.5)  
                
            except Exception as e:
                logger.error(f"Execution loop error: {e}")
                await asyncio.sleep(1)

    async def _resolution_monitor_loop(self):
        while self.running:
            try:
                for trade_id, trade in list(self.trades.items()):
                    if trade.resolved:
                        continue
                    
                    resolution = await self._check_market_resolution(
                        trade.opportunity.market_id
                    )
                    
                    if resolution:
                        await self._process_trade_resolution(trade, resolution)
                
                await asyncio.sleep(5)  
                
            except Exception as e:
                logger.error(f"Resolution monitor error: {e}")
                await asyncio.sleep(5)

    async def _fetch_closing_markets(self) -> List[Dict]:
        """Fetch markets that are closing soon"""
        markets = []
        
        if self.polymarket:
            try:
                poly_markets = await self._fetch_polymarket_closing_markets()
                markets.extend(poly_markets)
            except Exception as e:
                logger.error(f"Polymarket fetch error: {e}")
        
        if self.kalshi:
            try:
                kalshi_markets = await self._fetch_kalshi_closing_markets()
                markets.extend(kalshi_markets)
            except Exception as e:
                logger.error(f"Kalshi fetch error: {e}")
        
        return markets

    async def _fetch_polymarket_closing_markets(self) -> List[Dict]:
        
        #  Daniel NOTE: This would query Polymarket API for markets with close_time approaching
        # For now this return empty we would implement with actual API
        return []

    async def _fetch_kalshi_closing_markets(self) -> List[Dict]:
        # Daniel Note: This would query Kalshi API for markets with close_time approaching
        return []

    async def _analyze_market_for_clipping(self, market: Dict) -> Optional[ClippingOpportunity]:

        market_id = market.get("market_id")

        # Check if we have a pending order execution for this market
        if market_id in self.pending_orders:
            return None

        # Check if we already have an active trade for this market
        if market_id in self.active_trade_market_ids:
            return None

        question = market.get("question", "")
        fixture_id = market.get("fixture_id", 0)
        
        # Get current prices
        yes_price = market.get("yes_price", 0.5)
        no_price = market.get("no_price", 0.5)
        spread = abs(yes_price - no_price)
        
        seconds_to_close = market.get("seconds_to_close", 999999)
        
        outcome_analysis = await self._predict_outcome(market)
        
        if not outcome_analysis:
            return None
        
        expected_outcome = outcome_analysis["outcome"]  
        confidence = outcome_analysis["confidence"]
        
        if confidence < self.min_confidence:
            return None
        
        if expected_outcome == "YES":
            current_price = yes_price
            target_price = 1.0
        else:
            current_price = no_price
            target_price = 1.0
        
        # Sherlock: Fix Division by Zero risk
        if current_price <= 0.001:
            return None

        expected_profit_pct = ((target_price - current_price) / current_price) * 100
        
        if expected_profit_pct < self.min_profit_threshold:
            return None
        
        return ClippingOpportunity(
            opportunity_id=f"clip_{market_id}_{int(datetime.now().timestamp())}",
            market_id=market_id,
            market_question=question,
            fixture_id=fixture_id,
            yes_price=yes_price,
            no_price=no_price,
            spread=spread,
            expected_outcome=expected_outcome,
            confidence=confidence,
            expected_profit_pct=expected_profit_pct,
            seconds_to_resolution=seconds_to_close,
            recommended_side=expected_outcome,
            recommended_price=current_price,
            recommended_size=min(
                self.max_trade_size,
                self.max_trade_size * confidence 
            )
        )

    async def _predict_outcome(self, market: Dict) -> Optional[Dict]:
    
        market_type = market.get("type", "unknown")
        
        if market_type not in ["soccer", "football", "basketball", "baseball"]:
            return None
        
        current_score = market.get("current_score", {})
        time_remaining = market.get("seconds_to_close", 999999)
        
        home_score = current_score.get("home", 0)
        away_score = current_score.get("away", 0)
        
        question = market.get("question", "").lower()
        
        if "win" in question:
            if home_score > away_score:
                if "home" in question or market.get("home_team", "").lower() in question:
                    confidence = self._calculate_lead_confidence(
                        home_score - away_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "YES", "confidence": confidence}
                else:
                    confidence = self._calculate_lead_confidence(
                        home_score - away_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "NO", "confidence": confidence}
            
            elif away_score > home_score:
                
                if "away" in question or market.get("away_team", "").lower() in question:
                    confidence = self._calculate_lead_confidence(
                        away_score - home_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "YES", "confidence": confidence}
                else:
                    confidence = self._calculate_lead_confidence(
                        away_score - home_score,
                        time_remaining,
                        market_type
                    )
                    return {"outcome": "NO", "confidence": confidence}

            else:
                # DRAW CASE (Scores Equal)
                # If the market is checking for a "Win", a Draw means NO.
                # Specifically needed for Trade Resolution when match ends in Draw.
                if market.get("status") == "resolved" or time_remaining <= 0:
                    return {"outcome": "NO", "confidence": 1.0}

                # Sherlock Fix: Also evaluate active Draws. If it's a draw late in the game,
                # the chance of a specific team winning is low -> outcome NO.
                confidence = self._calculate_lead_confidence(
                    0,
                    time_remaining,
                    market_type
                )
                return {"outcome": "NO", "confidence": confidence}
        
        return None

    def _calculate_lead_confidence(
        self,
        lead_margin: int,
        seconds_remaining: int,
        sport: str
    ) -> float:
        
        if sport == "soccer":
            return self._calculate_soccer_confidence(lead_margin, seconds_remaining)
        
        elif sport in ["basketball", "baseball"]:
            if sport == "basketball":
                points_per_second = 0.04 
            else:
                points_per_second = 0.003  
            
            expected_swing = points_per_second * seconds_remaining * 2
            
            if lead_margin > expected_swing * 1.5:
                confidence = 0.98
            elif lead_margin > expected_swing:
                confidence = 0.90
            else:
                confidence = 0.60
        
        else:
            confidence = 0.50  
        
        return min(0.99, confidence)

    def _calculate_soccer_confidence(self, lead_margin: int, seconds_remaining: int) -> float:
        """
        Calculates confidence for soccer matches based on lead margin and remaining time.
        """
        # Note: This variable was unused in the original code, but I'll keep the logic if it's needed for future extensions
        # expected_goals = (seconds_remaining / SOCCER_GAME_DURATION_SECONDS) * SOCCER_EXPECTED_GOALS_FACTOR

        if lead_margin >= 3:
            return CONFIDENCE_MAX
        elif lead_margin == 2:
            if seconds_remaining < TIME_THRESHOLD_VERY_LATE:
                return CONFIDENCE_VERY_HIGH
            elif seconds_remaining < TIME_THRESHOLD_LATE:
                return CONFIDENCE_HIGH
            else:
                return CONFIDENCE_MEDIUM
        elif lead_margin == 1:
            if seconds_remaining < TIME_THRESHOLD_CRITICAL:
                return CONFIDENCE_HIGH
            elif seconds_remaining < TIME_THRESHOLD_VERY_LATE:
                return CONFIDENCE_MODERATE
            else:
                return CONFIDENCE_LOW
        elif lead_margin == 0:
            # DRAW Logic: High confidence "NO Win" only if very close to end
            if seconds_remaining < TIME_THRESHOLD_CRITICAL:
                return CONFIDENCE_HIGH
            return CONFIDENCE_NEUTRAL
        else:
            return CONFIDENCE_NEUTRAL

    async def _execute_clipping_trade(self, opportunity: ClippingOpportunity):
        trade = ClippingTrade(
            trade_id=opportunity.opportunity_id,
            opportunity=opportunity,
            entry_time=datetime.now(),
            entry_price=opportunity.recommended_price,
            size_usd=opportunity.recommended_size
        )
        
        if self.simulation_mode:
            
            self.trades[trade.trade_id] = trade
            self.active_trade_market_ids.add(opportunity.market_id)
            self.stats.trades_executed += 1
            
            self._log_event("trade_executed_simulation", {
                "trade_id": trade.trade_id,
                "entry_price": trade.entry_price,
                "size_usd": trade.size_usd,
                "expected_profit": opportunity.expected_profit_pct
            })
            
            logger.info(f"[SIMULATION] Clipping trade executed: {trade.trade_id}")
            logger.info(f"  Entry: {trade.entry_price:.4f}")
            logger.info(f"  Size: ${trade.size_usd:.2f}")
            logger.info(f"  Expected profit: {opportunity.expected_profit_pct:.1f}%")
        
        else:
            # Mark as pending to prevent duplicate signals during async execution
            self.pending_orders.add(opportunity.market_id)
            try:
                success = await self._place_exchange_order(opportunity)

                if success:
                    self.trades[trade.trade_id] = trade
                    self.active_trade_market_ids.add(opportunity.market_id)
                    self.stats.trades_executed += 1
                    logger.info(f"[LIVE] Clipping trade executed: {trade.trade_id}")
                else:
                    logger.error(f"Failed to execute clipping trade: {trade.trade_id}")
            finally:
                if opportunity.market_id in self.pending_orders:
                    self.pending_orders.remove(opportunity.market_id)

    async def _place_exchange_order(self, opportunity: ClippingOpportunity) -> bool:
        if self.polymarket:
            try:
                """
                # Daniel NOTE: Would need to implement actual order placement
                # result = await self.polymarket.place_order(...)
                """
                return False  #THIS IS THE PLACEHOLDER
            except Exception as e:
                logger.error(f"Polymarket order error: {e}")
        
        if self.kalshi:
            try:
                # Same For THIS result = await self.kalshi.place_order(...)
                return False  # Placeholder
            except Exception as e:
                logger.error(f"Kalshi order error: {e}")
        
        return False

    async def _check_market_resolution(self, market_id: str) -> Optional[Dict]:
        """
        # DANIEL NOTE: In production: Query exchange for resolution status
        # Return {"outcome": "YES"|"NO", "resolution_time": datetime}
        """
        if self.simulation_mode:
            market = self.monitored_markets.get(market_id)
            if market and market.get("status") == "resolved":
                # Determine outcome based on final score
                outcome_analysis = await self._predict_outcome(market)
                if outcome_analysis:
                    return {
                        "outcome": outcome_analysis["outcome"],
                        "resolution_time": datetime.now()
                    }

        return None

    async def _process_trade_resolution(self, trade: ClippingTrade, resolution: Dict):
        trade.resolved = True
        trade.resolution_time = resolution.get("resolution_time", datetime.now())
        trade.actual_outcome = resolution.get("outcome")
        
        if trade.actual_outcome == trade.opportunity.expected_outcome:
            # Sherlock: Fix Division by Zero risk
            if trade.entry_price > 0.001:
                trade.pnl = (1.0 - trade.entry_price) * trade.size_usd / trade.entry_price
            else:
                # If we somehow entered at 0, treat it as pure profit on the size?
                # Or just protect the crash.
                trade.pnl = trade.size_usd

            self.stats.trades_won += 1
        else:
            trade.pnl = -trade.size_usd
            self.stats.trades_lost += 1
            self.stats.false_positives += 1
        
        self.stats.total_pnl += trade.pnl
        
        total = self.stats.trades_won + self.stats.trades_lost
        self.stats.win_rate = self.stats.trades_won / total if total > 0 else 0
        self.stats.avg_profit_per_trade = self.stats.total_pnl / total if total > 0 else 0
        
        del self.trades[trade.trade_id]

        # Only remove from set if no other trades for this market exist
        # (Handles edge case where multiple trades might exist for same market)
        has_active = any(t.opportunity.market_id == trade.opportunity.market_id for t in self.trades.values())
        if not has_active:
            self.active_trade_market_ids.discard(trade.opportunity.market_id)

        self.closed_trades.append(trade)
        
        self._log_event("trade_resolved", {
            "trade_id": trade.trade_id,
            "expected_outcome": trade.opportunity.expected_outcome,
            "actual_outcome": trade.actual_outcome,
            "pnl": trade.pnl
        })
        
        logger.info(f"Trade resolved: {trade.trade_id}")
        logger.info(f"  Expected: {trade.opportunity.expected_outcome}")
        logger.info(f"  Actual: {trade.actual_outcome}")
        logger.info(f"  P&L: ${trade.pnl:.2f}")


    
    async def feed_live_fixture_update(self, fixture_data: Dict):
        
        minute = fixture_data.get("minute", 0)
        status = fixture_data.get("status", "")
        market_id = fixture_data.get("market_id", f"fixture_{fixture_data['fixture_id']}")
        
        # Handle Match End / Resolution
        if status in ["FT", "AET", "PEN"]:
            if market_id in self.monitored_markets:
                logger.info(f"Market {market_id} ended (Status: {status}). Marking resolved.")
                self.monitored_markets[market_id]["status"] = "resolved"
                # Update final score
                self.monitored_markets[market_id]["current_score"] = {
                    "home": fixture_data.get("home_score", 0),
                    "away": fixture_data.get("away_score", 0)
                }
                # Set seconds to 0 to ensure logic downstream treats it as over
                self.monitored_markets[market_id]["seconds_to_close"] = 0
            return
        
       
        total_minutes = 90
        if status == "HT":
            seconds_remaining = (total_minutes - 45) * 60
        elif status == "ET":
            # Extra Time is typically 30 mins (90 -> 120)
            # Use max(0, ...) to avoid negative if it goes beyond 120 in stoppage of ET
            et_total_minutes = 120
            # If minute < 90, something is weird, but we assume it's at least 90
            current_minute = max(90, minute)
            seconds_remaining = (et_total_minutes - current_minute) * 60

            # Handle ET Stoppage Time: If minute >= 120 but status is still ET
            if seconds_remaining <= 0:
                 seconds_remaining = 60
        else:
            # Regular Time (90 minutes) logic
            # Sherlock Fix: Handle Stoppage Time conservatively.
            # If minute >= 90 but status is still active (e.g. "2H"), we are in stoppage time.
            # Since we don't know the exact added time, we assume a conservative buffer (e.g., 8 minutes total).
            # This prevents assuming "1 minute left" and triggering high-risk trades prematurely.

            # Sherlock Fix: Modern soccer often has >10m stoppage.
            # If we assume 8m and it goes to 12m, we incorrectly treat minutes 98-102 as "60s left",
            # triggering high-confidence trades during high-volatility moments.
            STOPPAGE_BUFFER_MINUTES = 13

            if minute >= 90 and status not in ["FT", "AET", "PEN"]:
                stoppage_end_minute = 90 + STOPPAGE_BUFFER_MINUTES

                if minute >= stoppage_end_minute:
                    # If we exceeded our buffer, we are in "Deep Unknown Stoppage".
                    # Treat as 5 minutes remaining (300s) to force CONFIDENCE_NEUTRAL
                    # instead of artificially clamping to 60s (CONFIDENCE_HIGH).
                    seconds_remaining = 300
                else:
                    seconds_remaining = (stoppage_end_minute - minute) * 60
                    seconds_remaining = max(60, seconds_remaining)
            else:
                seconds_remaining = (total_minutes - minute) * 60
                seconds_remaining = max(0, seconds_remaining)
        
    
        market = {
            "market_id": fixture_data.get("market_id", f"fixture_{fixture_data['fixture_id']}"),
            "question": fixture_data.get("question", ""),
            "fixture_id": fixture_data.get("fixture_id"),
            "type": "soccer",
            "home_team": fixture_data.get("home_team"),
            "away_team": fixture_data.get("away_team"),
            "current_score": {
                "home": fixture_data.get("home_score", 0),
                "away": fixture_data.get("away_score", 0)
            },
            "seconds_to_close": seconds_remaining,
            "yes_price": fixture_data.get("yes_price", 0.5),
            "no_price": fixture_data.get("no_price", 0.5),
            "status": "active" if seconds_remaining > 0 else "resolved"
        }
        
        self.monitored_markets[market["market_id"]] = market
        
        if seconds_remaining <= self.max_seconds_to_close:
            opportunity = await self._analyze_market_for_clipping(market)
            
            if opportunity:
                logger.info(f"Clipping opportunity from live fixture: {opportunity.opportunity_id}")
                self.active_opportunities[opportunity.opportunity_id] = opportunity
                self.stats.opportunities_detected += 1

    def _log_event(self, event_type: str, data: Dict):
        self.event_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })

    def get_stats(self) -> AlphaTwoStats:
        return self.stats

    def export_event_log(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.event_log, f, indent=2, default=str)
        logger.info(f"Event log exported to {filepath}")
