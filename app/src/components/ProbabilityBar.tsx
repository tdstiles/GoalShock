import { motion } from 'framer-motion';
import { useState } from 'react';

interface ProbabilityBarProps {
  yesPrice: number;
  noPrice: number;
  height?: number;
}

export default function ProbabilityBar({ yesPrice, noPrice, height = 8 }: ProbabilityBarProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Normalize prices to ensure they fill the bar (in case of vig or data issues)
  const total = yesPrice + noPrice;
  const hasData = total > 0;

  // Default to 50/50 visual split if no data, but greyed out
  const yesPercent = hasData ? (yesPrice / total) * 100 : 0;
  const noPercent = hasData ? (noPrice / total) * 100 : 0;

  return (
    <div
      style={{ position: 'relative', marginTop: '12px' }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Main Bar */}
      <div
        role="progressbar"
        aria-label="Market Probability"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={yesPercent}
        style={{
          width: '100%',
          height: `${height}px`,
          background: 'rgba(255,255,255,0.1)',
          borderRadius: '4px',
          overflow: 'hidden',
          display: 'flex',
          cursor: 'pointer'
        }}
      >
        {!hasData ? (
          // No Data State
          <div style={{ width: '100%', height: '100%', background: '#334155' }} />
        ) : (
          <>
            {/* YES Segment */}
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${yesPercent}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              style={{
                height: '100%',
                background: '#10b981',
                borderRight: '1px solid rgba(0,0,0,0.2)'
              }}
            />
            {/* NO Segment */}
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${noPercent}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              style={{ height: '100%', background: '#ef4444' }}
            />
          </>
        )}
      </div>

      {/* Custom Tooltip */}
      {isHovered && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '8px',
            background: '#0f172a',
            border: '1px solid #334155',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            whiteSpace: 'nowrap',
            zIndex: 10,
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
            pointerEvents: 'none'
          }}
        >
          {!hasData ? (
            <span style={{ color: '#94a3b8' }}>No Data Available</span>
          ) : (
            <div style={{ display: 'flex', gap: '10px' }}>
              <span style={{ color: '#10b981', fontWeight: 'bold' }}>
                YES: {yesPercent.toFixed(1)}%
              </span>
              <span style={{ color: '#475569' }}>|</span>
              <span style={{ color: '#ef4444', fontWeight: 'bold' }}>
                NO: {noPercent.toFixed(1)}%
              </span>
            </div>
          )}
          {/* Arrow */}
          <div style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            marginLeft: '-4px',
            borderWidth: '4px',
            borderStyle: 'solid',
            borderColor: '#334155 transparent transparent transparent'
          }} />
        </motion.div>
      )}
    </div>
  );
}
