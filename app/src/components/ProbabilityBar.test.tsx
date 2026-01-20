
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProbabilityBar from './ProbabilityBar';

describe('ProbabilityBar', () => {
    it('should render correct percentages', () => {
        const { container } = render(<ProbabilityBar yesPrice={0.6} noPrice={0.4} />);
        const bar = container.firstChild as HTMLElement;
        expect(bar).toHaveAttribute('title', 'YES: 60.0% | NO: 40.0%');
    });

    it('should handle normalization when sum is not 1', () => {
        const { container } = render(<ProbabilityBar yesPrice={60} noPrice={40} />);
        const bar = container.firstChild as HTMLElement;
        expect(bar).toHaveAttribute('title', 'YES: 60.0% | NO: 40.0%');
    });

    it('should handle zero values gracefully', () => {
        const { container } = render(<ProbabilityBar yesPrice={0} noPrice={0} />);
        const bar = container.firstChild as HTMLElement;
        // Since total is 0, it defaults to 1. 0/1 * 100 = 0
        expect(bar).toHaveAttribute('title', 'YES: 0.0% | NO: 0.0%');
    });

    it('should handle single sided probability', () => {
         const { container } = render(<ProbabilityBar yesPrice={1} noPrice={0} />);
         const bar = container.firstChild as HTMLElement;
         expect(bar).toHaveAttribute('title', 'YES: 100.0% | NO: 0.0%');
    });
});
