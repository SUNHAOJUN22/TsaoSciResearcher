import { describe, expect, it } from 'vitest';
import { fitSingleLineFontSize } from '../../scripts/report-layout.mjs';

describe('validation report layout', () => {
  const measure = (text: string, size: number) => text.length * size * 0.55;

  it('keeps short values at the preferred size', () => {
    expect(fitSingleLineFontSize('PASS', 140, measure)).toBe(18);
  });

  it('shrinks long acceptance states until they fit', () => {
    const size = fitSingleLineFontSize('EVIDENCE_INCOMPLETE', 141, measure);
    expect(size).toBeLessThan(18);
    expect(measure('EVIDENCE_INCOMPLETE', size)).toBeLessThanOrEqual(141);
  });

  it('uses the minimum size when the available width is too small', () => {
    expect(fitSingleLineFontSize('EVIDENCE_INCOMPLETE', 5, measure)).toBe(8);
  });
});
