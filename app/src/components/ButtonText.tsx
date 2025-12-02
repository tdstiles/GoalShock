/**
 * ButtonText Component
 * Wraps each character in a span for individual animation effects
 */
interface ButtonTextProps {
  children: string;
}

export default function ButtonText({ children }: ButtonTextProps) {
  return (
    <>
      {children.split('').map((char, i) => (
        <span
          key={i}
          className="button-chars"
          style={{
            position: 'relative',
            display: 'inline-block',
            transitionDelay: `${i * 0.02}s`
          }}
        >
          {char === ' ' ? '\u00A0' : char}
        </span>
      ))}
    </>
  );
}
