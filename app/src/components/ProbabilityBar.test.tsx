
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import ProbabilityBar from './ProbabilityBar';

describe('ProbabilityBar', () => {
    it('should render correct percentages on hover', async () => {
        const { container } = render(<ProbabilityBar yesPrice={0.6} noPrice={0.4} />);
        const bar = container.firstChild as HTMLElement;

        await act(async () => {
            fireEvent.mouseEnter(bar);
        });

        expect(await screen.findByText('YES: 60.0%')).toBeInTheDocument();
        expect(await screen.findByText('NO: 40.0%')).toBeInTheDocument();
    });

    it('should handle normalization when sum is not 1', async () => {
        const { container } = render(<ProbabilityBar yesPrice={60} noPrice={40} />);
        const bar = container.firstChild as HTMLElement;

        await act(async () => {
            fireEvent.mouseEnter(bar);
        });

        expect(await screen.findByText('YES: 60.0%')).toBeInTheDocument();
        expect(await screen.findByText('NO: 40.0%')).toBeInTheDocument();
    });

    it('should handle zero values gracefully', async () => {
        const { container } = render(<ProbabilityBar yesPrice={0} noPrice={0} />);
        const bar = container.firstChild as HTMLElement;

        await act(async () => {
            fireEvent.mouseEnter(bar);
        });

        expect(await screen.findByText('No Data Available')).toBeInTheDocument();
    });

    it('should handle single sided probability', async () => {
         const { container } = render(<ProbabilityBar yesPrice={1} noPrice={0} />);
         const bar = container.firstChild as HTMLElement;

         await act(async () => {
            fireEvent.mouseEnter(bar);
        });

         expect(await screen.findByText('YES: 100.0%')).toBeInTheDocument();
         expect(await screen.findByText('NO: 0.0%')).toBeInTheDocument();
    });
});
