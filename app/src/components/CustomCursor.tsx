import { useEffect, useRef, useState } from 'react';

export default function CustomCursor() {
  const cursorRef = useRef<HTMLDivElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);
  const [isMagnifying, setIsMagnifying] = useState(false);

  useEffect(() => {
    const cursor = cursorRef.current;
    const dot = dotRef.current;
    if (!cursor || !dot) return;

    // Zero-lag cursor movement with magnifying glass detection
    const handleMouseMove = (e: MouseEvent) => {
      // Direct pixel-perfect positioning with will-change optimization
      cursor.style.left = `${e.clientX}px`;
      cursor.style.top = `${e.clientY}px`;

      // Detect if hovering over text elements
      const target = e.target as HTMLElement;
      const isOverText =
        target.tagName === 'P' ||
        target.tagName === 'H1' ||
        target.tagName === 'H2' ||
        target.tagName === 'H3' ||
        target.tagName === 'H4' ||
        target.tagName === 'H5' ||
        target.tagName === 'H6' ||
        target.tagName === 'SPAN' ||
        target.tagName === 'LABEL' ||
        target.tagName === 'A';

      // Simplified - removed performance-heavy text zoom
      if (isOverText) {
        setIsMagnifying(true);
      } else {
        setIsMagnifying(false);
      }
    };

    document.addEventListener('mousemove', handleMouseMove, { passive: true });

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <div
      ref={cursorRef}
      className={`custom-cursor ${isMagnifying ? 'magnifying' : ''}`}
      style={{
        position: 'fixed',
        transform: 'translate(-50%, -50%)',
        willChange: 'left, top',
        left: '-100px',
        top: '-100px',
        pointerEvents: 'none',
        zIndex: 9999999
      }}
    >
      <div ref={dotRef} className="cursor-dot" />
    </div>
  );
}
