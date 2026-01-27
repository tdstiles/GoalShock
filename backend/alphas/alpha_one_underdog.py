
import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

# --- CONFIGURATION CONSTANTS ---
DEFAULT_UNDERDOG_THRESHOLD = 0.45
DEFAULT_MAX_TRADE_SIZE = 500.0
DEFAULT_MAX_POSITIONS = 5
DEFAULT_TAKE_PROFIT_PCT = 15.0
DEFAULT_STOP_LOSS_PCT = 10.0
DEFAULT_MAX_DAILY_LOSS = 2000.0

# --- CONFIDENCE CALCULATION CONSTANTS ---
MIN_CONFIDENCE = 0.3
MAX_CONFIDENCE = 1.0
ODDS_FACTOR_FLOOR = 0.3
TIME_FACTOR_EARLY_FLOOR = 0.7
TIME_FACTOR_EARLY_SLOPE = 0.3
TIME_FACTOR_LATE_FLOOR = 0.5
TIME_FACTOR_LATE_SLOPE = 0.5
MARGIN_FACTOR_BASE = 0.7
MARGIN_FACTOR_SLOPE = 0.15
EARLY_GAME_MINUTE = 30
LATE_GAME_MINUTE = 70
LATE_GAME_DURATION = 20

# --- SIMULATION CONSTANTS ---
SIM_ANNUAL_VOLATILITY = 0.5
SIM_SECONDS_IN_DAY = 24 * 3600
SIM_PRICE_CEILING = 0.99
SIM_PRICE_FLOOR = 0.01
SIM_DRIFT_THRESHOLD_HIGH = 0.9
SIM_DRIFT_THRESHOLD_LOW = 0.1
SIM_DRIFT_FACTOR = 0.001
SIM_BASE_LEAD_PRICE = 0.45
SIM_TIME_COMPONENT_WEIGHT = 0.40
SIM_MARGIN_COMPONENT_WEIGHT = 0.15
SIM_ODDS_MULTIPLIER = 1.5
MATCH_DURATION_MINUTES = 90.0

# --- MARKET PRICE CONSTANTS ---
MARKET_PRICE_MULTIPLIER_BACKUP = 1.2

class TradingMode(Enum):
    SIMULATION = "simulation"
    LIVE = "live"


@dataclass
class TradeSignal:
    signal_id: str
    fixture_id: int
    team: str
    side: str  
    entry_price: float
    target_price: float
    stop_loss_price: float
    size_usd: float
    confidence: float  
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SimulatedPosition:
    position_id: str
    signal: TradeSignal
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    status: str = "open"
    last_price: Optional[float] = None
    last_update_time: Optional[datetime] = None
    token_id: Optional[str] = None
    quantity: Optional[float] = None


@dataclass
class AlphaOneStats:
    total_signals: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    sharpe_ratio: float = 0.0


