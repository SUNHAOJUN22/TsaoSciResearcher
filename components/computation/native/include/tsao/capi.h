#pragma once

#include <stdint.h>

#if defined(_WIN32)
  #if defined(TSAO_NATIVE_BUILD)
    #define TSAO_NATIVE_API __declspec(dllexport)
  #else
    #define TSAO_NATIVE_API __declspec(dllimport)
  #endif
#else
  #define TSAO_NATIVE_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define TSAO_NATIVE_ABI_VERSION 1u
#define TSAO_NATIVE_API_VERSION "1.1.0"
#define TSAO_NATIVE_DEVICE_NAME_CAPACITY 128u

enum TsaoNativeStatus {
    TSAO_NATIVE_STATUS_OK = 0,
    TSAO_NATIVE_STATUS_INVALID_ARGUMENT = 1,
    TSAO_NATIVE_STATUS_UNSUPPORTED_BACKEND = 2,
    TSAO_NATIVE_STATUS_RUNTIME_ERROR = 3,
    TSAO_NATIVE_STATUS_OUT_OF_RANGE = 4
};

enum TsaoNativeBackendMask {
    TSAO_NATIVE_BACKEND_CPU = 1u << 0,
    TSAO_NATIVE_BACKEND_OPENMP = 1u << 1,
    TSAO_NATIVE_BACKEND_CUDA = 1u << 2,
    TSAO_NATIVE_BACKEND_HIP = 1u << 3,
    TSAO_NATIVE_BACKEND_SYCL = 1u << 4
};

typedef struct TsaoNativeHardwareSummary {
    uint32_t abi_version;
    uint32_t logical_cpu_count;
    uint32_t backend_mask;
    uint32_t accelerator_count;
} TsaoNativeHardwareSummary;

typedef struct TsaoNativeDeviceInfo {
    uint32_t abi_version;
    uint32_t backend;
    uint32_t index;
    uint32_t architecture_major;
    uint32_t architecture_minor;
    uint64_t memory_bytes;
    char name[TSAO_NATIVE_DEVICE_NAME_CAPACITY];
} TsaoNativeDeviceInfo;

TSAO_NATIVE_API uint32_t tsao_native_abi_version(void);
TSAO_NATIVE_API const char* tsao_native_api_version(void);
TSAO_NATIVE_API const char* tsao_native_capabilities_json(void);
TSAO_NATIVE_API uint32_t tsao_native_compiled_backend_mask(void);
TSAO_NATIVE_API int32_t tsao_native_probe(TsaoNativeHardwareSummary* output);
TSAO_NATIVE_API uint32_t tsao_native_device_count(uint32_t backend);
TSAO_NATIVE_API int32_t tsao_native_device_info(
    uint32_t backend,
    uint32_t index,
    TsaoNativeDeviceInfo* output
);

#ifdef __cplusplus
}
#endif
