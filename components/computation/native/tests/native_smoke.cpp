#include "tsao/capi.h"

#include <cstdlib>
#include <cstring>

int main() {
    if (tsao_native_abi_version() != TSAO_NATIVE_ABI_VERSION) {
        return EXIT_FAILURE;
    }
    if (std::strcmp(tsao_native_api_version(), TSAO_NATIVE_API_VERSION) != 0) {
        return EXIT_FAILURE;
    }
    const char* capabilities = tsao_native_capabilities_json();
    if (capabilities == nullptr || std::strstr(capabilities, "\"cpu\"") == nullptr) {
        return EXIT_FAILURE;
    }
    const uint32_t compiled = tsao_native_compiled_backend_mask();
    if ((compiled & TSAO_NATIVE_BACKEND_CPU) == 0u) {
        return EXIT_FAILURE;
    }
    TsaoNativeHardwareSummary summary{};
    if (tsao_native_probe(&summary) != TSAO_NATIVE_STATUS_OK) {
        return EXIT_FAILURE;
    }
    if (summary.abi_version != TSAO_NATIVE_ABI_VERSION || summary.logical_cpu_count < 1u) {
        return EXIT_FAILURE;
    }
    if ((summary.backend_mask & TSAO_NATIVE_BACKEND_CPU) == 0u) {
        return EXIT_FAILURE;
    }
    if ((summary.backend_mask & ~compiled) != 0u) {
        return EXIT_FAILURE;
    }
    const uint32_t cuda_count = tsao_native_device_count(TSAO_NATIVE_BACKEND_CUDA);
    if (summary.accelerator_count != cuda_count) {
        return EXIT_FAILURE;
    }
    if (cuda_count > 0u) {
        TsaoNativeDeviceInfo device{};
        if (tsao_native_device_info(TSAO_NATIVE_BACKEND_CUDA, 0u, &device) !=
            TSAO_NATIVE_STATUS_OK) {
            return EXIT_FAILURE;
        }
        if (device.abi_version != TSAO_NATIVE_ABI_VERSION || device.name[0] == '\0') {
            return EXIT_FAILURE;
        }
    }
    TsaoNativeDeviceInfo device{};
    if (tsao_native_device_info(TSAO_NATIVE_BACKEND_CPU, 0u, &device) !=
        TSAO_NATIVE_STATUS_UNSUPPORTED_BACKEND) {
        return EXIT_FAILURE;
    }
    if (tsao_native_device_info(TSAO_NATIVE_BACKEND_CUDA, 0u, nullptr) !=
        TSAO_NATIVE_STATUS_INVALID_ARGUMENT) {
        return EXIT_FAILURE;
    }
    if (tsao_native_probe(nullptr) != TSAO_NATIVE_STATUS_INVALID_ARGUMENT) {
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