class AlphaOneUnderdog:
   
    
    def __init__(
        self,
        mode: TradingMode = TradingMode.SIMULATION,
        polymarket_client=None,
        kalshi_client=None
    ):
        self.mode = mode
        self.polymarket = polymarket_client
        self.kalshi = kalshi_client
        
        self.underdog_threshold = float(os.getenv("UNDERDOG_THRESHOLD", str(DEFAULT_UNDERDOG_THRESHOLD)))
        self.max_trade_size = float(os.getenv("MAX_TRADE_SIZE_USD", str(DEFAULT_MAX_TRADE_SIZE)))
        self.max_positions = int(os.getenv("MAX_POSITIONS", str(DEFAULT_MAX_POSITIONS)))
        self.take_profit_pct = float(os.getenv("TAKE_PROFIT_PERCENT", str(DEFAULT_TAKE_PROFIT_PCT)))
        self.stop_loss_pct = float(os.getenv("STOP_LOSS_PERCENT", str(DEFAULT_STOP_LOSS_PCT)))
        self.max_daily_loss = float(os.getenv("MAX_DAILY_LOSS_USD", str(DEFAULT_MAX_DAILY_LOSS)))
        
        self.pre_match_odds: Dict[int, Dict[str, float]] = {}  
        self.positions: Dict[str, SimulatedPosition] = {}
        self.closed_positions: List[SimulatedPosition] = []
        self.daily_pnl = 0.0
        self.stats = AlphaOneStats()

        # Cache for token IDs to avoid expensive search calls
        # Key: (fixture_id, team_name) -> Value: token_id
        self.token_map: Dict[tuple, str] = {}
        
        self.event_log: List[Dict] = []
        
        logger.info(f"Alpha One initialized in {mode.value} mode")
        logger.info(f"  Underdog threshold: {self.underdog_threshold}")
        logger.info(f"  Max trade size: ${self.max_trade_size}")
        logger.info(f"  Take profit: {self.take_profit_pct}%")
        logger.info(f"  Stop loss: {self.stop_loss_pct}%")

    async def cache_pre_match_odds(self, fixture_id: int, odds: Dict[str, float]):
       
        self.pre_match_odds[fixture_id] = odds
        
      
        underdog = min(odds.items(), key=lambda x: x[1])
        
        self._log_event("odds_cached", {
            "fixture_id": fixture_id,
            "odds": odds,
            "underdog": underdog[0],
            "underdog_odds": underdog[1]
        })
        
        logger.info(f"Cached odds for fixture {fixture_id}: underdog = {underdog[0]} @ {underdog[1]:.2f}")

    async def on_goal_event(self, goal_event) -> Optional[TradeSignal]:
       
        fixture_id = goal_event.fixture_id
        scoring_team = goal_event.team
        home_team = goal_event.home_team
        away_team = goal_event.away_team
        home_score = goal_event.home_score
        away_score = goal_event.away_score
        minute = goal_event.minute
        
        self._log_event("goal_received", goal_event.to_dict() if hasattr(goal_event, 'to_dict') else vars(goal_event))
        
        if fixture_id not in self.pre_match_odds:
            logger.debug(f"No pre-match odds for fixture {fixture_id}")
            return None
        
        odds = self.pre_match_odds[fixture_id]
        
       
        team_odds_map = self._map_odds_to_teams(odds, home_team, away_team)
        
        if not team_odds_map:
            logger.warning(f"Could not map teams to odds for fixture {fixture_id}")
            return None
        
        underdog_team = min(team_odds_map.items(), key=lambda x: x[1])[0]
        underdog_odds = team_odds_map[underdog_team]
        
        if scoring_team != underdog_team:
            logger.debug(f"Goal by favorite ({scoring_team}), not underdog ({underdog_team})")
            self._log_event("goal_by_favorite", {
                "scoring_team": scoring_team,
                "underdog": underdog_team
            })
            return None
        
        logger.info(f"Underdog {underdog_team} scored!")
        
        if underdog_team == home_team:
            underdog_score = home_score
            favorite_score = away_score
        else:
            underdog_score = away_score
            favorite_score = home_score
        
        is_leading = underdog_score > favorite_score
        
        if not is_leading:
            logger.info(f"Underdog scored but not leading: {underdog_score}-{favorite_score}")
            self._log_event("underdog_not_leading", {
                "underdog": underdog_team,
                "underdog_score": underdog_score,
                "favorite_score": favorite_score
            })
            return None
        
        logger.info(f"Underdog {underdog_team} is NOW LEADING {underdog_score}-{favorite_score}!")
        
        if underdog_odds > self.underdog_threshold:
            logger.info(f"Underdog odds {underdog_odds:.2f} above threshold {self.underdog_threshold}")
            return None
        
        if len(self.positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached")
            return None
        
        if self.daily_pnl <= -self.max_daily_loss:
            logger.warning(f"Daily loss limit (${self.max_daily_loss}) reached")
            return None
        
        existing = [p for p in self.positions.values() if p.signal.fixture_id == fixture_id]
        if existing:
            logger.debug(f"Already have position on fixture {fixture_id}")
            return None
        
        current_price = await self._get_current_market_price(fixture_id, underdog_team)
        
        if current_price is None:
            logger.warning(f"Could not get market price for {underdog_team}")
            # Sherlock Fix: More realistic simulation pricing.
            # When underdog leads, price jumps significantly, not just 1.2x pre-match odds.

            # Base price for taking the lead (approx 0.45 usually)
            base_lead_price = SIM_BASE_LEAD_PRICE

            # Time decay factor: Price increases as time runs out (if leading)
            time_progression = minute / MATCH_DURATION_MINUTES
            time_component = time_progression * SIM_TIME_COMPONENT_WEIGHT  # Adds up to SIM_TIME_COMPONENT_WEIGHT by end of game

            # Margin factor: Extra cushion for bigger leads (e.g. 2-0 vs 1-0)
            lead_margin = underdog_score - favorite_score
            margin_component = (lead_margin - 1) * SIM_MARGIN_COMPONENT_WEIGHT

            estimated_price = base_lead_price + time_component + margin_component

            # Clamp between SIM_PRICE_FLOOR and SIM_PRICE_CEILING, but ensure it's at least significantly higher than pre-match odds
            current_price = max(underdog_odds * SIM_ODDS_MULTIPLIER, min(SIM_PRICE_CEILING, estimated_price))

        
        confidence = self._calculate_confidence(underdog_odds, minute, underdog_score - favorite_score)
        adjusted_size = self.max_trade_size * confidence
        
     
        # Sherlock Fix: Clamp target price to ceiling.
        # If target price exceeds 1.0 (or simulated ceiling), it is unreachable, causing stuck positions.
        target_price = min(SIM_PRICE_CEILING, current_price * (1 + self.take_profit_pct / 100))

        signal = TradeSignal(
            signal_id=f"alpha1_{fixture_id}_{int(datetime.now().timestamp())}",
            fixture_id=fixture_id,
            team=underdog_team,
            side="YES",
            entry_price=current_price,
            target_price=target_price,
            stop_loss_price=current_price * (1 - self.stop_loss_pct / 100),
            size_usd=adjusted_size,
            confidence=confidence,
            reason=f"Underdog {underdog_team} (pre-match odds: {underdog_odds:.2f}) now leading {underdog_score}-{favorite_score}"
        )
        
        self.stats.total_signals += 1
        
        self._log_event("signal_generated", {
            "signal_id": signal.signal_id,
            "team": underdog_team,
            "entry_price": current_price,
            "confidence": confidence,
            "size_usd": adjusted_size
        })
        
        logger.info(f"SIGNAL GENERATED: {signal.signal_id}")
        logger.info(f"  Team: {underdog_team}")
        logger.info(f"  Entry: {current_price:.4f} ({current_price*100:.1f}%)")
        logger.info(f"  Target: {signal.target_price:.4f}")
        logger.info(f"  Stop: {signal.stop_loss_price:.4f}")
        logger.info(f"  Size: ${adjusted_size:.2f}")
        logger.info(f"  Confidence: {confidence:.2f}")
        
       
        await self._execute_trade(signal)
        
        return signal

    def _map_odds_to_teams(self, odds: Dict[str, float], home_team: str, away_team: str) -> Dict[str, float]:
        """
        Maps team names to odds values using fuzzy matching on the odds keys.
        """
        team_odds_map = {}

        # Pre-compute lower case strings to avoid re-computation in loop
        home_lower = home_team.lower()
        away_lower = away_team.lower()

        for key, value in odds.items():
            key_lower = key.lower()

            if "home" in key_lower or home_lower in key_lower:
                team_odds_map[home_team] = value
            elif "away" in key_lower or away_lower in key_lower:
                team_odds_map[away_team] = value

        return team_odds_map

    def _calculate_confidence(self, pre_match_odds: float, minute: int, lead_margin: int) -> float:
        # Sherlock Fix: Previous logic was inverted (1 - ...), favoring weaker underdogs.
        # We want higher confidence for stronger underdogs (odds closer to threshold).
        odds_ratio = pre_match_odds / self.underdog_threshold
        odds_factor = max(ODDS_FACTOR_FLOOR, min(1.0, odds_ratio))
        
        if minute < EARLY_GAME_MINUTE:
            time_factor = TIME_FACTOR_EARLY_FLOOR + (minute / EARLY_GAME_MINUTE) * TIME_FACTOR_EARLY_SLOPE
        elif minute < LATE_GAME_MINUTE:
            time_factor = 1.0
        else:
            time_factor = max(TIME_FACTOR_LATE_FLOOR, 1 - (minute - LATE_GAME_MINUTE) / LATE_GAME_DURATION * TIME_FACTOR_LATE_SLOPE)
        
        margin_factor = min(1.0, MARGIN_FACTOR_BASE + lead_margin * MARGIN_FACTOR_SLOPE)
        
        confidence = odds_factor * time_factor * margin_factor
        
        return min(MAX_CONFIDENCE, max(MIN_CONFIDENCE, confidence))

    async def _get_current_market_price(self, fixture_id: int, team: str) -> Optional[float]:
        # Shadow Mode: Even in simulation, try to fetch real prices if clients are available
        
        if self.polymarket:
            try:
                # Check cache first
                cache_key = (fixture_id, team)
                token_id = self.token_map.get(cache_key)

                if not token_id:
                    # Search for market
                    markets = await self.polymarket.get_markets_by_event(f"{team} to win")
                    if markets:
                        market = markets[0]
                        token_id = market.get("clobTokenIds", [None])[0]
                        if token_id:
                            self.token_map[cache_key] = token_id

                if token_id:
                    price = await self.polymarket.get_yes_price(token_id)
                    if price is not None:
                        return price
            except Exception as e:
                # Log only if verbose, as this might happen frequently in offline mode
                logger.debug(f"Polymarket price fetch error: {e}")
        
        if self.kalshi:
            try:
           
                pass
            except Exception as e:
                logger.error(f"Kalshi price fetch error: {e}")
        
        return None

    async def _execute_trade(self, signal: TradeSignal):
        if self.mode == TradingMode.SIMULATION:
            await self._execute_simulation_trade(signal)
        else:
            await self._execute_live_trade(signal)

    async def _execute_simulation_trade(self, signal: TradeSignal):
        # Capture token_id if we have it cached, to facilitate price tracking
        token_id = self.token_map.get((signal.fixture_id, signal.team))

        position = SimulatedPosition(
            position_id=signal.signal_id,
            signal=signal,
            entry_time=datetime.now(),
            last_price=signal.entry_price,
            last_update_time=datetime.now(),
            token_id=token_id,
            # In simulation, we assume full fill at the requested size
            quantity=signal.size_usd / signal.entry_price if signal.entry_price > 0 else 0
        )
        
        self.positions[signal.signal_id] = position
        self.stats.total_trades += 1
        
        self._log_event("trade_executed_simulation", {
            "position_id": position.position_id,
            "entry_price": signal.entry_price,
            "size_usd": signal.size_usd
        })
        
        logger.info(f"[SIMULATION] Trade executed: {signal.signal_id}")

    async def _execute_live_trade(self, signal: TradeSignal):
        if not self.polymarket and not self.kalshi:
            logger.error("No exchange client configured for live trading")
            return
        
        if self.polymarket:
            try:
                markets = await self.polymarket.get_markets_by_event(f"{signal.team} to win")
                if markets:
                    market = markets[0]
                    token_id = market.get("clobTokenIds", [None])[0]
                    
                    if token_id:
                        # Sherlock Fix: Convert USD Size to Share Count
                        # size_usd is the amount to invest.
                        # shares = size_usd / price
                        if signal.entry_price > 0:
                            quantity = signal.size_usd / signal.entry_price
                        else:
                            quantity = signal.size_usd # Fallback if price 0, though unsafe

                        result = await self.polymarket.place_order(
                            token_id=token_id,
                            side="BUY",
                            price=signal.entry_price,
                            size=quantity
                        )
                        
                        if result:
                            position = SimulatedPosition(
                                position_id=result.get("order_id", signal.signal_id),
                                signal=signal,
                                entry_time=datetime.now(),
                                token_id=token_id,
                                quantity=quantity
                            )
                            self.positions[position.position_id] = position
                            self.stats.total_trades += 1
                            
                            logger.info(f"[LIVE] Trade executed on Polymarket: {position.position_id} (Qty: {quantity:.2f})")
                            return
            except Exception as e:
                logger.error(f"Polymarket trade error: {e}")
        
        logger.error("Failed to execute live trade")

    async def _execute_live_close(self, position: SimulatedPosition, price: float) -> bool:
        if not self.polymarket:
            return False

        try:
            # Prefer using stored token_id, fallback to re-fetching if missing (backward compat)
            token_id = position.token_id

            if not token_id:
                markets = await self.polymarket.get_markets_by_event(f"{position.signal.team} to win")
                if markets:
                    market = markets[0]
                    token_id = market.get("clobTokenIds", [None])[0]

            if not token_id:
                logger.error(f"Could not find token_id for position {position.position_id}")
                return False

            # Determine quantity to close
            if position.quantity:
                qty_to_close = position.quantity
            else:
                # Fallback for positions opened before this fix or in simulation
                if position.signal.entry_price > 0:
                    qty_to_close = position.signal.size_usd / position.signal.entry_price
                else:
                    qty_to_close = position.signal.size_usd

            # Sherlock Fix: Fetch execution price from Orderbook (Bid) instead of using passed price (Ask/Last).
            # We want to sell INTO the Bid (taker) to ensure immediate exit, especially for Stop Loss.
            execution_price = price  # Default fallback

            try:
                # Only try to fetch orderbook if the client supports it
                if hasattr(self.polymarket, 'get_orderbook'):
                    orderbook = await self.polymarket.get_orderbook(token_id)

                    # Sherlock Fix: Validate Bid Price > 0 to prevent selling for free
                    if orderbook and orderbook.get("best_bid"):
                        bid_price = float(orderbook["best_bid"])
                        if bid_price > 0:
                            execution_price = bid_price
                            logger.info(f"Using Best Bid {execution_price} for closing trade (Trigger Price: {price})")
                        else:
                            logger.warning(f"Best Bid is {bid_price}, ignoring. Using trigger price {price}.")
            except Exception as e:
                logger.warning(f"Failed to fetch orderbook for execution price, falling back to trigger price: {e}")

            # Execute SELL order
            result = await self.polymarket.place_order(
                token_id=token_id,
                side="SELL",
                price=execution_price,
                size=qty_to_close
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error closing position {position.position_id}: {e}")
            return False

    async def monitor_positions(self):
        while True:
            try:
                for position_id, position in list(self.positions.items()):
                    current_price = await self._get_current_market_price(
                        position.signal.fixture_id,
                        position.signal.team
                    )
                    
                    if current_price is None:
                        if self.mode == TradingMode.SIMULATION:
                            current_price = self._simulate_price_movement(position)
                        else:
                            continue
                    
                    if current_price >= position.signal.target_price:
                        await self._close_position(position, current_price, "TAKE_PROFIT")
                    
                    elif current_price <= position.signal.stop_loss_price:
                        await self._close_position(position, current_price, "STOP_LOSS")
                
                await asyncio.sleep(5) 
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(5)

    def _simulate_price_movement(self, position: SimulatedPosition) -> float:
        """
        Simulate a random walk price movement for the position.
        Uses module-level simulation constants.
        """
        now = datetime.now()
        
        # Initialize if not set (for backward compatibility or recovery)
        if position.last_price is None:
            position.last_price = position.signal.entry_price
        if position.last_update_time is None:
            position.last_update_time = position.entry_time

        # Calculate time step
        elapsed_step = (now - position.last_update_time).total_seconds()
        if elapsed_step <= 0:
            return position.last_price

        # Volatility decreases slightly over time but remains relative to price
        # Using a simpler model: Annualized Volatility scaled to time step
        # Assuming ~50% daily volatility for these markets
        dt = elapsed_step / SIM_SECONDS_IN_DAY # Fraction of day
        
        # Drift towards 0.5 slightly if extreme, else random walk
        current_p = position.last_price
        drift = 0.0
        
        # Mean reversion for extreme prices
        if current_p > SIM_DRIFT_THRESHOLD_HIGH:
            drift = -SIM_DRIFT_FACTOR * dt
        elif current_p < SIM_DRIFT_THRESHOLD_LOW:
            drift = SIM_DRIFT_FACTOR * dt

        # Random walk step: P_t = P_{t-1} + P_{t-1} * shock
        # shock ~ N(drift * dt, vol * sqrt(dt))
        shock = random.gauss(drift, SIM_ANNUAL_VOLATILITY * (dt ** 0.5))

        new_price = current_p * (1 + shock)
        new_price = max(SIM_PRICE_FLOOR, min(SIM_PRICE_CEILING, new_price))

        # Update state
        position.last_price = new_price
        position.last_update_time = now

        return new_price

    async def _close_position(self, position: SimulatedPosition, exit_price: float, reason: str):
        # Sherlock Fix: Execute SELL on exchange if in LIVE mode
        if self.mode == TradingMode.LIVE:
            success = await self._execute_live_close(position, exit_price)
            if not success:
                logger.error(f"CRITICAL: Failed to close position {position.position_id} on exchange!")
                # We DO NOT proceed to update stats or remove position,
                # so the monitor loop tries again next time.
                return

        position.exit_time = datetime.now()
        position.exit_price = exit_price
        position.status = f"closed_{reason.lower()}"
        
        entry = position.signal.entry_price
        size = position.signal.size_usd
        
        pnl_pct = (exit_price - entry) / entry
        position.pnl = pnl_pct * size
        
        self.daily_pnl += position.pnl
        self.stats.total_pnl += position.pnl
        
        if position.pnl > 0:
            self.stats.winning_trades += 1
        else:
            self.stats.losing_trades += 1
        
        total = self.stats.winning_trades + self.stats.losing_trades
        self.stats.win_rate = self.stats.winning_trades / total if total > 0 else 0
        
        del self.positions[position.position_id]
        self.closed_positions.append(position)
        
        self._log_event("position_closed", {
            "position_id": position.position_id,
            "exit_price": exit_price,
            "pnl": position.pnl,
            "reason": reason
        })
        
        logger.info(f"Position closed: {position.position_id}")
        logger.info(f"  Exit price: {exit_price:.4f}")
        logger.info(f"  P&L: ${position.pnl:.2f}")
        logger.info(f"  Reason: {reason}")

    def _log_event(self, event_type: str, data: Dict):
        self.event_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })

    def get_stats(self) -> AlphaOneStats:
        return self.stats

    def export_event_log(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.event_log, f, indent=2, default=str)
        logger.info(f"Event log exported to {filepath}")
