import type { Product, PropertyValue } from '@/types/index';

/**
 * Conservative polymer-science helpers for screening, input generation and
 * standards-oriented data review. These functions do not replace molecular
 * simulation, manufacturer specifications or laboratory measurements.
 */

export interface PolymerDescriptors {
  polymerName: string;
  molecularWeightGPerMol: number; // repeat-unit molar mass for explicitly supported homopolymers
  monomerSMILES: string;
  glassTransitionTempK: number;
  glassTransitionTempC: number;
  typicalDensity: number; // g/cm³, descriptive midpoint only
  crystallinePotential: number; // descriptive screening percentage
  isotacticIndexPotential?: number; // only present when tacticity is independently specified
  polarity: 'Non-polar' | 'Highly-polar' | 'Moderate-polar';
  chainStiffness: 'Flexible' | 'Semi-rigid' | 'Rigid';
  chemicalFormula: string;
  modelVersion: 'curated-repeat-unit-library-2.1.0';
  method: 'curated-library';
  applicability: string;
  warnings: string[];
}

export interface QSPRPredictions {
  estimatedFlexuralModulusMPa: number;
  predictedElongationAtBreak: number; // %
  calculatedCrystallineRatio: number; // %
  estimatedIzodImpactStrengthKJ: number; // kJ/m²
  shoreHardnessEstimate: string;
  swellingRatioEPDM?: number;
  molarVolumeCm3PerMol: number;
  modelVersion: 'pp-screening-heuristic-2.0.0';
  applicability: string;
  crystallinityModel: 'two-phase-density-weight-fraction';
  warnings: string[];
}

export interface LammpsConfig {
  polymerType: string;
  atomsCount: number;
  tempK: number;
  crossLinkDegree: number; // %, metadata only; topology must already contain crosslinks
  coolingStartK?: number; // defaults to tempK; if supplied, it must match tempK
  coolingEndK?: number; // defaults to coolingStartK - 110 K
  coolingSteps?: number; // defaults to 200,000
  timestepFs?: number; // defaults to 1 fs
  msdGroup?: string; // existing LAMMPS group ID; defaults to built-in group "all"
}

export interface ASTMValidationResult {
  gradeName: string;
  category: string;
  status: 'PASSED' | 'WARNING' | 'CRITICAL';
  standardsTested: string[];
  findings: string[];
}

const DESCRIPTOR_MODEL_VERSION = 'curated-repeat-unit-library-2.1.0' as const;
const QSPR_MODEL_VERSION = 'pp-screening-heuristic-2.0.0' as const;
const STRICT_DECIMAL_PATTERN = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;

function celsiusToKelvin(celsius: number): number {
  return celsius + 273.15;
}

function normalizeSmiles(smiles: string): string {
  if (typeof smiles !== 'string') throw new TypeError('Monomer SMILES must be a string.');
  const normalized = smiles.trim().replace(/\s+/g, '');
  if (normalized.length === 0) throw new RangeError('Monomer SMILES must not be empty.');
  if (normalized.length > 500 || /[\r\n\0]/.test(normalized)) {
    throw new RangeError('Monomer SMILES exceeds the supported screening input contract.');
  }
  return normalized;
}

function descriptor(
  values: Omit<PolymerDescriptors, 'modelVersion' | 'method'>,
): PolymerDescriptors {
  return {
    ...values,
    modelVersion: DESCRIPTOR_MODEL_VERSION,
    method: 'curated-library',
  };
}

/**
 * Returns curated repeat-unit descriptors for a small, explicitly supported
 * library. The monomer alone cannot determine tacticity, branching,
 * copolymer composition, molar-mass distribution or processing history.
 */
