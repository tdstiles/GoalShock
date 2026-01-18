/**
 * Real-time trading engine hook
 * Manages WebSocket connection and live data updates
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import type { LiveMatch, GoalEvent, MarketPrice, GoalAlert, MarketUpdate } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/live';
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 30000;

export interface TradingEngineState {
  connected: boolean;
  liveMatches: LiveMatch[];
  recentGoals: GoalEvent[];
  markets: Map<string, MarketPrice>;
  lastUpdate: Date | null;
}

export function useTradingEngine() {
  const [state, setState] = useState<TradingEngineState>({
    connected: false,
    liveMatches: [],
    recentGoals: [],
    markets: new Map(),
    lastUpdate: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pingTimerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Handle incoming WebSocket messages
   * CRITICAL: This processes all real-time updates
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      // Goal detected - UPDATE FRONTEND IMMEDIATELY
      if (data.type === 'goal') {
        const alert = data as GoalAlert;
        console.log('⚽ GOAL:', alert.goal.player, alert.goal.team);

        setState(prev => ({
          ...prev,
          recentGoals: [alert.goal, ...prev.recentGoals].slice(0, 20),
          lastUpdate: new Date(),
        }));

        // Update markets for this goal
        if (alert.markets && alert.markets.length > 0) {
          setState(prev => {
            const newMarkets = new Map(prev.markets);
            alert.markets.forEach(market => {
              newMarkets.set(market.market_id, market);
            });
            return { ...prev, markets: newMarkets };
          });
        }

        // Show browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('⚽ Goal!', {
            body: `${alert.goal.player} (${alert.goal.team}) - ${alert.goal.minute}'`,
            icon: '/soccer-ball.png',
          });
        }
      }

      // Market price update
      else if (data.type === 'market_update') {
        const update = data as MarketUpdate;

        setState(prev => {
          const market = prev.markets.get(update.market_id);
          if (!market) return prev;

          const updatedMarket: MarketPrice = {
            ...market,
            yes_price: update.yes_price,
            no_price: update.no_price,
            last_updated: update.timestamp,
          };

          const newMarkets = new Map(prev.markets);
          newMarkets.set(update.market_id, updatedMarket);

          return {
            ...prev,
            markets: newMarkets,
            lastUpdate: new Date(),
          };
        });
      }

      // Live matches update
      else if (data.type === 'matches') {
        setState(prev => ({
          ...prev,
          liveMatches: data.matches,
          lastUpdate: new Date(),
        }));
      }

      // Connection confirmed
      else if (data.type === 'connected') {
        console.log('✅ Connected to real-time feed');
        setState(prev => ({ ...prev, connected: true }));
      }

    } catch (error) {
      console.error('Failed to process WebSocket message:', error);
    }
  }, []);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      console.log('🔌 Connecting to WebSocket...', WS_URL);
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setState(prev => ({ ...prev, connected: true }));

        // Start ping/pong
        if (pingTimerRef.current) clearInterval(pingTimerRef.current);
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setState(prev => ({ ...prev, connected: false }));
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket closed');
        setState(prev => ({ ...prev, connected: false }));

        // Clear ping timer
        if (pingTimerRef.current) {
          clearInterval(pingTimerRef.current);
          pingTimerRef.current = null;
        }

        // Attempt reconnect
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          console.log('🔄 Reconnecting...');
          connect();
        }, RECONNECT_DELAY);
      };

      wsRef.current = ws;

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setState(prev => ({ ...prev, connected: false }));
    }
  }, [handleMessage]);

  /**
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }

    setState(prev => ({ ...prev, connected: false }));
  }, []);

  /**
   * Get market for a specific ID
   */
  const getMarket = useCallback((marketId: string): MarketPrice | undefined => {
    return state.markets.get(marketId);
  }, [state.markets]);

  /**
   * Get markets for a specific fixture
   */
  const getMarketsForFixture = useCallback((fixtureId: number): MarketPrice[] => {
    return Array.from(state.markets.values())
      .filter(market => market.fixture_id === fixtureId);
  }, [state.markets]);

  // Auto-connect on mount
  useEffect(() => {
    connect();

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    getMarket,
    getMarketsForFixture,
  };
}
