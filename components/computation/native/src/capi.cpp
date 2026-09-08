#include "tsao/capi.h"

#include <algorithm>
#include <cstring>
#include <thread>

#if defined(TSAO_NATIVE_HAS_CUDA_RUNTIME)
  #include <cuda_runtime_api.h>
#endif

namespace {

constexpr const char* kCapabilities =
    "{\"abi_version\":1,\"api_version\":\"" TSAO_NATIVE_API_VERSION "\","
    "\"control_plane\":\"python\",\"native_language\":\"c++20\","
    "\"compiled_backend_query\":true,\"runtime_device_query\":true,"
    "\"candidate_backends\":[\"cpu\",\"openmp\",\"cuda\",\"hip\",\"sycl\"],"
    "\"claim_boundary\":\"Runtime discovery only; no solver support, speedup, convergence, "
    "physical validity, applicability, or authorization is claimed.\"}";

uint32_t compiled_backend_mask() {
    uint32_t mask = TSAO_NATIVE_BACKEND_CPU;
#if defined(_OPENMP)
    mask |= TSAO_NATIVE_BACKEND_OPENMP;
#endif
#if defined(TSAO_NATIVE_HAS_CUDA_RUNTIME)
    mask |= TSAO_NATIVE_BACKEND_CUDA;
#endif
#if defined(TSAO_NATIVE_HAS_HIP)
    mask |= TSAO_NATIVE_BACKEND_HIP;
#endif
#if defined(TSAO_NATIVE_HAS_SYCL)
    mask |= TSAO_NATIVE_BACKEND_SYCL;
#endif
    return mask;
}

uint32_t cuda_device_count() {
#if defined(TSAO_NATIVE_HAS_CUDA_RUNTIME)
    int count = 0;
    const auto status = cudaGetDeviceCount(&count);
    if (status != cudaSuccess || count <= 0) {
        return 0u;
    }
    return static_cast<uint32_t>(count);
#else
    return 0u;
#endif
}

void copy_device_name(char* destination, const char* source) {
    if (destination == nullptr) {
        return;
    }
    const char* safe_source = source == nullptr ? "unknown" : source;
    std::strncpy(destination, safe_source, TSAO_NATIVE_DEVICE_NAME_CAPACITY - 1u);
    destination[TSAO_NATIVE_DEVICE_NAME_CAPACITY - 1u] = '\0';
}

}  // namespace

uint32_t tsao_native_abi_version(void) {
    return TSAO_NATIVE_ABI_VERSION;
}

const char* tsao_native_api_version(void) {
    return TSAO_NATIVE_API_VERSION;
}

const char* tsao_native_capabilities_json(void) {
    return kCapabilities;
}

uint32_t tsao_native_compiled_backend_mask(void) {
    return compiled_backend_mask();
}

int32_t tsao_native_probe(TsaoNativeHardwareSummary* output) {
    if (output == nullptr) {
        return TSAO_NATIVE_STATUS_INVALID_ARGUMENT;
    }
    output->abi_version = TSAO_NATIVE_ABI_VERSION;
    const auto detected = std::thread::hardware_concurrency();
    output->logical_cpu_count = detected == 0u ? 1u : detected;
    output->backend_mask = TSAO_NATIVE_BACKEND_CPU;
#if defined(_OPENMP)
    output->backend_mask |= TSAO_NATIVE_BACKEND_OPENMP;
#endif
    output->accelerator_count = cuda_device_count();
    if (output->accelerator_count > 0u) {
        output->backend_mask |= TSAO_NATIVE_BACKEND_CUDA;
    }
    return TSAO_NATIVE_STATUS_OK;
}

uint32_t tsao_native_device_count(uint32_t backend) {
    if (backend == TSAO_NATIVE_BACKEND_CUDA) {
        return cuda_device_count();
    }
    return 0u;
}

int32_t tsao_native_device_info(
    uint32_t backend,
    uint32_t index,
    TsaoNativeDeviceInfo* output
) {
    if (output == nullptr) {
        return TSAO_NATIVE_STATUS_INVALID_ARGUMENT;
    }
    if (backend != TSAO_NATIVE_BACKEND_CUDA) {
        return TSAO_NATIVE_STATUS_UNSUPPORTED_BACKEND;
    }
#if defined(TSAO_NATIVE_HAS_CUDA_RUNTIME)
    const uint32_t count = cuda_device_count();
    if (index >= count) {
        return TSAO_NATIVE_STATUS_OUT_OF_RANGE;
    }
    cudaDeviceProp properties{};
    const auto status = cudaGetDeviceProperties(&properties, static_cast<int>(index));
    if (status != cudaSuccess) {
        return TSAO_NATIVE_STATUS_RUNTIME_ERROR;
    }
    output->abi_version = TSAO_NATIVE_ABI_VERSION;
    output->backend = TSAO_NATIVE_BACKEND_CUDA;
    output->index = index;
    output->architecture_major = static_cast<uint32_t>(std::max(properties.major, 0));
    output->architecture_minor = static_cast<uint32_t>(std::max(properties.minor, 0));
    output->memory_bytes = static_cast<uint64_t>(properties.totalGlobalMem);
    copy_device_name(output->name, properties.name);
    return TSAO_NATIVE_STATUS_OK;
#else
    (void)index;
    return TSAO_NATIVE_STATUS_UNSUPPORTED_BACKEND;
#endif
}
