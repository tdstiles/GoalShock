/**
 * Live Matches Feed Component
 * Displays real-time soccer matches with market prices
 * Updates immediately when goals occur
 */
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTradingEngine } from '../hooks/useTradingEngine';
import { fetchLiveMatches } from '../utils/api';
import type { LiveMatch, MarketPrice } from '../utils/api';

export default function LiveMatchesFeed() {
  const { connected, liveMatches, recentGoals, markets, getMarketsForFixture } = useTradingEngine();

  // Fetch initial matches on mount
  useEffect(() => {
    fetchLiveMatches();
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      {/* Connection Status */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '20px'
      }}>
        <div style={{
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          background: connected ? '#10b981' : '#ef4444',
          boxShadow: connected ? '0 0 10px rgba(16, 185, 129, 0.5)' : 'none',
          animation: connected ? 'pulse 2s infinite' : 'none'
        }} />
        <span style={{ color: connected ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
          {connected ? 'Live Feed Connected' : 'Connecting...'}
        </span>
      </div>

      {/* Recent Goals */}
      {recentGoals.length > 0 && (
        <div style={{ marginBottom: '30px' }}>
          <h2 style={{ color: '#10b981', marginBottom: '15px' }}>
            ⚽ Recent Goals
          </h2>
          <AnimatePresence>
            {recentGoals.slice(0, 5).map((goal, i) => (
              <motion.div
                key={goal.id}
                initial={{ opacity: 0, x: -50, scale: 0.9 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 50 }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                style={{
                  padding: '15px',
                  background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(20, 184, 166, 0.1))',
                  borderLeft: '4px solid #10b981',
                  borderRadius: '8px',
                  marginBottom: '10px',
                  boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#fff', marginBottom: '5px' }}>
                      {goal.player} ⚽
                    </p>
                    <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                      {goal.home_team} {goal.home_score} - {goal.away_score} {goal.away_team}
                    </p>
                    <p style={{ color: '#10b981', fontSize: '0.85rem', marginTop: '5px' }}>
                      {goal.league_name} • {goal.minute}'
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ color: '#14b8a6', fontSize: '0.8rem' }}>
                      {new Date(goal.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Live Matches */}
      <h2 style={{ color: '#14b8a6', marginBottom: '15px' }}>
        📺 Live Matches
      </h2>

      {liveMatches.length === 0 ? (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          background: 'rgba(20, 25, 50, 0.6)',
          borderRadius: '12px',
          border: '1px solid rgba(20, 184, 166, 0.3)'
        }}>
          <p style={{ color: '#94a3b8', fontSize: '1.1rem' }}>
            {connected ? 'No live matches right now' : 'Connecting to live feed...'}
          </p>
          <p style={{ color: '#64748b', fontSize: '0.9rem', marginTop: '10px' }}>
            {connected && 'Check back during match hours'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '20px' }}>
          {liveMatches.map((match) => (
            <LiveMatchCard
              key={match.fixture_id}
              match={match}
              markets={getMarketsForFixture(match.fixture_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Individual Match Card with Markets
 */
function LiveMatchCard({ match, markets }: { match: LiveMatch; markets: MarketPrice[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
      style={{
        padding: '20px',
        background: 'rgba(20, 25, 50, 0.8)',
        borderRadius: '12px',
        border: '1px solid rgba(20, 184, 166, 0.3)'
      }}
    >
      {/* Match Header */}
      <div style={{ marginBottom: '15px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
          <span style={{ color: '#84cc16', fontSize: '0.85rem', fontWeight: 'bold' }}>
            ● LIVE
          </span>
          <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            {match.league_name}
          </span>
        </div>
      </div>

      {/* Teams and Score */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <p style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#fff' }}>
            {match.home_team}
          </p>
          <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>
            {match.home_score}
          </p>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#fff' }}>
            {match.away_team}
          </p>
          <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>
            {match.away_score}
          </p>
        </div>
      </div>

      {/* Match Time */}
      <div style={{
        padding: '8px 15px',
        background: 'rgba(132, 204, 22, 0.2)',
        borderRadius: '6px',
        marginBottom: '20px',
        textAlign: 'center'
      }}>
        <span style={{ color: '#84cc16', fontWeight: 'bold' }}>
          {match.minute}' - {match.status}
        </span>
      </div>

      {/* Markets */}
      {markets.length > 0 && (
        <div>
          <h3 style={{ color: '#14b8a6', fontSize: '0.95rem', marginBottom: '10px' }}>
            Prediction Markets
          </h3>
          <div style={{ display: 'grid', gap: '10px' }}>
            {markets.slice(0, 3).map((market) => (
              <MarketPriceCard key={market.market_id} market={market} />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

/**
 * Market Price Card
 */
function MarketPriceCard({ market }: { market: MarketPrice }) {
  const isStale = (new Date().getTime() - new Date(market.last_updated).getTime()) > 60000;

  return (
    <div style={{
      padding: '12px',
      background: isStale ? 'rgba(239, 68, 68, 0.1)' : 'rgba(20, 184, 166, 0.1)',
      borderLeft: `3px solid ${isStale ? '#ef4444' : '#14b8a6'}`,
      borderRadius: '6px'
    }}>
      <p style={{ fontSize: '0.9rem', color: '#fff', marginBottom: '8px' }}>
        {market.question}
      </p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ color: '#10b981', fontSize: '0.75rem', marginRight: '5px' }}>YES</span>
          <span style={{ color: '#fff', fontWeight: 'bold' }}>
            ${market.yes_price.toFixed(2)}
          </span>
        </div>
        <div>
          <span style={{ color: '#ef4444', fontSize: '0.75rem', marginRight: '5px' }}>NO</span>
          <span style={{ color: '#fff', fontWeight: 'bold' }}>
            ${market.no_price.toFixed(2)}
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
          {market.source}
        </div>
      </div>
      {isStale && (
        <p style={{ color: '#ef4444', fontSize: '0.7rem', marginTop: '5px' }}>
          ⚠ Price may be stale
        </p>
      )}
    </div>
  );
}
