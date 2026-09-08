import {
  validateKMeansBackendBenchmarkProfile,
  type KMeansBackendBenchmarkProfile,
  type KMeansBenchmarkEnvironment,
} from './kmeansBackendPolicy';

export const KMEANS_PROFILE_MIGRATION_POLICY_VERSION =
  'kmeans-profile-migration-policy-1.0.0';

export type KMeansProfileMigrationReason =
  | 'fingerprint-rekey-same-computational-environment'
  | 'runtime-version-changed'
  | 'runtime-kind-changed'
  | 'platform-changed'
  | 'architecture-changed'
  | 'logical-core-count-changed'
  | 'wasm-capability-changed'
  | 'wasm-simd-capability-changed'
  | 'wasm-thread-capability-changed'
  | 'stored-profile-invalid'
  | 'current-environment-validation-failed';

export interface KMeansProfileMigrationEvent {
  policyVersion: typeof KMEANS_PROFILE_MIGRATION_POLICY_VERSION;
  fromFingerprint: string;
  toFingerprint: string;
  reason: KMeansProfileMigrationReason;
  migratedAt: string;
  requiresRecalibration: boolean;
}

export interface KMeansProfileMigrationAssessment {
  action: 'none' | 'migrate' | 'invalidate';
  reason: string | null;
  profile: KMeansBackendBenchmarkProfile | null;
  event: KMeansProfileMigrationEvent | null;
}

function normalizeRuntimeVersion(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

function createEvent(
  stored: KMeansBenchmarkEnvironment,
  current: KMeansBenchmarkEnvironment,
  reason: KMeansProfileMigrationReason,
  now: Date,
  requiresRecalibration: boolean,
): KMeansProfileMigrationEvent {
  return {
    policyVersion: KMEANS_PROFILE_MIGRATION_POLICY_VERSION,
    fromFingerprint: stored.fingerprint,
    toFingerprint: current.fingerprint,
    reason,
    migratedAt: now.toISOString(),
    requiresRecalibration,
  };
}

function firstIncompatibleDifference(
  stored: KMeansBenchmarkEnvironment,
  current: KMeansBenchmarkEnvironment,
): KMeansProfileMigrationReason | null {
  if (stored.runtime !== current.runtime) return 'runtime-kind-changed';
  if (normalizeRuntimeVersion(stored.runtimeVersion) !== normalizeRuntimeVersion(current.runtimeVersion)) {
    return 'runtime-version-changed';
  }
  if (stored.platform !== current.platform) return 'platform-changed';
  if (stored.architecture !== current.architecture) return 'architecture-changed';
  if (stored.logicalCores !== current.logicalCores) return 'logical-core-count-changed';
  if (stored.wasm !== current.wasm) return 'wasm-capability-changed';
  if (stored.wasmSimd !== current.wasmSimd) return 'wasm-simd-capability-changed';
  if (stored.wasmThreads !== current.wasmThreads) return 'wasm-thread-capability-changed';
  return null;
}

/**
 * Performance profiles are deliberately not reused across browser/engine,
 * architecture, core-count, or WASM capability changes. The only supported
 * migration is a fingerprint re-key where every computational environment
 * field remains identical after stable normalization.
 */
export function assessKMeansProfileMigration(
  profile: KMeansBackendBenchmarkProfile,
  storedEnvironment: KMeansBenchmarkEnvironment,
  currentEnvironment: KMeansBenchmarkEnvironment,
  now = new Date(),
): KMeansProfileMigrationAssessment {
  const storedValidation = validateKMeansBackendBenchmarkProfile(
    profile,
    storedEnvironment,
    now,
  );
  if (!storedValidation.valid) {
    return {
      action: 'invalidate',
      reason: storedValidation.reason ?? 'stored profile is invalid',
      profile: null,
      event: createEvent(
        storedEnvironment,
        currentEnvironment,
        'stored-profile-invalid',
        now,
        true,
      ),
    };
  }

  if (storedEnvironment.fingerprint === currentEnvironment.fingerprint) {
    const currentValidation = validateKMeansBackendBenchmarkProfile(
      profile,
      currentEnvironment,
      now,
    );
    return currentValidation.valid
      ? { action: 'none', reason: null, profile, event: null }
      : {
          action: 'invalidate',
          reason: currentValidation.reason ?? 'current environment validation failed',
          profile: null,
          event: createEvent(
            storedEnvironment,
            currentEnvironment,
            'current-environment-validation-failed',
            now,
            true,
          ),
        };
  }

  const incompatibility = firstIncompatibleDifference(storedEnvironment, currentEnvironment);
  if (incompatibility) {
    return {
      action: 'invalidate',
      reason: `K-Means backend profile requires recalibration: ${incompatibility}`,
      profile: null,
      event: createEvent(
        storedEnvironment,
        currentEnvironment,
        incompatibility,
        now,
        true,
      ),
    };
  }

  const migratedProfile: KMeansBackendBenchmarkProfile = {
    ...profile,
    environmentFingerprint: currentEnvironment.fingerprint,
  };
  const migratedValidation = validateKMeansBackendBenchmarkProfile(
    migratedProfile,
    currentEnvironment,
    now,
  );
  if (!migratedValidation.valid) {
    return {
      action: 'invalidate',
      reason: migratedValidation.reason ?? 'migrated profile validation failed',
      profile: null,
      event: createEvent(
        storedEnvironment,
        currentEnvironment,
        'current-environment-validation-failed',
        now,
        true,
      ),
    };
  }

  return {
    action: 'migrate',
    reason: null,
    profile: migratedProfile,
    event: createEvent(
      storedEnvironment,
      currentEnvironment,
      'fingerprint-rekey-same-computational-environment',
      now,
      false,
    ),
  };
}
