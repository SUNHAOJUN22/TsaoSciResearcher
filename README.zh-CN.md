# TsaoSciResearcher 0.4.0

中文主文档请阅读 [README.md](README.md)。

TsaoSciResearcher 是面向自然科学与工程研究的证据优先 Agent Skill，包含 15 个工作流、158 项能力记录和 8 套 Draft 2020-12 JSON Schema。它强调可验证、可追溯和可复现，不把未执行的实验、计算或外部检索描述为已完成。

## 核心验证

```bash
python -m pip install -r requirements-dev.txt
python scripts/run_tests.py
python scripts/run_mutation_smoke.py
python scripts/performance_smoke.py
python scripts/validate_release.py
```

安全、状态机、Claim–Evidence、Figure Contract 和确定性发布说明见 [README.md](README.md) 与 [docs/VALIDATION.md](docs/VALIDATION.md)。
