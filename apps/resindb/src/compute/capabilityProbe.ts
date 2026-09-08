import type { ComputeCapabilities } from './types';

type NavigatorWithComputeHints = Navigator & {
  deviceMemory?: number;
  gpu?: unknown;
};

type WebAssemblyValidator = Pick<typeof WebAssembly, 'validate'>;

export interface ComputeProbeEnvironment {
  navigator?: Partial<NavigatorWithComputeHints>;
  webAssembly?: WebAssemblyValidator;
  sharedArrayBuffer?: boolean;
  crossOriginIsolated?: boolean;
  edgeService?: boolean;
}

const SIMD_PROBE_MODULE = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
  0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b,
  0x03, 0x02, 0x01, 0x00,
  0x0a, 0x08, 0x01, 0x06, 0x00, 0x41, 0x00, 0xfd, 0x0f, 0x0b,
]);

function getDefaultNavigator(): Partial<NavigatorWithComputeHints> | undefined {
  return typeof navigator === 'undefined'
    ? undefined
    : (navigator as NavigatorWithComputeHints);
}

function getDefaultWebAssembly(): WebAssemblyValidator | undefined {
  return typeof WebAssembly === 'undefined' ? undefined : WebAssembly;
}

function normalizeHardwareConcurrency(value: number | undefined): number {
  return Number.isFinite(value) && (value ?? 0) > 0 ? Math.max(1, Math.floor(value!)) : 1;
}

function normalizeDeviceMemory(value: number | undefined): number | undefined {
  return Number.isFinite(value) && (value ?? 0) > 0 ? value : undefined;
}

export function supportsWasmSimd(webAssembly: WebAssemblyValidator | undefined): boolean {
  if (!webAssembly) return false;
  try {
    return webAssembly.validate(SIMD_PROBE_MODULE);
  } catch {
    return false;
  }
}

export function probeComputeCapabilities(
  environment: ComputeProbeEnvironment = {},
): ComputeCapabilities {
  const navigatorLike = environment.navigator ?? getDefaultNavigator();
  const webAssembly = environment.webAssembly ?? getDefaultWebAssembly();
  const sharedArrayBuffer = environment.sharedArrayBuffer
    ?? typeof SharedArrayBuffer !== 'undefined';
  const isolated = environment.crossOriginIsolated
    ?? globalThis.crossOriginIsolated === true;
  const wasm = Boolean(webAssembly);

  return {
    hardwareConcurrency: normalizeHardwareConcurrency(navigatorLike?.hardwareConcurrency),
    deviceMemoryGiB: normalizeDeviceMemory(navigatorLike?.deviceMemory),
    wasm,
    wasmSimd: wasm && supportsWasmSimd(webAssembly),
    wasmThreads: wasm && sharedArrayBuffer && isolated,
    sharedArrayBuffer,
    crossOriginIsolated: isolated,
    webgpu: Boolean(navigatorLike?.gpu),
    edgeService: environment.edgeService ?? false,
  };
}
