import { describe, expect, it } from 'vitest';
import type { Product } from '@/types/index';
import {
  auditASTMStandards,
  calculatePolymerDescriptors,
  generateLammpsMDInput,
  predictPropertiesQSPR,
} from '@/utils/polymerPhysics';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'sample',
    gradeName: 'Sample grade',
    manufacturerId: 'm',
    manufacturer: 'Demo',
    categoryIds: ['cat_pp'],
    properties: {},
    createdAt: '2026-01-01',
    updatedAt: '2026-01-01',
    ...overrides,
  };
}

describe('curated polymer descriptor contract', () => {
  it('does not infer PP tacticity from the propylene monomer', () => {
    const result = calculatePolymerDescriptors('CC=C');
    expect(result.polymerName).toContain('tacticity unspecified');
    expect(result.isotacticIndexPotential).toBeUndefined();
    expect(result.modelVersion).toBe('curated-repeat-unit-library-2.1.0');
    expect(result.warnings.join(' ')).toContain('does not establish isotacticity');
  });

  it('does not infer HDPE architecture from ethylene alone', () => {
    const result = calculatePolymerDescriptors('C=C');
    expect(result.polymerName).toContain('architecture unspecified');
    expect(result.warnings.join(' ')).toContain('cannot determine branching');
  });

  it('rejects empty and unsupported monomer patterns instead of fabricating descriptors', () => {
    expect(() => calculatePolymerDescriptors('   ')).toThrow(/must not be empty/i);
    expect(() => calculatePolymerDescriptors('N#N')).toThrow(/unsupported monomer pattern/i);
    expect(() => calculatePolymerDescriptors('CC')).toThrow(/unsupported monomer pattern/i);
  });

  it('rejects composition-ambiguous EPDM input and keeps PS non-polar', () => {
    expect(() => calculatePolymerDescriptors('C=C.CC=C.C1C=CC2C1CC=C2'))
      .toThrow(/copolymer composition/i);
    expect(calculatePolymerDescriptors('C=Cc1ccccc1').polarity).toBe('Non-polar');
  });
});

describe('LAMMPS template numerical and unit contract', () => {
  it('validates configuration boundaries', () => {
    expect(() => generateLammpsMDInput({
      polymerType: 'PP\nread_data injected.data',
      atomsCount: 10,
      tempK: 300,
      crossLinkDegree: 0,
    })).toThrow(/single-line/i);
    expect(() => generateLammpsMDInput({
      polymerType: 'PP',
      atomsCount: 0,
      tempK: 300,
      crossLinkDegree: 0,
    })).toThrow(/atomsCount/i);
    expect(() => generateLammpsMDInput({
      polymerType: 'PP',
      atomsCount: 10,
      tempK: 300,
      coolingEndK: 300,
      crossLinkDegree: 0,
    })).toThrow(/lower than/i);
    expect(() => generateLammpsMDInput({
      polymerType: 'PP',
      atomsCount: 10,
      tempK: 300,
      crossLinkDegree: 0,
      msdGroup: 'all;clear',
    })).toThrow(/group ID/i);
  });

  it('freezes the initial length and reports tensile stress in MPa', () => {
    const input = generateLammpsMDInput({
      polymerType: 'Crosslinked PP',
      atomsCount: 50_000,
      tempK: 300,
      crossLinkDegree: 2.5,
    });
    expect(input).toContain('variable        L0 equal $(lx)');
    expect(input).toContain('variable        stressX_MPa equal -pxx*0.101325');
    expect(input).toContain('remap x');
    expect(input).toContain('compute         tracked_msd all msd');
    expect(input).toContain('temp 300 190');
    expect(input).not.toContain('stressX equal -press');
    expect(input).toContain('metadata only');
  });

  it('honours explicit cooling, timestep and MSD-group inputs', () => {
    const input = generateLammpsMDInput({
      polymerType: 'PP screening cell',
      atomsCount: 12_000,
      tempK: 450,
      coolingStartK: 450,
      coolingEndK: 300,
      coolingSteps: 150_000,
      timestepFs: 0.5,
      crossLinkDegree: 0,
      msdGroup: 'polymer',
    });
    expect(input).toContain('variable        timestep_fs equal 0.5');
    expect(input).toContain('compute         tracked_msd polymer msd');
    expect(input).toContain('temp 450 300');
    expect(input).toContain('run             150000');
    expect(input).toContain('Nominal programmed rate:');
  });
});

