import { expect, test, describe } from 'vitest';
import { materialEngine } from '../../src/lib/materialScience';

describe('Material Engine - Units & Conversions', () => {
    test('calculatePearson works correctly', () => {
        const points: [number, number][] = [
            [1, 2], [2, 4], [3, 6], [4, 8]
        ];
        const pearson = materialEngine.calculatePearson(points);
        expect(pearson).toBeCloseTo(1, 4);
    });

    test('parseRheologyData handles valid inputs', () => {
        const dataStr = '1.0,100;10.0,50';
        const parsed = materialEngine.parseRheologyData(dataStr);
        expect(parsed).toEqual([
            { rate: 1.0, visc: 100 },
            { rate: 10.0, visc: 50 },
        ]);
    });
});

describe('Material Engine - Math safety guards', () => {
    test('calculateDistributionMoments handles n = 3 safely without dividing by zero', () => {
        const values = [10, 12, 11];
        const res = materialEngine.calculateDistributionMoments(values);
        expect(res).not.toBeNull();
        expect(res!.skewness).toBeTypeOf('number');
        expect(res!.kurtosis).toBe(0); // Kurtosis is guarded to 0 when n <= 3
    });

    test('analyzeCorrelation handles constant columns safely without crashing', () => {
        const points: [number, number][] = [[1, 2], [1, 2], [1, 2]];
        const res = materialEngine.analyzeCorrelation(points);
        expect(res).toBeNull();
    });

    test('calculatePValue handles r = 1 and r = -1 safely', () => {
        const p1 = materialEngine.calculatePValue(1.0, 10);
        const p2 = materialEngine.calculatePValue(-1.0, 10);
        expect(p1).toBe(0);
        expect(p2).toBe(0);
    });

    test('calculateSlopeConfidenceInterval handles division by zero ssX', () => {
        const points: [number, number][] = [[1, 2], [1, 4], [1, 6]];
        const res = materialEngine.calculateSlopeConfidenceInterval(points);
        expect(res).toBeNull();
    });

    test('analyzeDatalineIntegrity handles perfect fits with mse = 0 safely', () => {
        const points: [number, number][] = [[1, 2], [2, 4], [3, 6], [4, 8]];
        const res = materialEngine.analyzeDatalineIntegrity(points, 2, 0);
        expect(res).not.toBeNull();
        expect(res.healthScore).toBe(100);
        expect(res.influentialPointsCount).toBe(0);
    });
});
