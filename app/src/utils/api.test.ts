
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as api from './api';

// Helper to mock fetch responses
function mockFetch<T>(status: number, responseData: T) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => responseData,
  });
}

function mockFetchError(errorMsg: string) {
    global.fetch = vi.fn().mockRejectedValue(new Error(errorMsg));
}

describe('API Utils', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
      vi.clearAllMocks();
  });

  describe('fetchLiveMatches', () => {
    it('should return matches on successful response', async () => {
      const mockMatches = [{ fixture_id: 1, home_team: 'A', away_team: 'B' }];
      mockFetch(200, { matches: mockMatches });

      const result = await api.fetchLiveMatches();
      expect(result).toEqual(mockMatches);
      expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/matches/live`);
    });

    it('should return empty array on 404', async () => {
      mockFetch(404, { error: 'Not Found' });

      const result = await api.fetchLiveMatches();
      expect(result).toEqual([]);
    });

    it('should return empty array on network error', async () => {
        mockFetchError("Network Error");

        const result = await api.fetchLiveMatches();
        expect(result).toEqual([]);
    });
  });

  describe('fetchMarketsForFixture', () => {
    it('should return markets on success', async () => {
        const mockMarkets = [{ market_id: 'm1', question: 'Win?' }];
        mockFetch(200, { markets: mockMarkets });

        const result = await api.fetchMarketsForFixture(123);
        expect(result).toEqual(mockMarkets);
        expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/markets/123`);
    });

    it('should return empty array on failure', async () => {
        mockFetch(500, {});
        const result = await api.fetchMarketsForFixture(123);
        expect(result).toEqual([]);
    });
  });

  describe('fetchAllMarkets', () => {
    it('should return all markets on success', async () => {
      const mockMarkets = [{ market_id: 'm1', question: 'Win?' }];
      mockFetch(200, { markets: mockMarkets });

      const result = await api.fetchAllMarkets();
      expect(result).toEqual(mockMarkets);
      expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/markets/all`);
    });

    it('should return empty array on failure', async () => {
      mockFetch(500, {});
      const result = await api.fetchAllMarkets();
      expect(result).toEqual([]);
    });
  });

  describe('checkHealth', () => {
      it('should return health status on success', async () => {
          const mockHealth = { status: 'ok', version: '1.0' };
          mockFetch(200, mockHealth);

          const result = await api.checkHealth();
          expect(result).toEqual(mockHealth);
      });

      it('should return error object on failure', async () => {
          mockFetch(503, { status: 'error' });
          const result = await api.checkHealth();
          expect(result).toEqual({ status: 'error', error: 'Error: HTTP 503' });
      });
  });

  describe('Bot Status', () => {
    it('fetchBotStatus should return status on success', async () => {
      const mockStatus = { active: true, uptime: 120 };
      mockFetch(200, mockStatus);
      const result = await api.fetchBotStatus();
      expect(result).toEqual(mockStatus);
      expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/status`);
    });

    it('fetchBotStatus should return null on failure', async () => {
      mockFetch(500, {});
      const result = await api.fetchBotStatus();
      expect(result).toBeNull();
    });
  });

  describe('Bot Control', () => {
      it('startBot should return true on success', async () => {
          mockFetch(200, {});
          const result = await api.startBot();
          expect(result).toBe(true);
          expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/bot/start`, expect.objectContaining({ method: 'POST' }));
      });

      it('startBot should return false on failure', async () => {
          mockFetch(500, {});
          const result = await api.startBot();
          expect(result).toBe(false);
      });

      it('stopBot should return true on success', async () => {
        mockFetch(200, {});
        const result = await api.stopBot();
        expect(result).toBe(true);
        expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/bot/stop`, expect.objectContaining({ method: 'POST' }));
      });

      it('stopBot should return false on failure', async () => {
          mockFetch(500, {});
          const result = await api.stopBot();
          expect(result).toBe(false);
      });
  });

  describe('Settings', () => {
      it('loadSettings should return settings on success', async () => {
          const mockSettings = { api_football_key: 'abc' };
          mockFetch(200, mockSettings);
          const result = await api.loadSettings();
          expect(result).toEqual(mockSettings);
          expect(fetch).toHaveBeenCalledWith(`${api.API_BASE}/api/settings/load`);
      });

      it('loadSettings should return empty object on failure', async () => {
          mockFetch(500, {});
          const result = await api.loadSettings();
          expect(result).toEqual({});
      });

      it('saveSettings should return true on success', async () => {
          mockFetch(200, {});
          const settings = { api_football_key: 'abc' };
          const result = await api.saveSettings(settings);
          expect(result).toBe(true);
          expect(fetch).toHaveBeenCalledWith(
              `${api.API_BASE}/api/settings/save`,
              expect.objectContaining({
                  method: 'POST',
                  body: expect.stringContaining('"api_football_key":"abc"')
              })
          );
      });

      it('saveSettings should return false on failure', async () => {
          mockFetch(500, {});
          const settings = { api_football_key: 'abc' };
          const result = await api.saveSettings(settings);
          expect(result).toBe(false);
      });
  });
});