export function calculatePolymerDescriptors(smiles: string): PolymerDescriptors {
  const cleanSmiles = normalizeSmiles(smiles);

  const epdmSignature = cleanSmiles.includes('.')
    && (cleanSmiles.includes('C1C=CC2C1CC=C2') || cleanSmiles.toUpperCase().includes('ENB'))
    && cleanSmiles.includes('C=C');
  if (epdmSignature) {
    throw new RangeError(
      'Unsupported copolymer composition: EPDM requires explicit ethylene/propylene/diene fractions and a validated repeat-unit representation.',
    );
  }

  if (new Set(['C=CCl', 'ClC=C', 'C(Cl)=C']).has(cleanSmiles)) {
    return descriptor({
      polymerName: 'Poly(vinyl chloride) (PVC)',
      molecularWeightGPerMol: 62.50,
      monomerSMILES: 'C=CCl',
      glassTransitionTempK: celsiusToKelvin(81),
      glassTransitionTempC: 81,
      typicalDensity: 1.38,
      crystallinePotential: 10,
      polarity: 'Highly-polar',
      chainStiffness: 'Semi-rigid',
      chemicalFormula: '(C2H3Cl)n',
      applicability: 'Typical unplasticized PVC repeat-unit descriptor.',
      warnings: ['Plasticizer, copolymer and formulation effects are not represented.'],
    });
  }

  if (
    cleanSmiles === 'C=Cc1ccccc1'
    || cleanSmiles === 'C=CC1=CC=CC=C1'
    || cleanSmiles === 'c1ccccc1C=C'
  ) {
    return descriptor({
      polymerName: 'Polystyrene (PS; stereoregularity unspecified)',
      molecularWeightGPerMol: 104.15,
      monomerSMILES: 'C=Cc1ccccc1',
      glassTransitionTempK: celsiusToKelvin(100),
      glassTransitionTempC: 100,
      typicalDensity: 1.05,
      crystallinePotential: 5,
      polarity: 'Non-polar',
      chainStiffness: 'Rigid',
      chemicalFormula: '(C8H8)n',
      applicability: 'Typical atactic general-purpose polystyrene descriptor.',
      warnings: ['Syndiotacticity, rubber modification and copolymer composition are not inferred.'],
    });
  }

  if (new Set(['CC=C', 'C=CC', 'C=C(C)']).has(cleanSmiles)) {
    return descriptor({
      polymerName: 'Polypropylene (PP; tacticity unspecified)',
      molecularWeightGPerMol: 42.08,
      monomerSMILES: 'CC=C',
      glassTransitionTempK: celsiusToKelvin(-10),
      glassTransitionTempC: -10,
      typicalDensity: 0.90,
      crystallinePotential: 45,
      polarity: 'Non-polar',
      chainStiffness: 'Flexible',
      chemicalFormula: '(C3H6)n',
      applicability: 'Typical PP family descriptor without tacticity or comonomer inference.',
      warnings: [
        'A propylene monomer does not establish isotacticity, crystallinity or impact-copolymer morphology.',
      ],
    });
  }

  if (new Set(['C=C', '[CH2]=[CH2]']).has(cleanSmiles)) {
    return descriptor({
      polymerName: 'Polyethylene (PE; branching architecture unspecified)',
      molecularWeightGPerMol: 28.05,
      monomerSMILES: 'C=C',
      glassTransitionTempK: celsiusToKelvin(-120),
      glassTransitionTempC: -120,
      typicalDensity: 0.92,
      crystallinePotential: 60,
      polarity: 'Non-polar',
      chainStiffness: 'Flexible',
      chemicalFormula: '(C2H4)n',
      applicability: 'Generic PE family descriptor; HDPE, LLDPE and LDPE architecture is not inferred.',
      warnings: [
        'Ethylene monomer identity alone cannot determine branching, density class or crystallinity.',
      ],
    });
  }

  throw new RangeError(
    'Unsupported monomer pattern: no curated descriptor model is available. Provide an explicitly supported repeat unit or use a validated cheminformatics workflow.',
  );
}

