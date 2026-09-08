import { paretoFrontIndices, type ParetoDirection } from '@/compute/pareto';

const PARETO_MODEL_VERSION = 'pareto-frontier-2.0.0';

export type ParetoObjective = {
  key: string;
  minimize: boolean;
};

export type ParetoMessage = {
  type: 'COMPUTE_PARETO';
  payload: {
    data: { id: string; values: Record<string, number> }[];
    objectives: ParetoObjective[];
  };
};

export type ParetoResponse = {
  type: 'PARETO_RESULT';
  payload: {
    paretoIds: string[];
    modelVersion: typeof PARETO_MODEL_VERSION;
    algorithm: 'two-objective-sort-sweep' | 'incremental-front-maintenance';
    validPoints: number;
  };
} | {
  type: 'ERROR';
  payload: { message: string };
};

self.onmessage = (event: MessageEvent<ParetoMessage>) => {
  try {
    const { data, objectives } = event.data.payload;
    if (!objectives.length || !data.length) {
      self.postMessage({
        type: 'PARETO_RESULT',
        payload: {
          paretoIds: (data ?? []).map((item) => item.id),
          modelVersion: PARETO_MODEL_VERSION,
          algorithm: objectives.length === 2
            ? 'two-objective-sort-sweep'
            : 'incremental-front-maintenance',
          validPoints: data?.length ?? 0,
        },
      } satisfies ParetoResponse);
      return;
    }
    const keys = objectives.map((objective) => objective.key);
    if (new Set(keys).size !== keys.length) throw new Error('Pareto objective keys must be unique.');
    const validData = data.filter((item) => (
      item
      && item.values
      && keys.every((key) => Number.isFinite(Number(item.values[key])))
    ));
    const points = validData.map((item) => keys.map((key) => Number(item.values[key])));
    const directions: ParetoDirection[] = objectives.map((objective) => (
      objective.minimize ? 'minimize' : 'maximize'
    ));
    const frontIndices = paretoFrontIndices(points, directions);
    self.postMessage({
      type: 'PARETO_RESULT',
      payload: {
        paretoIds: frontIndices.map((index) => validData[index].id),
        modelVersion: PARETO_MODEL_VERSION,
        algorithm: objectives.length === 2
          ? 'two-objective-sort-sweep'
          : 'incremental-front-maintenance',
        validPoints: validData.length,
      },
    } satisfies ParetoResponse);
  } catch (error) {
    self.postMessage({
      type: 'ERROR',
      payload: { message: error instanceof Error ? error.message : 'Unknown error' },
    } satisfies ParetoResponse);
  }
};
