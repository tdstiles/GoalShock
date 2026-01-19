import { motion } from 'framer-motion';

interface ProbabilityBarProps {
  yesPrice: number;
  noPrice: number;
}

export default function ProbabilityBar({ yesPrice, noPrice }: ProbabilityBarProps) {
  // Normalize prices to ensure they fill the bar (in case of vig or data issues)
  const total = yesPrice + noPrice || 1;
  const yesPercent = (yesPrice / total) * 100;
  const noPercent = (noPrice / total) * 100;

  return (
    <div
      style={{
        width: '100%',
        height: '6px',
        background: 'rgba(255,255,255,0.1)',
        borderRadius: '3px',
        overflow: 'hidden',
        display: 'flex',
        marginTop: '12px'
      }}
      title={`YES: ${(yesPercent).toFixed(1)}% | NO: ${(noPercent).toFixed(1)}%`}
    >
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${yesPercent}%` }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        style={{ height: '100%', background: '#10b981' }}
      />
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${noPercent}%` }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        style={{ height: '100%', background: '#ef4444' }}
      />
    </div>
  );
}