function validateLammpsConfig(config: LammpsConfig): {
  polymerType: string;
  fileSlug: string;
  atomsCount: number;
  coolingStartK: number;
  coolingEndK: number;
  coolingSteps: number;
  timestepFs: number;
  crossLinkDegree: number;
  msdGroup: string;
} {
  if (!config || typeof config !== 'object') throw new TypeError('LAMMPS configuration is required.');
  const polymerType = config.polymerType?.trim();
  if (!polymerType || polymerType.length > 80 || /[\r\n\0]/.test(polymerType)) {
    throw new RangeError('polymerType must be a single-line label between 1 and 80 characters.');
  }
  if (!Number.isInteger(config.atomsCount) || config.atomsCount < 1 || config.atomsCount > 1_000_000_000) {
    throw new RangeError('atomsCount must be an integer between 1 and 1,000,000,000.');
  }
  if (!Number.isFinite(config.tempK) || config.tempK <= 0 || config.tempK > 2_000) {
    throw new RangeError('tempK must be finite and lie in (0, 2,000] K.');
  }
  if (!Number.isFinite(config.crossLinkDegree) || config.crossLinkDegree < 0 || config.crossLinkDegree > 100) {
    throw new RangeError('crossLinkDegree must be a finite percentage between 0 and 100.');
  }

  const coolingStartK = config.coolingStartK ?? config.tempK;
  if (!Number.isFinite(coolingStartK) || coolingStartK <= 0 || coolingStartK > 2_000) {
    throw new RangeError('coolingStartK must be finite and lie in (0, 2,000] K.');
  }
  if (config.coolingStartK !== undefined && Math.abs(coolingStartK - config.tempK) > 1e-12) {
    throw new RangeError('coolingStartK must match tempK so the generated cooling stage starts from the equilibrated target.');
  }
  const coolingEndK = config.coolingEndK ?? (
    coolingStartK > 110 ? coolingStartK - 110 : coolingStartK / 2
  );
  if (!Number.isFinite(coolingEndK) || coolingEndK <= 0 || coolingEndK > 2_000) {
    throw new RangeError('coolingEndK must be finite and lie in (0, 2,000] K.');
  }
  if (coolingEndK >= coolingStartK) {
    throw new RangeError('coolingEndK must be lower than coolingStartK.');
  }

  const coolingSteps = config.coolingSteps ?? 200_000;
  if (!Number.isInteger(coolingSteps) || coolingSteps < 1 || coolingSteps > 1_000_000_000) {
    throw new RangeError('coolingSteps must be an integer between 1 and 1,000,000,000.');
  }
  const timestepFs = config.timestepFs ?? 1;
  if (!Number.isFinite(timestepFs) || timestepFs < 1e-6 || timestepFs > 10) {
    throw new RangeError('timestepFs must be finite and lie in [1e-6, 10] fs.');
  }

  const msdGroup = (config.msdGroup ?? 'all').trim();
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(msdGroup)) {
    throw new RangeError('msdGroup must be an existing single-token LAMMPS group ID.');
  }

  const fileSlug = polymerType.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'polymer';
  return {
    polymerType,
    fileSlug,
    atomsCount: config.atomsCount,
    coolingStartK,
    coolingEndK,
    coolingSteps,
    timestepFs,
    crossLinkDegree: config.crossLinkDegree,
    msdGroup,
  };
}

/**
 * Generates a validated LAMMPS starting template. It does not create molecular
 * topology, assign force-field coefficients, define a custom MSD group or
 * validate the referenced data file.
 */
