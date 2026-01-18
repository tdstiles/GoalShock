export interface MarketPrice {
  market_id: string;
  fixture_id: number;
  question: string;
  title?: string; // For backward compatibility if needed
  yes_price: number;
  no_price: number;
  source: string;
  last_updated: string;
  volume_24h?: number;
  volume?: number; // For backward compatibility if needed
  home_team: string;
  away_team: string;
}

export interface LiveMatch {
  fixture_id: number;
  league_id: number;
  league_name: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  minute: number;
  status: string;
  markets?: MarketPrice[];
}

export interface GoalEvent {
  id: string;
  fixture_id: number;
  league_id: number;
  league_name: string;
  home_team: string;
  away_team: string;
  team: string;
  player: string;
  assist?: string;
  minute: number;
  goal_type: string;
  home_score: number;
  away_score: number;
  timestamp: string;
  market_ids?: string[];
}

export interface GoalAlert {
  type: 'goal';
  goal: GoalEvent;
  markets: MarketPrice[];
}

export interface MarketUpdate {
  type: 'market_update';
  market_id: string;
  yes_price: number;
  no_price: number;
  timestamp: string;
}

export interface Trade {
  id: string;
  timestamp: string;
  team: string;
  player: string;
  market: string;
  side: string;
  price: number;
  size: number;
  pnl?: number;
  status: string;
}

export interface BotStatus {
  running: boolean;
  uptime: number;
  total_trades: number;
  win_rate: number;
  total_pnl: number;
}

export interface HealthResponse {
  status: string;
  error?: string;
  api_football_configured?: boolean;
  market_apis_configured?: boolean;
  active_matches?: number;
  cached_markets?: number;
  connected_clients?: number;
}

export interface Settings {
  api_football_key?: string;
  kalshi_api_key?: string;
  kalshi_api_secret?: string;
  polymarket_api_key?: string;
  max_trade_size?: string | number;
  max_daily_loss?: string | number;
  underdog_threshold?: string | number;
  max_positions?: string | number;
  api_configured?: boolean;
  market_access?: boolean;
}
