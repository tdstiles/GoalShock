import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import ButtonText from './ButtonText';

describe('ButtonText Component', () => {
    it('should split text into individual spans', () => {
        const { container } = render(<ButtonText>Hello</ButtonText>);
        const spans = container.querySelectorAll('span.button-chars');

        expect(spans).toHaveLength(5);
        expect(spans[0]).toHaveTextContent('H');
        expect(spans[1]).toHaveTextContent('e');
        expect(spans[2]).toHaveTextContent('l');
        expect(spans[3]).toHaveTextContent('l');
        expect(spans[4]).toHaveTextContent('o');
    });

    it('should properly handle spaces with non-breaking space characters', () => {
        const { container } = render(<ButtonText>A B</ButtonText>);
        const spans = container.querySelectorAll('span.button-chars');

        expect(spans).toHaveLength(3);
        expect(spans[0]).toHaveTextContent('A');
        // react-testing-library toHaveTextContent strips multiple spaces and weird whitespaces
        // we can test textContent directly on the DOM element
        expect(spans[1].textContent).toBe('\u00A0');
        expect(spans[2]).toHaveTextContent('B');
    });

    it('should apply transition delays incrementally', () => {
        const { container } = render(<ButtonText>ABC</ButtonText>);
        const spans = container.querySelectorAll('span.button-chars');

        expect(spans).toHaveLength(3);
        expect(spans[0]).toHaveStyle('transition-delay: 0s');
        expect(spans[1]).toHaveStyle('transition-delay: 0.02s');
        expect(spans[2]).toHaveStyle('transition-delay: 0.04s');
    });

    it('should handle empty strings without crashing', () => {
        const { container } = render(<ButtonText>{''}</ButtonText>);
        const spans = container.querySelectorAll('span.button-chars');

        expect(spans).toHaveLength(0);
    });
});
