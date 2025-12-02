import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CustomCursor from './components/CustomCursor';
import SubtleRippleBackground from './components/SubtleRippleBackground';
import ButtonText from './components/ButtonText';

const API_BASE = 'http://localhost:8000';

// Types
interface Trade {
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

interface BotStatus {
  running: boolean;
  uptime: number;
  total_trades: number;
  win_rate: number;
  total_pnl: number;
}

// Loading splash screen
function SplashScreen({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 1000);
          return 100;
        }
        return prev + 2;
      });
    }, 20);

    return () => clearInterval(interval);
  }, [onComplete]);

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1.0 }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: '#0a0e27',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000
      }}
    >
      <SubtleRippleBackground />
      <h1 style={{
        fontSize: '4rem',
        background: 'linear-gradient(135deg, #10b981, #14b8a6)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        marginBottom: '40px'
      }}>
        GOALSHOCK
      </h1>
      <div style={{
        width: '400px',
        height: '6px',
        background: 'rgba(255, 255, 255, 0.1)',
        borderRadius: '3px',
        overflow: 'hidden'
      }}>
        <motion.div
          style={{
            height: '100%',
            background: 'linear-gradient(90deg, #10b981, #14b8a6)',
            borderRadius: '3px'
          }}
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.1 }}
        />
      </div>
      <p style={{ marginTop: '20px', color: '#10b981', fontSize: '1.2rem' }}>
        {progress}%
      </p>
    </motion.div>
  );
}

// Main App
export default function App() {
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'landing' | 'dashboard' | 'markets' | 'settings'>('landing');

  return (
    <>
      <CustomCursor />

      <AnimatePresence>
        {loading && <SplashScreen onComplete={() => setLoading(false)} />}
      </AnimatePresence>

      {!loading && (
        <>
          <div className="grid-background" />
          <SubtleRippleBackground />

          {view === 'landing' && <LandingView onEnter={() => setView('dashboard')} />}
          {view === 'dashboard' && (
            <DashboardView
              onMarkets={() => setView('markets')}
              onSettings={() => setView('settings')}
              onBack={() => setView('landing')}
            />
          )}
          {view === 'markets' && <MarketsView onBack={() => setView('dashboard')} />}
          {view === 'settings' && <SettingsView onBack={() => setView('dashboard')} />}
        </>
      )}
    </>
  );
}

