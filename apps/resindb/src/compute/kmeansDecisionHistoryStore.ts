import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import type { KMeansAssignmentSessionEvidence } from './kmeansAssignment';

export const KMEANS_DECISION_HISTORY_SCHEMA_VERSION = 'kmeans-decision-history-1.0.0';
export const KMEANS_DECISION_HISTORY_LIMIT = 50;

export interface KMeansDecisionHistoryEntry {
  schemaVersion: typeof KMEANS_DECISION_HISTORY_SCHEMA_VERSION;
  timestamp: string;
  requestedBackend: 'auto' | 'typescript' | 'wasm';
  selectedBackend: 'typescript' | 'wasm';
  actualBackend: 'typescript' | 'wasm';
  reason: string;
  profileAccepted: boolean;
  profileRejectionReason: string | null;
  fallbackUsed: boolean;
  fallbackReason: string | null;
  workloadOperations: number;
  environmentFingerprint: string;
}

interface KMeansDecisionHistoryDatabase extends DBSchema {
  events: {
    key: number;
    value: KMeansDecisionHistoryEntry;
  };
}

export interface KMeansDecisionHistoryPersistence {
  add(entry: KMeansDecisionHistoryEntry): Promise<void>;
  readAll(): Promise<KMeansDecisionHistoryEntry[]>;
  clear(): Promise<void>;
}

function createIndexedDbPersistence(): KMeansDecisionHistoryPersistence {
  let databasePromise: Promise<IDBPDatabase<KMeansDecisionHistoryDatabase>> | null = null;

  const getDatabase = async (): Promise<IDBPDatabase<KMeansDecisionHistoryDatabase>> => {
    if (typeof indexedDB === 'undefined') {
      throw new Error('IndexedDB is unavailable in this environment');
    }
    if (!databasePromise) {
      databasePromise = openDB<KMeansDecisionHistoryDatabase>(
        'resindb-kmeans-decision-history-v1',
        1,
        {
          upgrade(database) {
            if (!database.objectStoreNames.contains('events')) {
              database.createObjectStore('events', { autoIncrement: true });
            }
          },
        },
      );
    }
    try {
      return await databasePromise;
    } catch (error) {
      databasePromise = null;
      throw error;
    }
  };

  return {
    async add(entry) {
      const database = await getDatabase();
      const transaction = database.transaction('events', 'readwrite');
      await transaction.store.add(entry);
      const keys = await transaction.store.getAllKeys();
      const excess = Math.max(0, keys.length - KMEANS_DECISION_HISTORY_LIMIT);
      for (let index = 0; index < excess; index++) {
        await transaction.store.delete(keys[index]);
      }
      await transaction.done;
    },
    async readAll() {
      const database = await getDatabase();
      return database.getAll('events');
    },
    async clear() {
      const database = await getDatabase();
      await database.clear('events');
    },
  };
}

export interface KMeansDecisionHistoryStore {
  append(entry: KMeansDecisionHistoryEntry): Promise<void>;
  load(): Promise<KMeansDecisionHistoryEntry[]>;
  clear(): Promise<void>;
}

export function createKMeansDecisionHistoryStore(
  persistence: KMeansDecisionHistoryPersistence = createIndexedDbPersistence(),
): KMeansDecisionHistoryStore {
  return {
    async append(entry) {
      if (entry.schemaVersion !== KMEANS_DECISION_HISTORY_SCHEMA_VERSION) {
        throw new TypeError('K-Means decision history schema version is incompatible');
      }
      if (!Number.isSafeInteger(entry.workloadOperations) || entry.workloadOperations < 0) {
        throw new RangeError('K-Means decision workload must be a non-negative safe integer');
      }
      if (!Number.isFinite(Date.parse(entry.timestamp))) {
        throw new TypeError('K-Means decision timestamp is invalid');
      }
      await persistence.add({ ...entry });
    },
    async load() {
      try {
        const entries = await persistence.readAll();
        return entries
          .filter((entry) => entry.schemaVersion === KMEANS_DECISION_HISTORY_SCHEMA_VERSION)
          .slice(-KMEANS_DECISION_HISTORY_LIMIT)
          .map((entry) => ({ ...entry }));
      } catch {
        return [];
      }
    },
    async clear() {
      await persistence.clear();
    },
  };
}

export function createKMeansDecisionHistoryEntry(
  evidence: KMeansAssignmentSessionEvidence,
  timestamp = new Date(),
): KMeansDecisionHistoryEntry {
  const decision = evidence.backendDecision;
  return {
    schemaVersion: KMEANS_DECISION_HISTORY_SCHEMA_VERSION,
    timestamp: timestamp.toISOString(),
    requestedBackend: decision.requestedBackend,
    selectedBackend: decision.selectedBackend,
    actualBackend: evidence.backend,
    reason: decision.reason,
    profileAccepted: decision.profileAccepted,
    profileRejectionReason: decision.profileRejectionReason,
    fallbackUsed: evidence.fallbackUsed,
    fallbackReason: evidence.fallbackReason,
    workloadOperations: decision.workloadOperations,
    environmentFingerprint: decision.environmentFingerprint,
  };
}

export const kmeansDecisionHistoryStore = createKMeansDecisionHistoryStore();