export function generateLammpsMDInput(config: LammpsConfig): string {
  const {
    polymerType,
    fileSlug,
    atomsCount,
    coolingStartK,
    coolingEndK,
    coolingSteps,
    timestepFs,
    crossLinkDegree,
    msdGroup,
  } = validateLammpsConfig(config);
  const coolingRateKPerSecond = (coolingStartK - coolingEndK)
    / (coolingSteps * timestepFs * 1e-15);
  if (!Number.isFinite(coolingRateKPerSecond) || coolingRateKPerSecond <= 0) {
    throw new RangeError('The requested cooling interval, step count and timestep do not define a finite positive cooling rate.');
  }

  return `# =========================================================================
# ResinDB Pro LAMMPS polymer workflow template
# Material label: ${polymerType}
# Expected atom count metadata: ${atomsCount}
# IMPORTANT: topology, charges, class-II coefficients and crosslinks must be
# independently generated and validated before this input is used.
# =========================================================================

units           real
dimension       3
boundary        p p p
atom_style      full

pair_style      lj/class2/coul/long 12.0
bond_style      class2
angle_style     class2
dihedral_style  class2
improper_style  class2
kspace_style    pppm 1.0e-4

read_data       relaxed_${fileSlug}_structure.data

variable        target_temperature equal ${coolingStartK}
variable        timestep_fs equal ${timestepFs}
variable        crosslink_degree_percent equal ${crossLinkDegree}
# crosslink_degree_percent is provenance metadata only. This template does not
# create or delete bonds and does not infer atom types from the percentage.

neighbor        2.0 bin
neigh_modify    delay 0 every 1 check yes

thermo          100
thermo_style    custom step atoms temp pe ke etotal press pxx pyy pzz vol density
minimize        1.0e-4 1.0e-6 10000 100000

reset_timestep  0
timestep        \${timestep_fs}
velocity        all create \${target_temperature} 4928459 rot yes dist gaussian
fix             relaxation_npt all npt temp \${target_temperature} \${target_temperature} 100.0 iso 1.0 1.0 1000.0

dump            trajectory_dump all custom 2000 relaxation_dump.lammpstrj id type x y z q
dump_modify     trajectory_dump sort id
# The built-in group "all" tracks every atom. A custom msdGroup must already be
# defined by the supplied data/topology workflow before this command is used.
compute         tracked_msd ${msdGroup} msd
thermo_style    custom step atoms temp pe ke press pxx pyy pzz vol density c_tracked_msd[4]
run             100000

# Fast MD cooling profile for comparative simulation only; it is not an
# experimental cooling-rate reproduction and MSD alone does not determine Tg.
# Nominal programmed rate: ${coolingRateKPerSecond.toExponential(6)} K/s.
unfix           relaxation_npt
fix             cooling_npt all npt temp ${coolingStartK} ${coolingEndK} 100.0 iso 1.0 1.0 1000.0
thermo          500
run             ${coolingSteps}

# Uniaxial deformation with lateral NPT control. The class-II topology used here
# is not bond-reactive, so this section is a stress-strain sampling window, not
# a guaranteed fracture simulation.
unfix           cooling_npt
fix             lateral_npt all npt temp ${coolingEndK} ${coolingEndK} 100.0 y 1.0 1.0 1000.0 z 1.0 1.0 1000.0
run             0
variable        L0 equal $(lx)
variable        strain_rate_fs equal 1.0e-5
fix             tensile_deform all deform 1 x erate \${strain_rate_fs} units box remap x

# In real units, pxx is reported in atm. Negative pxx is tensile; convert atm to MPa.
variable        strainX equal (lx-v_L0)/v_L0
variable        stressX_MPa equal -pxx*0.101325
thermo_style    custom step temp vol density lx v_strainX v_stressX_MPa pxx pyy pzz pe etotal
run             150000
`;
}

