
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


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
        
        self.underdog_threshold = float(os.getenv("UNDERDOG_THRESHOLD", "0.45"))
        self.max_trade_size = float(os.getenv("MAX_TRADE_SIZE_USD", "500"))
        self.max_positions = int(os.getenv("MAX_POSITIONS", "5"))
        self.take_profit_pct = float(os.getenv("TAKE_PROFIT_PERCENT", "15"))
        self.stop_loss_pct = float(os.getenv("STOP_LOSS_PERCENT", "10"))
        self.max_daily_loss = float(os.getenv("MAX_DAILY_LOSS_USD", "2000"))
        
        self.pre_match_odds: Dict[int, Dict[str, float]] = {}  
        self.positions: Dict[str, SimulatedPosition] = {}
        self.closed_positions: List[SimulatedPosition] = []
        self.daily_pnl = 0.0
        self.stats = AlphaOneStats()
        
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
        
       
        team_odds_map = {}
        for key, value in odds.items():
            if "home" in key.lower() or home_team.lower() in key.lower():
                team_odds_map[home_team] = value
            elif "away" in key.lower() or away_team.lower() in key.lower():
                team_odds_map[away_team] = value
            elif key.lower() not in ["draw", "tie"]:
                # Try exact match
                if home_team.lower() in key.lower():
                    team_odds_map[home_team] = value
                elif away_team.lower() in key.lower():
                    team_odds_map[away_team] = value
        
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
            current_price = underdog_odds * 1.2  
        
        
        confidence = self._calculate_confidence(underdog_odds, minute, underdog_score - favorite_score)
        adjusted_size = self.max_trade_size * confidence
        
     
        signal = TradeSignal(
            signal_id=f"alpha1_{fixture_id}_{int(datetime.now().timestamp())}",
            fixture_id=fixture_id,
            team=underdog_team,
            side="YES",
            entry_price=current_price,
            target_price=current_price * (1 + self.take_profit_pct / 100),
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

    def _calculate_confidence(self, pre_match_odds: float, minute: int, lead_margin: int) -> float:
        
  
        odds_factor = max(0.3, 1 - (pre_match_odds / self.underdog_threshold))
        
        if minute < 30:
            time_factor = 0.7 + (minute / 30) * 0.3
        elif minute < 70:
            time_factor = 1.0
        else:
            time_factor = max(0.5, 1 - (minute - 70) / 20 * 0.5)
        
        margin_factor = min(1.0, 0.7 + lead_margin * 0.15)
        
        confidence = odds_factor * time_factor * margin_factor
        
        return min(1.0, max(0.3, confidence))

    async def _get_current_market_price(self, fixture_id: int, team: str) -> Optional[float]:
        if self.mode == TradingMode.SIMULATION:
            return None
        
        if self.polymarket:
            try:
                markets = await self.polymarket.get_markets_by_event(f"{team} to win")
                if markets:
                    market = markets[0]
                    token_id = market.get("clobTokenIds", [None])[0]
                    if token_id:
                        return await self.polymarket.get_yes_price(token_id)
            except Exception as e:
                logger.error(f"Polymarket price fetch error: {e}")
        
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
        position = SimulatedPosition(
            position_id=signal.signal_id,
            signal=signal,
            entry_time=datetime.now()
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
                        result = await self.polymarket.place_order(
                            token_id=token_id,
                            side="BUY",
                            price=signal.entry_price,
                            size=signal.size_usd
                        )
                        
                        if result:
                            position = SimulatedPosition(
                                position_id=result.get("order_id", signal.signal_id),
                                signal=signal,
                                entry_time=datetime.now()
                            )
                            self.positions[position.position_id] = position
                            self.stats.total_trades += 1
                            
                            logger.info(f"[LIVE] Trade executed on Polymarket: {position.position_id}")
                            return
            except Exception as e:
                logger.error(f"Polymarket trade error: {e}")
        
        logger.error("Failed to execute live trade")

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
        import random
        
        entry_price = position.signal.entry_price
        elapsed = (datetime.now() - position.entry_time).total_seconds()
        
        volatility = 0.02 * max(0.5, 1 - elapsed / 3600)
        drift = 0.001  
        
        change = random.gauss(drift, volatility)
        new_price = entry_price * (1 + change * elapsed / 60)
        
        return max(0.01, min(0.99, new_price))

    async def _close_position(self, position: SimulatedPosition, exit_price: float, reason: str):
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