// Landing Page
function LandingView({ onEnter }: { onEnter: () => void }) {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      position: 'relative'
    }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        style={{ textAlign: 'center' }}
      >
        <h1 style={{
          fontSize: '5rem',
          background: 'linear-gradient(135deg, #10b981, #14b8a6, #84cc16)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '30px',
          fontWeight: 'bold'
        }}>
          GOALSHOCK
        </h1>

        <p style={{
          fontSize: '1.5rem',
          color: '#94a3b8',
          marginBottom: '50px',
          maxWidth: '600px'
        }}>
          Real-time soccer goal detection meets automated prediction market trading
        </p>

        <button
          className="btn-neon"
          onClick={onEnter}
        >
          <ButtonText>Launch Dashboard</ButtonText>
        </button>

        <div style={{
          marginTop: '80px',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '30px',
          maxWidth: '900px'
        }}>
          {[
            { title: 'Live Detection', desc: 'Sub-second goal alerts', color: '#10b981' },
            { title: 'Auto Trading', desc: 'Kalshi + Polymarket', color: '#14b8a6' },
            { title: 'Underdog Edge', desc: 'Exploit market lag', color: '#84cc16' }
          ].map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 * (i + 1) }}
              className="card"
              style={{ textAlign: 'center' }}
            >
              <h3 style={{ color: feature.color, marginBottom: '10px' }}>
                {feature.title}
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                {feature.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

// Live Markets Component
function LiveMarketsSection() {
  const [markets, setMarkets] = useState<any[]>([]);
  const [liveMatches, setLiveMatches] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [marketsRes, matchesRes] = await Promise.all([
          fetch(`${API_BASE}/api/markets`),
          fetch(`${API_BASE}/api/markets/live`)
        ]);
        const marketsData = await marketsRes.json();
        const matchesData = await matchesRes.json();

        setMarkets(marketsData.markets || []);
        setLiveMatches(matchesData.matches || []);
        setConnected(true);
      } catch (error) {
        console.error('Error fetching data:', error);
        setConnected(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Connection Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <div style={{
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          background: connected ? '#10b981' : '#ef4444',
          boxShadow: connected ? '0 0 10px rgba(16, 185, 129, 0.5)' : 'none',
          animation: connected ? 'pulse 2s infinite' : 'none'
        }} />
        <span style={{ color: connected ? '#10b981' : '#ef4444', fontWeight: 'bold', fontSize: '0.9rem' }}>
          {connected ? '● Data Feed Online' : '○ Connecting...'}
        </span>
      </div>

      {/* Prediction Markets */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#10b981', marginBottom: '15px' }}>🎯 Prediction Markets</h2>
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          {markets.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '40px' }}>
              Loading markets...
            </p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              {markets.map((market, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  style={{
                    padding: '20px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    borderLeft: '4px solid #10b981',
                    borderRadius: '12px',
                    border: '1px solid rgba(16, 185, 129, 0.2)'
                  }}
                >
                  <p style={{ fontWeight: 'bold', color: '#fff', marginBottom: '12px', fontSize: '1rem' }}>
                    {market.question || market.title}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '25px' }}>
                      <div>
                        <p style={{ color: '#10b981', fontSize: '0.75rem', marginBottom: '5px', fontWeight: 'bold' }}>YES</p>
                        <p style={{ fontWeight: 'bold', fontSize: '1.3rem', color: '#10b981' }}>${market.yes_price?.toFixed(2)}</p>
                      </div>
                      <div>
                        <p style={{ color: '#ef4444', fontSize: '0.75rem', marginBottom: '5px', fontWeight: 'bold' }}>NO</p>
                        <p style={{ fontWeight: 'bold', fontSize: '1.3rem', color: '#ef4444' }}>${market.no_price?.toFixed(2)}</p>
                      </div>
                    </div>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                      Vol: ${market.volume?.toLocaleString()}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Live Matches */}
      <div className="card">
        <h2 style={{ color: '#14b8a6', marginBottom: '15px' }}>⚽ Live Soccer Matches</h2>
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {liveMatches.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ color: '#94a3b8', fontSize: '1rem', marginBottom: '8px' }}>
                No live matches currently
              </p>
              <p style={{ color: '#64748b', fontSize: '0.85rem' }}>
                Matches will appear here when games are live
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
              {liveMatches.map((match, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  style={{
                    padding: '20px',
                    background: 'rgba(20, 184, 166, 0.1)',
                    borderLeft: '4px solid #14b8a6',
                    borderRadius: '12px',
                    border: '1px solid rgba(20, 184, 166, 0.2)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <p style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.95rem' }}>{match.home_team}</p>
                    <p style={{ color: '#10b981', fontWeight: 'bold', fontSize: '1.2rem' }}>{match.home_score || 0}</p>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <p style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.95rem' }}>{match.away_team}</p>
                    <p style={{ color: '#10b981', fontWeight: 'bold', fontSize: '1.2rem' }}>{match.away_score || 0}</p>
                  </div>
                  <div style={{ padding: '8px', background: 'rgba(132, 204, 22, 0.2)', borderRadius: '6px', textAlign: 'center' }}>
                    <p style={{ color: '#84cc16', fontSize: '0.85rem', fontWeight: 'bold' }}>
                      ⏱ {match.minute}' - {match.league}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// Dashboard with Bot Controls
function DashboardView({ onMarkets, onSettings, onBack }: { onMarkets: () => void; onSettings: () => void; onBack: () => void }) {
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch bot status
  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      const data = await res.json();
      setBotStatus(data);
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  // Start bot
  const startBot = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/bot/start`, { method: 'POST' });
      if (response.ok) {
        // Immediately update local state for instant UI feedback
        setBotStatus(prev => prev ? { ...prev, running: true } : null);
        // Then fetch fresh status
        setTimeout(fetchStatus, 100);
      }
    } catch (error) {
      console.error('Error starting bot:', error);
      alert('Backend not running. Please start the backend server first.');
    }
  };

  // Stop bot
  const stopBot = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/bot/stop`, { method: 'POST' });
      if (response.ok) {
        // Immediately update local state for instant UI feedback
        setBotStatus(prev => prev ? { ...prev, running: false } : null);
        // Then fetch fresh status
        setTimeout(fetchStatus, 100);
      }
    } catch (error) {
      console.error('Error stopping bot:', error);
      alert('Backend not running. Please start the backend server first.');
    }
  };

  // WebSocket connection
  useEffect(() => {
    fetchStatus();
    const statusInterval = setInterval(fetchStatus, 5000);

    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws');
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      console.log('✅ WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'trade') {
        setTrades(prev => [data.trade, ...prev].slice(0, 50));
      } else if (data.type === 'status') {
        // Update status from WebSocket
        setBotStatus(data.data);
      } else if (data.type === 'goal') {
        console.log('Goal detected:', data.goal);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      setWsConnected(false);
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log('🔌 WebSocket disconnected');
    };

    return () => {
      clearInterval(statusInterval);
      ws.close();
    };
  }, []);

  return (
    <div style={{ minHeight: '100vh', padding: '20px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '30px'
      }}>
        <h1 style={{
          fontSize: '2.5rem',
          background: 'linear-gradient(135deg, #10b981, #14b8a6)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          GOALSHOCK
        </h1>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{
            padding: '8px 15px',
            background: wsConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            borderRadius: '20px',
            fontSize: '0.85rem',
            color: wsConnected ? '#10b981' : '#ef4444',
            fontWeight: 'bold'
          }}>
            {wsConnected ? '● Online' : '○ Offline'}
          </div>
          <button className="btn-secondary" onClick={onMarkets}>
            <ButtonText>Markets</ButtonText>
          </button>
          <button className="btn-accent" onClick={onSettings}>
            <ButtonText>Settings</ButtonText>
          </button>
          <button className="btn-accent" onClick={onBack}>
            <ButtonText>Exit</ButtonText>
          </button>
        </div>
      </div>

      {/* Bot Control Panel */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ color: '#10b981', marginBottom: '10px' }}>Trading Bot</h2>
            <div style={{ display: 'flex', gap: '30px' }}>
              <div>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Status</p>
                <p style={{
                  fontSize: '1.2rem',
                  fontWeight: 'bold',
                  color: botStatus?.running ? '#10b981' : '#94a3b8'
                }}>
                  {botStatus?.running ? 'Running' : 'Stopped'}
                </p>
              </div>
              <div>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Uptime</p>
                <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#14b8a6' }}>
                  {botStatus?.uptime ? Math.floor(botStatus.uptime / 60) : 0}m
                </p>
              </div>
              <div>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Total Trades</p>
                <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#84cc16' }}>
                  {botStatus?.total_trades || 0}
                </p>
              </div>
              <div>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Win Rate</p>
                <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#10b981' }}>
                  {botStatus?.win_rate?.toFixed(1) || 0}%
                </p>
              </div>
              <div>
                <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Total P&L</p>
                <p style={{
                  fontSize: '1.2rem',
                  fontWeight: 'bold',
                  color: (botStatus?.total_pnl || 0) >= 0 ? '#10b981' : '#ef4444'
                }}>
                  ${(botStatus?.total_pnl || 0).toFixed(2)}
                </p>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            {!botStatus?.running ? (
              <button className="btn-success" onClick={startBot}>
                <ButtonText>Start Bot</ButtonText>
              </button>
            ) : (
              <button className="btn-accent" onClick={stopBot}>
                <ButtonText>Stop Bot</ButtonText>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Live Trades */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#10b981', marginBottom: '15px' }}>Live Trades</h2>
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          {trades.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '40px' }}>
              No trades yet. {botStatus?.running ? 'Waiting for goal events...' : 'Start the bot to begin trading.'}
            </p>
          ) : (
            trades.map((trade, i) => (
              <motion.div
                key={trade.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                style={{
                  padding: '15px',
                  background: trade.pnl && trade.pnl > 0
                    ? 'rgba(16, 185, 129, 0.1)'
                    : trade.pnl && trade.pnl < 0
                    ? 'rgba(239, 68, 68, 0.1)'
                    : 'rgba(20, 184, 166, 0.1)',
                  borderLeft: `3px solid ${
                    trade.pnl && trade.pnl > 0
                      ? '#10b981'
                      : trade.pnl && trade.pnl < 0
                      ? '#ef4444'
                      : '#14b8a6'
                  }`,
                  marginBottom: '10px',
                  borderRadius: '4px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div>
                    <p style={{ fontWeight: 'bold', color: '#fff', fontSize: '1.1rem' }}>
                      {trade.player} <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>({trade.team})</span>
                    </p>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
                      {trade.market}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{
                      fontSize: '1.2rem',
                      fontWeight: 'bold',
                      color: trade.side === 'YES' ? '#10b981' : '#ef4444'
                    }}>
                      {trade.side} @ ${trade.price.toFixed(2)}
                    </p>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
                      Size: ${trade.size}
                    </p>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                    {new Date(trade.timestamp).toLocaleTimeString()}
                  </p>
                  {trade.pnl !== undefined && (
                    <p style={{
                      fontWeight: 'bold',
                      color: trade.pnl > 0 ? '#10b981' : '#ef4444'
                    }}>
                      P&L: {trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </p>
                  )}
                  <span style={{
                    padding: '4px 12px',
                    borderRadius: '12px',
                    fontSize: '0.75rem',
                    fontWeight: 'bold',
                    background: trade.status === 'filled'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : trade.status === 'pending'
                      ? 'rgba(132, 204, 22, 0.2)'
                      : 'rgba(239, 68, 68, 0.2)',
                    color: trade.status === 'filled'
                      ? '#10b981'
                      : trade.status === 'pending'
                      ? '#84cc16'
                      : '#ef4444'
                  }}>
                    {trade.status.toUpperCase()}
                  </span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Live Markets Section */}
      <LiveMarketsSection />
    </div>
  );
}

// Markets View
function MarketsView({ onBack }: { onBack: () => void }) {
  const [markets, setMarkets] = useState<any[]>([]);
  const [liveMatches, setLiveMatches] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [marketsRes, matchesRes] = await Promise.all([
          fetch(`${API_BASE}/api/markets`),
          fetch(`${API_BASE}/api/markets/live`)
        ]);
        const marketsData = await marketsRes.json();
        const matchesData = await matchesRes.json();

        setMarkets(marketsData.markets || []);
        setLiveMatches(matchesData.matches || []);
      } catch (error) {
        console.error('Error fetching markets:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ minHeight: '100vh', padding: '20px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '30px'
      }}>
        <h1 style={{
          fontSize: '2.5rem',
          background: 'linear-gradient(135deg, #10b981, #14b8a6)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          Live Markets
        </h1>
        <button className="btn-accent" onClick={onBack}>
          <ButtonText>Back to Dashboard</ButtonText>
        </button>
      </div>

      {/* Prediction Markets - Full Width on Top */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#10b981', marginBottom: '15px' }}>Prediction Markets</h2>
        <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
          {markets.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '40px' }}>
              No markets available...
            </p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              {markets.map((market, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  style={{
                    padding: '15px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    borderLeft: '3px solid #10b981',
                    borderRadius: '8px'
                  }}
                >
                  <p style={{ fontWeight: 'bold', color: '#fff', marginBottom: '10px', fontSize: '0.95rem' }}>
                    {market.question || market.title}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '20px' }}>
                      <div>
                        <p style={{ color: '#10b981', fontSize: '0.75rem', marginBottom: '4px' }}>YES</p>
                        <p style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>${market.yes_price?.toFixed(2)}</p>
                      </div>
                      <div>
                        <p style={{ color: '#ef4444', fontSize: '0.75rem', marginBottom: '4px' }}>NO</p>
                        <p style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>${market.no_price?.toFixed(2)}</p>
                      </div>
                    </div>
                    <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                      Vol: ${market.volume?.toLocaleString()}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Live Matches - Below Markets */}
      <div className="card">
        <h2 style={{ color: '#14b8a6', marginBottom: '15px' }}>Live Matches</h2>
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {liveMatches.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ color: '#94a3b8', fontSize: '1rem', marginBottom: '8px' }}>
                No live matches right now
              </p>
              <p style={{ color: '#64748b', fontSize: '0.85rem' }}>
                API-Football connection issue - check API key or quota
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
              {liveMatches.map((match, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  style={{
                    padding: '15px',
                    background: 'rgba(20, 184, 166, 0.1)',
                    borderLeft: '3px solid #14b8a6',
                    borderRadius: '8px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <p style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.9rem' }}>{match.home_team}</p>
                    <p style={{ color: '#10b981', fontWeight: 'bold', fontSize: '1.1rem' }}>{match.home_score || 0}</p>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <p style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.9rem' }}>{match.away_team}</p>
                    <p style={{ color: '#10b981', fontWeight: 'bold', fontSize: '1.1rem' }}>{match.away_score || 0}</p>
                  </div>
                  <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                    {match.minute}' - {match.league}
                  </p>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Settings View (same as before but simplified)
function SettingsView({ onBack }: { onBack: () => void }) {
  const [settings, setSettings] = useState({
    apiFootballKey: '',
    kalshiApiKey: '',
    kalshiApiSecret: '',
    polymarketApiKey: '',
    maxTradeSize: '',
    maxDailyLoss: '',
    underdogThreshold: '',
    maxPositions: ''
  });

  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/settings/load`);
        const data = await response.json();
        setSettings({
          apiFootballKey: data.api_football_key || '',
          kalshiApiKey: data.kalshi_api_key || '',
          kalshiApiSecret: data.kalshi_api_secret || '',
          polymarketApiKey: data.polymarket_api_key || '',
          maxTradeSize: data.max_trade_size || '',
          maxDailyLoss: data.max_daily_loss || '',
          underdogThreshold: data.underdog_threshold || '',
          maxPositions: data.max_positions || ''
        });
      } catch (error) {
        console.error('Error loading settings:', error);
      }
    };
    loadSettings();
  }, []);

  const handleSave = async () => {
    try {
      await fetch(`${API_BASE}/api/settings/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_football_key: settings.apiFootballKey,
          kalshi_api_key: settings.kalshiApiKey,
          kalshi_api_secret: settings.kalshiApiSecret,
          polymarket_api_key: settings.polymarketApiKey,
          max_trade_size: settings.maxTradeSize,
          max_daily_loss: settings.maxDailyLoss,
          underdog_threshold: settings.underdogThreshold,
          max_positions: settings.maxPositions
        })
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  return (
    <div style={{ minHeight: '100vh', padding: '20px' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '30px'
        }}>
          <h1 style={{
            fontSize: '2.5rem',
            background: 'linear-gradient(135deg, #10b981, #14b8a6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Settings
          </h1>
          <button className="btn-accent" onClick={onBack}>
            <ButtonText>Back</ButtonText>
          </button>
        </div>

        <div className="card">
          <h2 style={{ color: '#10b981', marginBottom: '20px' }}>API Keys</h2>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
              API-Football Key
            </label>
            <input
              type="text"
              value={settings.apiFootballKey}
              onChange={(e) => setSettings({ ...settings, apiFootballKey: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                background: 'rgba(20, 25, 50, 0.8)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '1rem'
              }}
              placeholder="your-api-football-key"
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
              Polymarket API Key
            </label>
            <input
              type="text"
              value={settings.polymarketApiKey}
              onChange={(e) => setSettings({ ...settings, polymarketApiKey: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                background: 'rgba(20, 25, 50, 0.8)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '1rem'
              }}
              placeholder="your-polymarket-key"
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
              Kalshi API Key
            </label>
            <input
              type="text"
              value={settings.kalshiApiKey}
              onChange={(e) => setSettings({ ...settings, kalshiApiKey: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                background: 'rgba(20, 25, 50, 0.8)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '1rem'
              }}
              placeholder="your-kalshi-key"
            />
          </div>

          <div style={{ marginBottom: '30px' }}>
            <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
              Kalshi API Secret
            </label>
            <input
              type="password"
              value={settings.kalshiApiSecret}
              onChange={(e) => setSettings({ ...settings, kalshiApiSecret: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                background: 'rgba(20, 25, 50, 0.8)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '1rem'
              }}
              placeholder="your-kalshi-secret"
            />
          </div>

          <h2 style={{ color: '#14b8a6', marginBottom: '20px' }}>Trading Parameters</h2>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
                Max Trade Size (USD)
              </label>
              <input
                type="number"
                value={settings.maxTradeSize}
                onChange={(e) => setSettings({ ...settings, maxTradeSize: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'rgba(20, 25, 50, 0.8)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
                Max Daily Loss (USD)
              </label>
              <input
                type="number"
                value={settings.maxDailyLoss}
                onChange={(e) => setSettings({ ...settings, maxDailyLoss: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'rgba(20, 25, 50, 0.8)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
                Underdog Threshold
              </label>
              <input
                type="number"
                step="0.01"
                value={settings.underdogThreshold}
                onChange={(e) => setSettings({ ...settings, underdogThreshold: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'rgba(20, 25, 50, 0.8)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '8px' }}>
                Max Positions
              </label>
              <input
                type="number"
                value={settings.maxPositions}
                onChange={(e) => setSettings({ ...settings, maxPositions: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'rgba(20, 25, 50, 0.8)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '1rem'
                }}
              />
            </div>
          </div>

          <div style={{ marginTop: '30px', display: 'flex', gap: '15px' }}>
            <button className="btn-success" onClick={handleSave}>
              <ButtonText>Save Settings</ButtonText>
            </button>
            {saved && (
              <p style={{ color: '#10b981', alignSelf: 'center' }}>
                Settings saved successfully!
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