function requireFiniteInRange(name: string, value: number, minimum: number, maximum: number): number {
  if (!Number.isFinite(value) || value < minimum || value > maximum) {
    throw new RangeError(`${name} must be finite and lie between ${minimum} and ${maximum}.`);
  }
  return value;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

/**
 * PP-like empirical screening proxy. The output is intentionally labelled as a
 * heuristic and must not be treated as measured or universally transferable.
 */
export function predictPropertiesQSPR(
  density: number,
  mfr: number,
  tensileYield: number,
): QSPRPredictions {
  requireFiniteInRange('density (g/cm³)', density, 0.80, 1.05);
  requireFiniteInRange('mfr (g/10 min)', mfr, 0.01, 500);
  requireFiniteInRange('tensileYield (MPa)', tensileYield, 1, 200);

  const amorphousDensity = 0.852;
  const crystallineDensity = 0.943;
  const rawCrystallineRatio = crystallineDensity * (density - amorphousDensity)
    / (density * (crystallineDensity - amorphousDensity)) * 100;
  const crystallineRatio = clamp(rawCrystallineRatio, 0, 100);

  // Empirical PP screening relation; this is not a Halpin-Tsai composite model.
  const flexuralModulus = tensileYield * 48.5 * (1 + crystallineRatio / 250);
  const elongation = clamp(
    4500 / tensileYield ** 0.75
      * (12 / (mfr + 0.1)) ** 0.15
      * (1 - crystallineRatio / 200),
    10,
    2_000,
  );
  const izod = clamp(
    750 / (tensileYield + 5)
      * (10 / (mfr + 0.2)) ** 0.22
      * (1 - crystallineRatio / 180),
    1.2,
    150,
  );

  const hardnessNumber = density < 0.88
    ? clamp(Math.round(50 + density * 30), 0, 100)
    : clamp(Math.round(40 + (density - 0.88) * 180 + tensileYield * 0.4), 0, 100);
  const hardness = `${density < 0.88 ? 'A' : 'D'}${hardnessNumber}`;
  const molarVolume = 42.08 / density;
  const warnings = [
    'Empirical PP-like screening proxy; not a validated universal QSPR or a substitute for test data.',
    'MFR comparisons require the same temperature, load and test standard.',
    'Fillers, copolymer morphology, tacticity, molecular-weight distribution and processing history are not modelled.',
    'EPDM swelling and crosslink density are outside this PP-like screening contract.',
  ];
  if (rawCrystallineRatio < 0 || rawCrystallineRatio > 100) {
    warnings.push('Density lies outside the two-phase reference interval; crystallinity was clamped to 0-100%.');
  }

  return {
    estimatedFlexuralModulusMPa: Math.round(flexuralModulus),
    predictedElongationAtBreak: Number(elongation.toFixed(1)),
    calculatedCrystallineRatio: Number(crystallineRatio.toFixed(1)),
    estimatedIzodImpactStrengthKJ: Number(izod.toFixed(2)),
    shoreHardnessEstimate: hardness,
    molarVolumeCm3PerMol: Number(molarVolume.toFixed(2)),
    modelVersion: QSPR_MODEL_VERSION,
    applicability: 'Unfilled PP-like screening range: density 0.80-1.05 g/cm³, MFR 0.01-500 g/10 min, tensile yield 1-200 MPa.',
    crystallinityModel: 'two-phase-density-weight-fraction',
    warnings,
  };
}

function parseFiniteNumericValue(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!STRICT_DECIMAL_PATTERN.test(trimmed)) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizedUnit(unit: string | undefined): string {
  return (unit ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '')
    .replace(/³/g, '3')
    .replace(/·/g, '')
    .replace(/−/g, '-');
}

function convertDensity(value: number, unit: string | undefined): number | null {
  const normalized = normalizedUnit(unit);
  if (['g/cm3', 'gcm-3', 'g/cc'].includes(normalized)) return value;
  if (['kg/m3', 'kgm-3'].includes(normalized)) return value / 1_000;
  return null;
}

function convertStressToMPa(value: number, unit: string | undefined): number | null {
  const normalized = normalizedUnit(unit);
  if (normalized === 'mpa') return value;
  if (normalized === 'gpa') return value * 1_000;
  if (normalized === 'kpa') return value / 1_000;
  if (normalized === 'pa') return value / 1_000_000;
  return null;
}

function convertMfr(value: number, unit: string | undefined): number | null {
  const normalized = normalizedUnit(unit);
  if (['g/10min', 'g10min-1', 'g/10mins'].includes(normalized)) return value;
  if (['kg/10min', 'kg10min-1'].includes(normalized)) return value * 1_000;
  return null;
}

interface Measurement {
  key: string;
  property: PropertyValue;
  rawValue: number;
}

interface MeasurementLookup {
  measurement: Measurement | null;
  invalid: Array<{ key: string; property: PropertyValue }>;
}

function findMeasurement(
  properties: Record<string, PropertyValue>,
  keys: readonly string[],
): MeasurementLookup {
  let measurement: Measurement | null = null;
  const invalid: Array<{ key: string; property: PropertyValue }> = [];
  for (const key of keys) {
    const property = properties[key];
    if (!property) continue;
    const rawValue = parseFiniteNumericValue(property.value);
    if (rawValue === null) invalid.push({ key, property });
    else if (measurement === null) measurement = { key, property, rawValue };
  }
  return { measurement, invalid };
}

function categoryFlags(product: Product): { category: string; isPP: boolean; isHDPE: boolean } {
  const directCategory = (product as Product & { category?: string }).category ?? '';
  const identifiers = [...(product.categoryIds ?? []), directCategory]
    .map((value) => value.trim().toLowerCase().replace(/[\s_-]+/g, ''));
  const isPP = identifiers.some((identifier) => (
    ['pp', 'catpp', 'polypropylene', '聚丙烯'].includes(identifier)
  ));
  const isHDPE = identifiers.some((identifier) => (
    ['hdpe', 'cathdpe', 'highdensitypolyethylene', '高密度聚乙烯'].includes(identifier)
  ));
  return {
    category: isPP ? 'PP' : isHDPE ? 'HDPE' : directCategory || 'Unknown',
    isPP,
    isHDPE,
  };
}

/**
 * Screens database values against broad engineering plausibility ranges. It is
 * not a standards-conformance test because specimen preparation, conditioning
 * and complete method parameters are not reproduced here.
 */
export function auditASTMStandards(products: Product[]): ASTMValidationResult[] {
  const severity = { PASSED: 0, WARNING: 1, CRITICAL: 2 } as const;

  return products.map((product) => {
    const { category, isPP, isHDPE } = categoryFlags(product);
    const findings: string[] = [];
    const dataQualityFindings: string[] = [];
    const standardsTested: string[] = [];
    let status: ASTMValidationResult['status'] = 'PASSED';
    const raiseStatus = (next: ASTMValidationResult['status']): void => {
      if (severity[next] > severity[status]) status = next;
    };
    const addStandard = (standard: string): void => {
      if (!standardsTested.includes(standard)) standardsTested.push(standard);
    };
    const unsupportedUnit = (measurement: Measurement, expected: string): void => {
      findings.push(`Property ${measurement.key} uses unsupported unit "${measurement.property.unit ?? '(missing)'}"; expected ${expected}. The value was not screened.`);
      raiseStatus('WARNING');
    };
    const recordInvalidValues = (lookup: MeasurementLookup): void => {
      for (const invalid of lookup.invalid) {
        dataQualityFindings.push(
          `Property ${invalid.key} has a non-finite or malformed numeric value "${String(invalid.property.value)}"; the value was not screened.`,
        );
      }
    };

    const properties = product.properties ?? {};
    let evaluatedMeasurements = 0;

    const densityLookup = findMeasurement(properties, ['密度', 'density', 'Density']);
    recordInvalidValues(densityLookup);
    const densityMeasurement = densityLookup.measurement;
    if (densityMeasurement) {
      const density = convertDensity(densityMeasurement.rawValue, densityMeasurement.property.unit);
      if (density === null) unsupportedUnit(densityMeasurement, 'g/cm³ or kg/m³');
      else {
        evaluatedMeasurements += 1;
        addStandard('ASTM D792 / ISO 1183 (Density screening)');
        if (density <= 0 || density > 3) {
          findings.push(`Density [${density} g/cm³] is outside the supported polymer screening range (0, 3].`);
          raiseStatus('CRITICAL');
        } else if (isPP && (density < 0.890 || density > 0.920)) {
          findings.push(`Density [${density} g/cm³] deviates from typical Polypropylene boundaries (0.890 - 0.920 g/cm³). Review filler content, copolymer morphology, conditioning and method metadata.`);
          raiseStatus('WARNING');
        } else if (isHDPE && (density < 0.940 || density > 0.970)) {
          findings.push(`Density [${density} g/cm³] is outside the broad HDPE screening interval (0.940-0.970 g/cm³). Review branching, blend composition and measurement conditions.`);
          raiseStatus('WARNING');
        }
      }
    }

    const mfrLookup = findMeasurement(properties, [
      '熔体质量流动速率', 'mfr', 'mfi', 'MFR', 'MFI', '熔融指数', '流动速率',
    ]);
    recordInvalidValues(mfrLookup);
    const mfrMeasurement = mfrLookup.measurement;
    if (mfrMeasurement) {
      const mfr = convertMfr(mfrMeasurement.rawValue, mfrMeasurement.property.unit);
      if (mfr === null) unsupportedUnit(mfrMeasurement, 'g/10 min');
      else {
        evaluatedMeasurements += 1;
        addStandard('ASTM D1238 / ISO 1133 (MFR screening)');
        if (mfr <= 0) {
          findings.push(`MFR [${mfr} g/10 min] must be positive.`);
          raiseStatus('CRITICAL');
        } else if (mfr < 0.05) {
          findings.push(`MFR is very low [${mfr} g/10 min]. Confirm temperature, load, instrument range and extrusion suitability.`);
          raiseStatus('WARNING');
        } else if (mfr > 150) {
          findings.push(`MFR is very high [${mfr} g/10 min]. Confirm temperature/load conditions and assess low-molar-mass or brittleness risk.`);
          raiseStatus('CRITICAL');
        }
      }
    }

    const tensileLookup = findMeasurement(properties, [
      '拉伸屈服应力', 'tensileYield', 'tensileStrength', '拉伸强度',
      'Tensile Strength', '拉伸断裂应力',
    ]);
    recordInvalidValues(tensileLookup);
    const tensileMeasurement = tensileLookup.measurement;
    if (tensileMeasurement) {
      const tensile = convertStressToMPa(tensileMeasurement.rawValue, tensileMeasurement.property.unit);
      if (tensile === null) unsupportedUnit(tensileMeasurement, 'MPa, GPa, kPa or Pa');
      else {
        evaluatedMeasurements += 1;
        addStandard('ASTM D638 / ISO 527 (Tensile screening)');
        if (tensile <= 0 || tensile > 500) {
          findings.push(`Tensile value [${tensile} MPa] is outside the supported polymer screening range (0, 500].`);
          raiseStatus('CRITICAL');
        } else if (isPP && tensile < 15) {
          findings.push(`PP tensile yield/strength [${tensile} MPa] is below the broad screening interval. Review specimen state, elastomer content and test definition.`);
          raiseStatus('WARNING');
        }
      }
    }

    const flexuralLookup = findMeasurement(properties, [
      '弯曲模量', 'flexuralModulus', 'Flexural Modulus',
    ]);
    recordInvalidValues(flexuralLookup);
    const flexuralMeasurement = flexuralLookup.measurement;
    if (flexuralMeasurement) {
      const flexural = convertStressToMPa(flexuralMeasurement.rawValue, flexuralMeasurement.property.unit);
      if (flexural === null) unsupportedUnit(flexuralMeasurement, 'MPa or GPa');
      else {
        evaluatedMeasurements += 1;
        addStandard('ASTM D790 / ISO 178 (Flexural screening)');
        if (flexural <= 0 || flexural > 50_000) {
          findings.push(`Flexural modulus [${flexural} MPa] is outside the supported polymer screening range (0, 50,000].`);
          raiseStatus('CRITICAL');
        } else if (isPP && flexural < 600) {
          findings.push(`PP flexural modulus [${flexural} MPa] is below the broad screening interval; review impact modification and test conditions.`);
          raiseStatus('WARNING');
        } else if (isPP && flexural > 2_800) {
          findings.push(`PP flexural modulus [${flexural} MPa] exceeds the broad unfilled-resin interval and may indicate reinforcement or mineral filling.`);
          raiseStatus('WARNING');
        }
      }
    }

    if (dataQualityFindings.length > 0) {
      findings.push(...dataQualityFindings);
      raiseStatus('WARNING');
    }
    if (evaluatedMeasurements === 0) {
      findings.unshift('No finite values with supported units were available for density, MFR, tensile or flexural screening.');
      raiseStatus('WARNING');
    } else if (findings.length === 0) {
      findings.push('All physical telemetry vectors compile successfully against the configured broad polymer screening ranges. This is not a standards-conformance certificate.');
    }

    return {
      gradeName: product.gradeName || 'Unnamed Grade',
      category,
      status,
      standardsTested,
      findings,
    };
  });
}
