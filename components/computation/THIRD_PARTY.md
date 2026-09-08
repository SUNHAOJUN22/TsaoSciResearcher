# Third-party posture

TsaoSciComputation is independently implemented under MIT. It references public scientific software and acceleration technologies only for interoperability, planning, method vocabulary, and evidence contracts. No third-party source code, executable, binary library, container image, model weight, license key, pseudopotential, basis database, force field, driver, runtime, or copyrighted manual is vendored.

External tools retain their own licenses, export controls, citation requirements, platform support, and acceptable-use terms. Users must verify lawful access and cite the exact versions, builds, methods, hardware, precision modes, and datasets actually used. Commercial names such as Gaussian, VASP, Aspen, COMSOL, and Abaqus identify optional integration targets, not bundled software or verified availability.

The acceleration catalog may name CUDA, CUDA-X, cuTENSOR, cuEquivariance, nvmath-python, cuBLAS, cuSOLVER, cuSPARSE, cuFFT, NCCL, NVSHMEM, nvCOMP, GPUDirect Storage, TensorRT, RAPIDS, Warp, CuPy, DLPack, Arrow, Kokkos, ROCm/HIP, SYCL, OpenCL, MPI, and related technologies. These names are candidate integration metadata only. Their presence in documentation or registry data does not install them, grant a license, establish compatibility with a professional solver, prove a GPU is usable, or demonstrate numerical speedup or scientific validity.

Any optional native or accelerator backend must be acquired separately from its lawful source, pinned or otherwise version-bound where appropriate, integrity-checked, isolated from the dependency-free control plane, and evaluated against a CPU or analytical reference. The pure-Python control plane and CPU fallback remain the default portable path.
