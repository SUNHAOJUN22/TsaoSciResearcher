# TsaoDFT 验收级代码与 README 自动改造 Prompt

> 本文件是可重复执行的仓库修改规范。它以当前 `main` 为唯一基线，要求代码、文档、图件和机器证据同步演进，禁止只做视觉包装。

## 目标

把 `SUNHAOJUN22/TsaoDFT_skill` 改造成可直接验收的、双语、数学化、证据优先的 DFT 科研操作系统：

- Python 保持为科学控制面；
- Gaussian、VASP、Quantum ESPRESSO、CP2K 保持外部专业引擎边界；
- 仓库自有数值核必须具有确定性 CPU reference、严格有限数值输入、数值等价测试和安全 fallback；
- README 必须准确反映真实代码、真实质量门和真实资格状态；
- 不得虚构许可证、外部引擎执行、GPU/CUDA 内核或加速比。

## 必须执行的修改

1. **代码与合同**
   - 保留并验证 `strict_numeric.py`、`acceleration_registry.py`、`neighbor_list.py`、`engine_scan_core.py`、benchmark/campaign/evidence 合同；
   - 对新增文档建立机器可执行的 README 数学与策略 validator；
   - validator 必须进入永久质量门，未知/缺失公式、命令、图件或免责声明必须 fail-closed。

2. **中英文 README**
   - 同步重写 `README.md` 与 `README_EN.md`；
   - 至少覆盖 Kohn–Sham 方程、电子密度、总能量泛函、SCF 残差、Hellmann–Feynman 力、周期积分、minimum-image、cell-list 复杂度、数值容差、性能比、Eyring/TST、ML 不确定度与 OOD；
   - 给出结构准备、Parser、Gaussian、周期 DFT、HPC、资格证据、Windows/Linux 的使用策略和可执行命令；
   - 公式用于解释合同和工作流，不得伪装成仓库已经执行的科学结果。

3. **图件**
   - 保留唯一受治理 AI 封面；
   - 新增与真实代码一致的 AI-assisted deterministic SVG；
   - 每幅技术图必须包含 `SYNTHETIC DEMO · NOT SCIENTIFIC DATA` 或同等醒目标记；
   - 图件不得伪装为轨道、能带、DOS、势能面或实验结果。

4. **验收与 CI**
   - 只修改唯一 `main`，不建 branch/PR，不 force push；
   - 更新 release acceptance、质量门顺序测试、README visual/math validator 测试；
   - 运行 Linux Python 3.10/3.12/3.13、Windows PowerShell、SBOM、CodeQL；
   - 只有最终 HEAD 6/6 全绿才可报告完成。

## 非主张

- `CUDA-X aware` 不等于 CUDA-X 已执行；
- `SOFTWARE_ACCEPTANCE_READY` 只覆盖仓库软件、合同、文档和永久 CI；
- Gaussian/VASP/QE/CP2K 正确性与性能资格在缺少真实二进制、许可证、固定输入、硬件身份、科学参考值和重复运行时必须保持 `EXTERNAL_HOLD`。
