/**
 * API utilities for real-time soccer data
 * Handles HTTP requests to backend
 */

import { LiveMatch, MarketPrice, HealthResponse, BotStatus, Settings, LiveMatchesResponse, FixtureMarketsResponse, AllMarketsResponse } from '../types';

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

/**
 * Fetch all live soccer matches
 */
export async function fetchLiveMatches(): Promise<LiveMatch[]> {
  try {
    const response = await fetch(`${API_BASE}/api/matches/live`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const matchesResponse = (await response.json()) as LiveMatchesResponse;
    return matchesResponse.matches || [];
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

    const fixtureMarketsResponse = (await response.json()) as FixtureMarketsResponse;
    return fixtureMarketsResponse.markets || [];
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

    const allMarketsResponse = (await response.json()) as AllMarketsResponse;
    return allMarketsResponse.markets || [];
  } catch (error) {
    console.error('Failed to fetch markets:', error);
    return [];
  }
}

/**
 * Check system health
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    return (await response.json()) as HealthResponse;
  } catch (error) {
    console.error('Health check failed:', error);
    return { status: 'error', error: String(error) };
  }
}

/**
 * Fetch bot status
 */
export async function fetchBotStatus(): Promise<BotStatus | null> {
  try {
    const response = await fetch(`${API_BASE}/api/status`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const botStatus = (await response.json()) as BotStatus;
    // Assuming api/status returns { data: BotStatus } or just BotStatus?
    // In App.tsx: setBotStatus(botStatus.data) in websocket message, but setBotStatus(botStatus) in fetchStatus.
    // Let's assume it returns the status object directly based on fetchStatus usage.
    return botStatus;
  } catch (error) {
    console.error('Error fetching status:', error);
    return null;
  }
}

/**
 * Start the bot
 */
export async function startBot(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/bot/start`, { method: 'POST' });
    return response.ok;
  } catch (error) {
    console.error('Error starting bot:', error);
    return false;
  }
}

/**
 * Stop the bot
 */
export async function stopBot(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/bot/stop`, { method: 'POST' });
    return response.ok;
  } catch (error) {
    console.error('Error stopping bot:', error);
    return false;
  }
}

/**
 * Load settings
 */
export async function loadSettings(): Promise<Settings> {
  try {
    const response = await fetch(`${API_BASE}/api/settings/load`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as Settings;
  } catch (error) {
    console.error('Error loading settings:', error);
    return {};
  }
}

/**
 * Save settings
 */
export async function saveSettings(settings: Settings): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/settings/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_football_key: settings.api_football_key,
        kalshi_api_key: settings.kalshi_api_key,
        kalshi_api_secret: settings.kalshi_api_secret,
        polymarket_api_key: settings.polymarket_api_key,
        max_trade_size: settings.max_trade_size,
        max_daily_loss: settings.max_daily_loss,
        underdog_threshold: settings.underdog_threshold,
        max_positions: settings.max_positions
      })
    });
    return response.ok;
  } catch (error) {
    console.error('Error saving settings:', error);
    return false;
  }
}
