# Quick-start example

```bash
python scripts/init_project.py --name "PP conductive shielding" --question "Which formulation and dispersion mechanisms control resistivity stability?" --research-type mechanistic --output .
python scripts/route_task.py "检索聚丙烯半导体屏蔽料中炭黑选择性分散的文献"
python scripts/validate_project.py .tsao-research/project.yaml
python scripts/validate_figure.py examples/figure-contract.json
```