describe('PP-like QSPR screening contract', () => {
  it('rejects non-physical inputs before fractional powers are evaluated', () => {
    expect(() => predictPropertiesQSPR(0.9, -1, 30)).toThrow(/mfr/i);
    expect(() => predictPropertiesQSPR(Number.NaN, 2, 30)).toThrow(/density/i);
    expect(() => predictPropertiesQSPR(0.9, 2, 0)).toThrow(/tensileYield/i);
  });

  it('uses the two-phase density weight-fraction crystallinity relation', () => {
    const amorphous = predictPropertiesQSPR(0.852, 2, 30);
    const crystalline = predictPropertiesQSPR(0.943, 2, 30);
    expect(amorphous.calculatedCrystallineRatio).toBe(0);
    expect(crystalline.calculatedCrystallineRatio).toBe(100);
    expect(crystalline.crystallinityModel).toBe('two-phase-density-weight-fraction');
    expect(crystalline.warnings.length).toBeGreaterThan(0);
  });

  it('keeps all screening outputs finite and hardness bounded', () => {
    const result = predictPropertiesQSPR(0.905, 3.5, 34);
    for (const value of [
      result.estimatedFlexuralModulusMPa,
      result.predictedElongationAtBreak,
      result.calculatedCrystallineRatio,
      result.estimatedIzodImpactStrengthKJ,
      result.molarVolumeCm3PerMol,
    ]) expect(Number.isFinite(value)).toBe(true);
    expect(Number(result.shoreHardnessEstimate.slice(1))).toBeLessThanOrEqual(100);
    expect(result.swellingRatioEPDM).toBeUndefined();
  });
});

describe('ASTM-oriented screening audit', () => {
  it('uses strict parsing and does not treat blank text as numeric zero', () => {
    const result = auditASTMStandards([product({
      properties: {
        density: { value: '   ', unit: 'g/cm³' },
        mfr: { value: '12abc', unit: 'g/10min' },
      },
    })])[0];
    expect(result.status).toBe('WARNING');
    expect(result.findings[0]).toContain('No finite values');
  });

  it('normalizes supported density and modulus units before screening', () => {
    const result = auditASTMStandards([product({
      properties: {
        density: { value: 905, unit: 'kg/m³' },
        flexuralModulus: { value: 1.5, unit: 'GPa' },
      },
    })])[0];
    expect(result.status).toBe('PASSED');
    expect(result.standardsTested).toContain('ASTM D792 / ISO 1183 (Density screening)');
    expect(result.standardsTested).toContain('ASTM D790 / ISO 178 (Flexural screening)');
  });

  it('never downgrades a critical finding when later warnings are added', () => {
    const result = auditASTMStandards([product({
      properties: {
        mfr: { value: 200, unit: 'g/10min' },
        tensileYield: { value: 10, unit: 'MPa' },
      },
    })])[0];
    expect(result.status).toBe('CRITICAL');
    expect(result.findings.length).toBe(2);
  });

  it('does not misclassify PPS category identifiers as PP', () => {
    const result = auditASTMStandards([product({
      categoryIds: ['cat_pps'],
      properties: { density: { value: 1.35, unit: 'g/cm³' } },
    })])[0];
    expect(result.category).toBe('Unknown');
    expect(result.status).toBe('PASSED');
  });

  it('warns and skips unsupported or missing physical units', () => {
    const [unsupported, missing] = auditASTMStandards([
      product({ properties: { density: { value: 0.905, unit: 'lb/ft³' } } }),
      product({ properties: { density: { value: 0.905 } } }),
    ]);
    for (const result of [unsupported, missing]) {
      expect(result.status).toBe('WARNING');
      expect(result.findings.join(' ')).toContain('unsupported unit');
      expect(result.standardsTested).toHaveLength(0);
    }
  });

  it('does not hide malformed telemetry when another property is valid', () => {
    const result = auditASTMStandards([product({
      properties: {
        density: { value: '12abc', unit: 'g/cm³' },
        mfr: { value: 12, unit: 'g/10min' },
      },
    })])[0];
    expect(result.status).toBe('WARNING');
    expect(result.standardsTested).toContain('ASTM D1238 / ISO 1133 (MFR screening)');
    expect(result.findings.join(' ')).toContain('malformed numeric value');
  });
});
