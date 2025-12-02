/**
 * API utilities for real-time soccer data
 * Handles HTTP requests to backend
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

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

export interface MarketPrice {
  market_id: string;
  fixture_id: number;
  question: string;
  yes_price: number;
  no_price: number;
  source: string;
  last_updated: string;
  volume_24h?: number;
  home_team: string;
  away_team: string;
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

/**
 * Fetch all live soccer matches
 */
export async function fetchLiveMatches(): Promise<LiveMatch[]> {
  try {
    const response = await fetch(`${API_BASE}/api/matches/live`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    return data.matches || [];
  } catch (error) {
    console.error('Failed to fetch live matches:', error);
    return [];
  }
}

/**
 * Fetch markets for a specific fixture
 */
export async function fetchMarketsForFixture(fixtureId: number): Promise<MarketPrice[]> {
  try {
    const response = await fetch(`${API_BASE}/api/markets/${fixtureId}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    return data.markets || [];
  } catch (error) {
    console.error(`Failed to fetch markets for fixture ${fixtureId}:`, error);
    return [];
  }
}

/**
 * Fetch all available markets
 */
export async function fetchAllMarkets(): Promise<MarketPrice[]> {
  try {
    const response = await fetch(`${API_BASE}/api/markets/all`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    return data.markets || [];
  } catch (error) {
    console.error('Failed to fetch markets:', error);
    return [];
  }
}

/**
 * Check system health
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    return await response.json();
  } catch (error) {
    console.error('Health check failed:', error);
    return { status: 'error', error: String(error) };
  }
}
