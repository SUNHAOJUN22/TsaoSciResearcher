#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections.abc import Callable
from pathlib import Path
from runpy import run_path
from typing import Any

_COMMON = run_path(str(Path(__file__).resolve().parent / "common.py"))
load_structured: Callable[[str | Path], Any] = _COMMON["load_structured"]

STAGES = [
    ("P0", "G0", "任务、范围与治理"),
    ("P1", "G1", "证据、标准、专利与缺口"),
    ("P2", "G2", "产品需求、应用与CQA"),
    ("P3", "G3", "分析、原料、数据与测量"),
    ("P4", "G4", "化学路线与催化剂概念"),
    ("P5", "G5", "机理、动力学、物性与模型基础"),
    ("P6", "G6", "小试可行性与安全操作窗"),
    ("P7", "G7", "模型资格与可辨识性"),
    ("P8", "G8", "连续台架与动态验证"),
    ("P9", "G9", "分离、回收、后处理与循环"),
    ("P10", "G10", "中试设计基础"),
    ("P11", "G11", "中试执行、调和与模型更新"),
    ("P12", "G12", "示范与尺度代表性"),
    ("P13", "G13", "工业流程、设备、公用工程与排放"),
    ("P14", "G14", "控制、数字孪生、切换与可操作性"),
    ("P15", "G15", "HSE、可靠性、经济、环境、供应与IP"),
    ("P16", "G16", "产品、客户与法规资格"),
    ("P17", "G17", "工艺包冻结、试车与性能保证"),
    ("P18", "G18", "商业化后监测、变更与持续学习"),
]
WORKSTREAMS = [
    "governance",
    "evidence-ip",
    "product-quality",
    "chemistry",
    "analytics-data",
    "statistics-doe",
    "kinetics-properties",
    "reactor-multiphysics",
    "process-synthesis",
    "scaleup-pilot",
    "control-operations",
    "hse-reliability",
    "tea-supply-ip",
    "reporting-transfer",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    brief = load_structured(args.brief) or {}
    if not isinstance(brief, dict):
        parser.error("brief must be an object")
    project_id = str(brief.get("project_id") or "TBD")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "task_id",
                "project_id",
                "stage",
                "gate",
                "workstream",
                "task",
                "input",
                "deliverable",
                "owner_role",
                "dependency",
                "status",
            ]
        )
        count = 0
        for stage, gate, title in STAGES:
            for workstream in WORKSTREAMS:
                count += 1
                previous = "" if gate == "G0" else f"prior gate G{int(gate[1:]) - 1}"
                writer.writerow(
                    [
                        f"TSK-{count:04d}",
                        project_id,
                        stage,
                        gate,
                        workstream,
                        f"{title} / {workstream}",
                        "project brief + approved upstream artifacts",
                        f"{stage}_{workstream}_artifact",
                        "TBD",
                        previous,
                        "PLANNED",
                    ]
                )
    print(f"tasks={count} out={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
