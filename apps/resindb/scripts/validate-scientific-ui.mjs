import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const sourceRoot = join(root, 'src');
const artifactRoot = join(root, 'artifacts');

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const target = join(directory, entry.name);
      return entry.isDirectory() ? walk(target) : [target];
    })
    .sort();
}

const sourceFiles = walk(sourceRoot)
  .filter((file) => ['.ts', '.tsx'].includes(extname(file)));
const failures = [];
const read = (path) => readFileSync(join(root, path), 'utf8');

for (const file of sourceFiles) {
  const repositoryPath = relative(root, file);
  const text = readFileSync(file, 'utf8');
  if (
    (repositoryPath.startsWith('src/compute/') || repositoryPath.startsWith('src/workers/'))
    && /Math\.random\s*\(/.test(text)
  ) {
    failures.push(`${repositoryPath}: scientific compute path uses Math.random`);
  }
}

function requireText(path, text, message) {
  if (!existsSync(join(root, path))) {
    failures.push(`${path}: file is missing`);
    return;
  }
  if (!read(path).includes(text)) failures.push(`${path}: ${message}`);
}

function prohibitText(path, text, message) {
  if (existsSync(join(root, path)) && read(path).includes(text)) {
    failures.push(`${path}: ${message}`);
  }
}

requireText(
  'src/components/charts/scientificFigurePolicy.ts',
  'scientific-figure-policy-1.1.0',
  'current figure policy missing',
);
requireText(
  'src/components/charts/scientificFigurePolicy.ts',
  'SCIENTIFIC_FONT_FAMILY',
  'CJK-safe scientific typography missing',
);
requireText(
  'src/components/charts/ScientificEChart.tsx',
  'useDirtyRect: true',
  'shared dirty-rect chart host missing',
);
requireText(
  'src/components/charts/ScientificEChart.tsx',
  'useLanguage',
  'scientific chart states are not localized',
);
requireText(
  'src/components/charts/ScientificEChart.tsx',
  "typeof ResizeObserver === 'undefined'",
  'scientific chart resize fallback missing',
);
requireText(
  'src/components/charts/GpcDistribution.ts',
  'not measured GPC data',
  'GPC proxy boundary missing',
);
requireText(
  'src/components/charts/RheologyCurve.ts',
  'not fitted rheometry',
  'rheology proxy boundary missing',
);
requireText(
  'src/components/charts/FeatureImportanceChart.tsx',
  'not causality or SHAP',
  'ridge boundary missing',
);
requireText(
  'src/components/charts/WeibullChart.tsx',
  'not MLE',
  'Weibull estimator boundary missing',
);
requireText(
  'src/components/charts/DataVisualizer.tsx',
  'Ridge attribution is associative',
  'workspace scientific boundary missing',
);
requireText(
  'src/components/features/Analytics/ResinCapacityForecast.tsx',
  'not 95% confidence intervals',
  'capacity boundary missing',
);

const phase2lTargets = [
  {
    name: 'DependencyHeatmap',
    path: 'src/components/features/Product/DependencyHeatmap.tsx',
    legacyPath: 'src/components/features/Product/DependencyHeatmapLegacy.tsx',
    boundary: 'not statistical association or causal attribution',
    missingContract: 'unavailable (not zero)',
  },
  {
    name: 'RheologyGraph',
    path: 'src/components/charts/RheologyGraph.tsx',
    legacyPath: 'src/components/charts/RheologyGraphLegacy.tsx',
    boundary: 'not measured rheology',
    missingContract: 'sanitizePositiveRheologyPoints',
  },
];

const phase2lMigrations = phase2lTargets.map((target) => {
  const targetExists = existsSync(join(root, target.path));
  const legacyExists = existsSync(join(root, target.legacyPath));
  const source = targetExists ? read(target.path) : '';
  const blockers = [];
  if (!targetExists) blockers.push('target-file-missing');
  if (!source.includes('ScientificEChart')) blockers.push('shared-chart-host-missing');
  if (!source.includes('data-scientific-boundary')) blockers.push('scientific-boundary-not-embedded');
  if (!source.includes(target.boundary)) blockers.push('required-scientific-language-missing');
  if (!source.includes(target.missingContract)) blockers.push('missing-data-contract-not-explicit');
  if (/echarts\.init\s*\(/.test(source)) blockers.push('independent-echarts-init');
  if (/Legacy[A-Za-z]+/.test(source)) blockers.push('legacy-runtime-import');
  if (legacyExists) blockers.push('legacy-source-still-present');
  for (const blocker of blockers) failures.push(`${target.path}: ${blocker}`);
  return {
    name: target.name,
    status: blockers.length === 0 ? 'migrated' : 'blocker',
    sharedScientificEChart: source.includes('ScientificEChart'),
    scientificBoundaryEmbedded: source.includes('data-scientific-boundary'),
    legacySourceRemoved: !legacyExists,
    blockers,
  };
});

const remainingCompatibilityWrappers = [
  {
    name: 'DataVisualizer',
    wrapper: 'src/components/charts/DataVisualizer.tsx',
    legacy: 'src/components/charts/DataVisualizerLegacy.tsx',
  },
  {
    name: 'FormulaEditorModal',
    wrapper: 'src/components/modals/FormulaEditorModal.tsx',
    legacy: 'src/components/modals/FormulaEditorModalLegacy.tsx',
  },
  {
    name: 'PredictiveTrends',
    wrapper: 'src/components/features/Analytics/PredictiveTrends.tsx',
    legacy: 'src/components/features/Analytics/PredictiveTrendsLegacy.tsx',
  },
  {
    name: 'MaterialTrendForecaster',
    wrapper: 'src/components/features/Analytics/MaterialTrendForecaster.tsx',
    legacy: 'src/components/features/Analytics/MaterialTrendForecasterLegacy.tsx',
  },
  {
    name: 'ResinCapacityForecast',
    wrapper: 'src/components/features/Analytics/ResinCapacityForecast.tsx',
    legacy: 'src/components/features/Analytics/ResinCapacityForecastLegacy.tsx',
  },
];

for (const wrapper of remainingCompatibilityWrappers) {
  const wrapperExists = existsSync(join(root, wrapper.wrapper));
  const legacyExists = existsSync(join(root, wrapper.legacy));
  if (!wrapperExists) failures.push(`${wrapper.wrapper}: declared compatibility wrapper is missing`);
  if (!legacyExists) failures.push(`${wrapper.legacy}: declared Legacy implementation is missing`);
  if (wrapperExists) {
    const wrapperSource = read(wrapper.wrapper);
    const legacyStem = wrapper.legacy.split('/').at(-1)?.replace(/\.tsx$/, '') ?? '';
    if (!wrapperSource.includes(legacyStem)) {
      failures.push(`${wrapper.wrapper}: compatibility wrapper no longer imports ${legacyStem}`);
    }
  }
}

for (const target of phase2lTargets) {
  prohibitText(target.path, 'LegacyDependencyHeatmap', 'target still imports DependencyHeatmap Legacy runtime');
  prohibitText(target.path, 'LegacyRheologyGraph', 'target still imports RheologyGraph Legacy runtime');
}

const chartFiles = sourceFiles.filter((file) => (
  file.includes(`${join('src', 'components', 'charts')}`)
  && !file.endsWith('Legacy.tsx')
));
const directEchartsInitFiles = chartFiles
  .filter((file) => /echarts\.init\s*\(/.test(readFileSync(file, 'utf8')))
  .map((file) => relative(root, file));

const metrics = {
  schemaVersion: 'scientific-ui-audit-1.3.0',
  productionTypeScriptFiles: sourceFiles.length,
  chartFiles: chartFiles.length,
  directEchartsInitFiles,
  phase2lMigrations,
  legacyCompatibilityWrappers: remainingCompatibilityWrappers.map((entry) => entry.name),
  migratedCompatibilityWrappers: phase2lMigrations
    .filter((entry) => entry.status === 'migrated')
    .map((entry) => entry.name),
  localizedScientificFigureStates: true,
  cjkSafeScientificTypography: true,
  failures,
  acceptance: failures.length ? 'FAIL' : 'PASS',
};

mkdirSync(artifactRoot, { recursive: true });
writeFileSync(
  join(artifactRoot, 'scientific-ui-audit.json'),
  `${JSON.stringify(metrics, null, 2)}\n`,
);
console.log(JSON.stringify(metrics, null, 2));
if (failures.length) {
  throw new Error(`scientific UI audit failed:\n${failures.join('\n')}`);
}
