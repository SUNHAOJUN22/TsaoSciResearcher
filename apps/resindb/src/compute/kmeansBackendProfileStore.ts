import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import {
  createKMeansBenchmarkEnvironment,
  validateKMeansBackendBenchmarkProfile,
  type KMeansBackendBenchmarkProfile,
  type KMeansBenchmarkEnvironment,
} from './kmeansBackendPolicy';
import {
  assessKMeansProfileMigration,
  type KMeansProfileMigrationEvent,
} from './kmeansProfileMigration';
import { createKMeansWorkerBenchmarkEnvironment } from './kmeansWorkerEnvironment';

const PROFILE_DATABASE_NAME = 'resindb-kmeans-backend-profile-v1';
const PROFILE_DATABASE_VERSION = 1;
const PROFILE_STORE_NAME = 'profiles';
const ACTIVE_PROFILE_KEY = 'active';

export interface KMeansBackendProfileRecord {
  key: typeof ACTIVE_PROFILE_KEY;
  profile: KMeansBackendBenchmarkProfile;
  environment: KMeansBenchmarkEnvironment;
  savedAt: string;
  migrationHistory?: KMeansProfileMigrationEvent[];
}

interface KMeansBackendProfileDatabase extends DBSchema {
  profiles: {
    key: string;
    value: KMeansBackendProfileRecord;
  };
}

export interface KMeansBackendProfilePersistence {
  read(): Promise<KMeansBackendProfileRecord | undefined>;
  write(record: KMeansBackendProfileRecord): Promise<void>;
  remove(): Promise<void>;
}

export type KMeansBackendProfileLoadStatus =
  | 'valid'
  | 'missing'
  | 'invalid'
  | 'unavailable'
  | 'error';

export interface KMeansBackendProfileLoadResult {
  status: KMeansBackendProfileLoadStatus;
  profile: KMeansBackendBenchmarkProfile | null;
  environment: KMeansBenchmarkEnvironment | null;
  reason: string | null;
  savedAt: string | null;
  migration: KMeansProfileMigrationEvent | null;
  migrationHistory: readonly KMeansProfileMigrationEvent[];
}

export interface KMeansBackendProfileSaveResult {
  profile: KMeansBackendBenchmarkProfile;
  environment: KMeansBenchmarkEnvironment;
  savedAt: string;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function createIndexedDbPersistence(): KMeansBackendProfilePersistence {
  let databasePromise: Promise<IDBPDatabase<KMeansBackendProfileDatabase>> | null = null;

  const getDatabase = async (): Promise<IDBPDatabase<KMeansBackendProfileDatabase>> => {
    if (typeof indexedDB === 'undefined') {
      throw new Error('IndexedDB is unavailable in this environment');
    }
    if (!databasePromise) {
      databasePromise = openDB<KMeansBackendProfileDatabase>(
        PROFILE_DATABASE_NAME,
        PROFILE_DATABASE_VERSION,
        {
          upgrade(database) {
            if (!database.objectStoreNames.contains(PROFILE_STORE_NAME)) {
              database.createObjectStore(PROFILE_STORE_NAME, { keyPath: 'key' });
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
    async read() {
      const database = await getDatabase();
      return database.get(PROFILE_STORE_NAME, ACTIVE_PROFILE_KEY);
    },
    async write(record) {
      const database = await getDatabase();
      await database.put(PROFILE_STORE_NAME, record);
    },
    async remove() {
      const database = await getDatabase();
      await database.delete(PROFILE_STORE_NAME, ACTIVE_PROFILE_KEY);
    },
  };
}

export interface KMeansBackendProfileStore {
  load(now?: Date): Promise<KMeansBackendProfileLoadResult>;
  save(
    profile: KMeansBackendBenchmarkProfile,
    environment: KMeansBenchmarkEnvironment,
    now?: Date,
  ): Promise<KMeansBackendProfileSaveResult>;
  clear(): Promise<void>;
}

export function createKMeansBackendProfileStore(
  persistence: KMeansBackendProfilePersistence = createIndexedDbPersistence(),
  currentEnvironment: () => KMeansBenchmarkEnvironment = createKMeansBenchmarkEnvironment,
): KMeansBackendProfileStore {
  return {
    async load(now = new Date()) {
      let record: KMeansBackendProfileRecord | undefined;
      let environment: KMeansBenchmarkEnvironment;
      try {
        environment = currentEnvironment();
        record = await persistence.read();
      } catch (error) {
        const reason = errorMessage(error);
        return {
          status: reason.includes('IndexedDB is unavailable') ? 'unavailable' : 'error',
          profile: null,
          environment: null,
          reason,
          savedAt: null,
          migration: null,
          migrationHistory: [],
        };
      }
      if (!record) {
        return {
          status: 'missing',
          profile: null,
          environment,
          reason: 'No device-local K-Means backend profile is stored',
          savedAt: null,
          migration: null,
          migrationHistory: [],
        };
      }

      const assessment = assessKMeansProfileMigration(
        record.profile,
        record.environment,
        environment,
        now,
      );
      const migrationHistory = [...(record.migrationHistory ?? [])];

      if (assessment.action === 'invalidate' || !assessment.profile) {
        if (assessment.event) migrationHistory.push(assessment.event);
        try {
          await persistence.remove();
        } catch {
          // Invalid profiles are never returned even if cleanup cannot complete.
        }
        return {
          status: 'invalid',
          profile: null,
          environment,
          reason: assessment.reason,
          savedAt: record.savedAt,
          migration: assessment.event,
          migrationHistory,
        };
      }

      if (assessment.action === 'migrate' && assessment.event) {
        migrationHistory.push(assessment.event);
        const migratedRecord: KMeansBackendProfileRecord = {
          ...record,
          profile: assessment.profile,
          environment,
          migrationHistory,
        };
        try {
          await persistence.write(migratedRecord);
        } catch (error) {
          return {
            status: 'error',
            profile: null,
            environment,
            reason: `Profile migration could not be persisted: ${errorMessage(error)}`,
            savedAt: record.savedAt,
            migration: assessment.event,
            migrationHistory,
          };
        }
      }

      return {
        status: 'valid',
        profile: assessment.profile,
        environment,
        reason: null,
        savedAt: record.savedAt,
        migration: assessment.event,
        migrationHistory,
      };
    },

    async save(profile, environment, now = new Date()) {
      const validation = validateKMeansBackendBenchmarkProfile(profile, environment, now);
      if (!validation.valid) {
        throw new Error(`K-Means backend profile is not valid for storage: ${validation.reason}`);
      }
      const savedAt = now.toISOString();
      await persistence.write({
        key: ACTIVE_PROFILE_KEY,
        profile,
        environment,
        savedAt,
        migrationHistory: [],
      });
      return { profile, environment, savedAt };
    },

    async clear() {
      await persistence.remove();
    },
  };
}

export const kmeansBackendProfileStore = createKMeansBackendProfileStore(
  createIndexedDbPersistence(),
  createKMeansWorkerBenchmarkEnvironment,
);
