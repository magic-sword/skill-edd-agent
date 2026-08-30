#!/usr/bin/env python3
"""
テスト評価実行＆構造化ログ永続化スクリプト (CLI & API 対応)
隔離サンドボックス環境 (LocalWorkspaceEnv) 上でテストを実行し、テスト結果・精度・失敗詳細をレポートに記録する。
Google ADK 準拠の全6大評価タイプ（Trigger, Contract, Golden, Judge, Trajectory, Adversarial）に対応。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from edd_agent_tools.skills import SkillsState
from edd_agent_tools.evaluation import ContractTestRunner, SimulationEvalRunner, LocalWorkspaceEnv


def run_evaluation(
    skill_name: str,
    test_type: str = "all",
    eval_set_path: Optional[str] = None,
    report_output_path: str = "tests/results/latest_report.json"
) -> Dict[str, Any]:
    """指定されたスキルのテストを実行し、評価結果レポートを出力・永続化する。"""
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        return {"status": "failed", "message": f"Skill '{skill_name}' not found."}

    env = LocalWorkspaceEnv()
    report = {
        "skill_name": skill_name,
        "results": {},
        "summary": {
            "total_passed": 0,
            "total_failed": 0,
            "overall_accuracy": 1.0
        }
    }

    tests_dir = Path(skill.root_dir) / "tests"
    types_to_run = ["trigger", "contract", "golden", "judge", "trajectory", "adversarial"] if test_type == "all" else [test_type]

    for t in types_to_run:
        target_file = None
        if eval_set_path and Path(eval_set_path).exists():
            target_file = Path(eval_set_path)
        else:
            cand = tests_dir / f"{skill_name}_{t}.evalset.json"
            if cand.exists():
                target_file = cand

        if not target_file:
            continue

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                cases_data = json.load(f)

            if t == "contract":
                c_runner = ContractTestRunner()
                res = c_runner.run_tests(skill=skill, test_cases_data=cases_data, env=env)
                report["results"]["contract"] = {
                    "passed": res.passed,
                    "failed": res.failed,
                    "total": res.total,
                    "accuracy": res.accuracy,
                    "details": [d if isinstance(d, dict) else str(d) for d in res.details]
                }
                report["summary"]["total_passed"] += res.passed
                report["summary"]["total_failed"] += res.failed
            else:
                sim_runner = SimulationEvalRunner()
                res = sim_runner.run_tests(skill=skill, eval_set_data=cases_data, env=env)
                report["results"][t] = {
                    "passed": res.passed,
                    "failed": res.failed,
                    "accuracy": res.accuracy,
                    "details": []
                }
                report["summary"]["total_passed"] += report["results"][t]["passed"]
                report["summary"]["total_failed"] += report["results"][t]["failed"]
        except Exception as e:
            report["results"][t] = {
                "error": str(e),
                "accuracy": 0.0
            }
            report["summary"]["total_failed"] += 1

    total_tests = report["summary"]["total_passed"] + report["summary"]["total_failed"]
    if total_tests > 0:
        report["summary"]["overall_accuracy"] = report["summary"]["total_passed"] / total_tests

    # レポートファイルの永続化
    out_p = Path(report_output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return {
        "status": "success" if report["summary"]["total_failed"] == 0 else "failed",
        "report": report,
        "report_path": str(out_p)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation tests for a skill")
    parser.add_argument("skill_name", help="Name of the skill to test")
    parser.add_argument("--type", choices=["trigger", "contract", "golden", "judge", "trajectory", "adversarial", "all"], default="all", help="Test type to run")
    parser.add_argument("--evalset", help="Path to specific evalset.json file")
    parser.add_argument("--report", default="tests/results/latest_report.json", help="Path to save report JSON")

    args = parser.parse_args()
    res = run_evaluation(args.skill_name, test_type=args.type, eval_set_path=args.evalset, report_output_path=args.report)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["status"] == "success" else 1)
