#!/usr/bin/env python3
"""
edd-eval CLI - 評価駆動開発（EDD）評価・生成・ゲートキーパー用コマンドラインインターフェース
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from edd_agent_tools.state import SkillsState
from edd_agent_tools.models import SkillTier
from edd_agent_tools.evaluation.test_runner import ContractTestRunner
from edd_agent_tools.evaluation.simulation_runner import SimulationEvalRunner
from edd_agent_tools.evaluation.environment import LocalWorkspaceEnv
from edd_agent_tools.evaluation.generator import generate_evalset


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


def run_tier_gate(
    skill_name: str,
    target_tier: int = 1,
    eval_set_base_path: str = "tests"
) -> Dict[str, Any]:
    """対象スキルの Tier 昇格防壁テストを実行し、合否判定・ステータス更新を行う。"""
    state = SkillsState()
    skill = state.get_skill(skill_name)
    if not skill:
        return {
            "status": "failed",
            "message": f"Skill '{skill_name}' was not found in SkillsState."
        }

    # 1. 依存関係グラフ検証 (DAG Check)
    is_dag_valid, dag_errors = state.validate_dependency_graph()
    if not is_dag_valid:
        return {
            "status": "failed",
            "message": f"Dependency DAG validation failed: {dag_errors}"
        }

    env = LocalWorkspaceEnv()
    base_p = Path(eval_set_base_path)
    skill_tests_dir = Path(skill.root_dir) / "tests"

    def _find_evalset(test_type: str) -> Optional[Path]:
        cand1 = base_p / skill_name / f"{skill_name}_{test_type}.evalset.json"
        cand2 = base_p / f"{skill_name}_{test_type}.evalset.json"
        cand3 = skill_tests_dir / f"{skill_name}_{test_type}.evalset.json"
        for c in [cand1, cand2, cand3]:
            if c.exists():
                return c
        return None

    # Tier 1 判定: 契約テスト(100%) + トリガーテスト(90%)
    if target_tier >= 1:
        contract_f = _find_evalset("contract")
        if contract_f:
            with open(contract_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            c_res = ContractTestRunner().run_tests(skill=skill, test_cases_data=cases, env=env)
            if c_res.failed > 0 or c_res.accuracy < 1.0:
                return {
                    "status": "failed",
                    "message": f"Tier 1 Contract tests failed: {c_res.passed}/{c_res.total} passed."
                }

        trigger_f = _find_evalset("trigger")
        if trigger_f:
            with open(trigger_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            t_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if t_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 1 Trigger test accuracy ({t_res.accuracy:.1%}) is below threshold (90%)."
                }

    # Tier 2 判定: ゴールデンテスト(90%) + ジャッジテスト(85%)
    if target_tier >= 2:
        golden_f = _find_evalset("golden")
        if golden_f:
            with open(golden_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            g_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if g_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 2 Golden test accuracy ({g_res.accuracy:.1%}) is below threshold (90%)."
                }

        judge_f = _find_evalset("judge")
        if judge_f:
            with open(judge_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            j_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if j_res.accuracy < 0.85:
                return {
                    "status": "failed",
                    "message": f"Tier 2 Judge test accuracy ({j_res.accuracy:.1%}) is below threshold (85%)."
                }

    # Tier 3 判定: 推論軌跡テスト + 敵対的テスト(90%)
    if target_tier >= 3:
        adv_f = _find_evalset("adversarial")
        if adv_f:
            with open(adv_f, "r", encoding="utf-8") as f:
                cases = json.load(f)
            a_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if a_res.accuracy < 0.9:
                return {
                    "status": "failed",
                    "message": f"Tier 3 Adversarial test accuracy ({a_res.accuracy:.1%}) is below threshold (90%)."
                }

    # 昇格成功時の登録更新
    tier_map = {1: SkillTier.CORE, 2: SkillTier.EXTENSION, 3: SkillTier.EXTENSION}
    state.register_skill(
        name=skill_name,
        description=skill.description,
        tier=tier_map.get(target_tier, SkillTier.CORE),
        root_dir=skill.root_dir
    )

    return {
        "status": "success",
        "skill_name": skill_name,
        "promoted_tier": target_tier,
        "message": f"Successfully validated and promoted '{skill_name}' to Tier {target_tier}."
    }


def main():
    parser = argparse.ArgumentParser(prog="edd-eval", description="Evaluation-Driven Development Evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available subcommands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run evaluation tests on a skill")
    run_parser.add_argument("skill_name", help="Name of the target skill")
    run_parser.add_argument("--type", choices=["trigger", "contract", "golden", "judge", "trajectory", "adversarial", "all"], default="all", help="Test type to run")
    run_parser.add_argument("--evalset", help="Path to custom evalset.json")
    run_parser.add_argument("--report", default="tests/results/latest_report.json", help="Path for report output")

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate evaluation test cases for a skill")
    gen_parser.add_argument("skill_name", help="Name of the target skill")
    gen_parser.add_argument("--type", choices=["trigger", "contract", "golden", "judge", "trajectory", "adversarial", "all"], default="all", help="Test type to generate")
    gen_parser.add_argument("--output-dir", help="Output directory for generated evalsets")

    # gate command
    gate_parser = subparsers.add_parser("gate", help="Run tier promotion gatekeeper tests")
    gate_parser.add_argument("skill_name", help="Name of the target skill")
    gate_parser.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier to promote to")
    gate_parser.add_argument("--evalset-dir", default="tests", help="Base directory for evalset files")

    args = parser.parse_args()

    if args.command == "run":
        res = run_evaluation(args.skill_name, test_type=args.type, eval_set_path=args.evalset, report_output_path=args.report)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res.get("status") == "success" else 1)

    elif args.command == "generate":
        res = generate_evalset(args.skill_name, test_type=args.type, output_dir=args.output_dir)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res.get("status") == "success" else 1)

    elif args.command == "gate":
        res = run_tier_gate(args.skill_name, target_tier=args.tier, eval_set_base_path=args.evalset_dir)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
