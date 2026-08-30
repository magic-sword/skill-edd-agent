#!/usr/bin/env python3
"""
Unified CLI for edd-agent-tools (edd)

Anthropic Agent Skills & Google ADK 2.0 準拠の統合 CLI ツール。
動的ディスパッチ（Dynamic Dispatch）によるスキルの実行、初期化、静的検証、
パッケージング、評価実行、Tier 昇格判定、および失敗診断を提供します。
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

from edd_agent_tools.models import SkillLogicDraft, SkillPattern, SkillTier, EvalDetailReport
from edd_agent_tools.state import SkillsState
from edd_agent_tools.validation.validator import SkillValidator
from edd_agent_tools.packaging.scaffold import SkillScaffolder
from edd_agent_tools.packaging.packager import SkillPackager
from edd_agent_tools.evaluation.test_runner import ContractTestRunner
from edd_agent_tools.evaluation.simulation_runner import SimulationEvalRunner
from edd_agent_tools.evaluation.cascade_runner import CascadeTestRunner
from edd_agent_tools.evaluation.environment import LocalWorkspaceEnv
from edd_agent_tools.evaluation.diagnoser import SkillDiagnoser
from edd_agent_tools.evaluation.optimizer import SkillOptimizer


def resolve_skill_script(skill_dir: Path, script_name: Optional[str] = None) -> Optional[Path]:
    """スキルディレクトリ内の実行対象スクリプトを動的に解決します。"""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists() or not scripts_dir.is_dir():
        return None

    if script_name:
        cand = scripts_dir / script_name
        if cand.exists() and cand.is_file():
            return cand
        cand_py = scripts_dir / f"{script_name}.py"
        if cand_py.exists() and cand_py.is_file():
            return cand_py
        return None

    skill_name = skill_dir.name
    candidates = [
        scripts_dir / f"{skill_name.replace('-', '_')}.py",
        scripts_dir / f"{skill_name}.py",
        scripts_dir / "main.py",
        scripts_dir / "run.py",
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return cand

    py_files = [f for f in scripts_dir.glob("*.py") if f.name != "__init__.py"]
    if len(py_files) == 1:
        return py_files[0]

    return None


def cmd_run(args: argparse.Namespace, extra_args: List[str]) -> int:
    """スキル内のスクリプトを動的解決して実行します。"""
    state = SkillsState()
    skill_name = args.skill_name
    skill_obj = state.get_skill(skill_name)

    if skill_obj and os.path.exists(skill_obj.root_dir):
        skill_dir = Path(skill_obj.root_dir)
    else:
        direct_path = Path(skill_name).resolve()
        if direct_path.exists() and direct_path.is_dir():
            skill_dir = direct_path
        else:
            candidates = [
                Path("src/skills") / skill_name,
                Path("skills") / skill_name,
                Path(".agents/skills") / skill_name,
                Path(skill_name)
            ]
            found = False
            for cand in candidates:
                if cand.exists() and cand.is_dir():
                    skill_dir = cand.resolve()
                    found = True
                    break
            if not found:
                print(f"❌ Error: Skill '{skill_name}' was not found in SkillsState or filesystem.", file=sys.stderr)
                return 1

    script_path = None
    remaining_args = list(extra_args)

    # extra_args の先頭が明示的なスクリプト指定（例: custom.py）であるか確認
    if remaining_args and not remaining_args[0].startswith("-"):
        cand = resolve_skill_script(skill_dir, remaining_args[0])
        if cand:
            script_path = cand
            remaining_args = remaining_args[1:]

    if not script_path:
        script_path = resolve_skill_script(skill_dir)

    if not script_path or not script_path.exists():
        scripts = [f.name for f in (skill_dir / "scripts").glob("*.py") if f.name != "__init__.py"] if (skill_dir / "scripts").exists() else []
        print(f"❌ Error: Could not resolve execution script in '{skill_dir}/scripts'.", file=sys.stderr)
        if scripts:
            print(f"Available scripts: {', '.join(scripts)}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script_path)] + remaining_args
    env = os.environ.copy()
    env["EDD_SKILL_NAME"] = skill_dir.name
    env["EDD_SKILL_ROOT"] = str(skill_dir)

    try:
        proc = subprocess.run(cmd, env=env)
        return proc.returncode
    except Exception as e:
        print(f"❌ Error executing script: {e}", file=sys.stderr)
        return 1


def cmd_init(args: argparse.Namespace) -> int:
    """新規スキル雛形を生成します。"""
    try:
        res = SkillScaffolder.scaffold(
            skill_name=args.skill_name,
            output_base_dir=args.path,
            pattern=args.pattern
        )
        print(f"✅ Successfully initialized skill '{args.skill_name}' at: {res}")
        return 0
    except Exception as e:
        print(f"❌ Error initializing skill: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """スキルディレクトリの静的検証（Linter）を実行します。"""
    target = Path(args.path).resolve()
    if not target.exists():
        print(f"❌ Error: Target path does not exist: {target}", file=sys.stderr)
        return 1

    res = SkillValidator.validate_directory(target)
    print(f"\n🔍 Validating Skill: {res.skill_name} ({target})\n" + "=" * 60)
    if res.errors:
        print("\n❌ Errors:")
        for err in res.errors:
            print(f"  • {err}")
    if res.warnings:
        print("\n⚠️ Warnings:")
        for warn in res.warnings:
            print(f"  • {warn}")

    if res.is_valid:
        print("\n✅ Skill is completely valid according to Anthropic & Google ADK 2.0 standards!")
        return 0
    else:
        print(f"\n❌ Validation failed with {len(res.errors)} error(s).")
        return 1


def cmd_package(args: argparse.Namespace) -> int:
    """スキルを検証後に配布用 zip にパッケージ化します。"""
    try:
        zip_p = SkillPackager.package(skill_dir=args.path, output_dir=args.out, validate=True)
        print(f"✅ Successfully created skill package: {zip_p}")
        return 0
    except Exception as e:
        print(f"❌ Error packaging skill: {e}", file=sys.stderr)
        return 1


def cmd_eval(args: argparse.Namespace) -> int:
    """スキルの契約テストおよびシミュレーション評価を実行します。"""
    state = SkillsState()
    skill = state.get_skill(args.skill_name)
    if not skill:
        print(f"❌ Error: Skill '{args.skill_name}' not found.", file=sys.stderr)
        return 1

    env = LocalWorkspaceEnv()
    report = {
        "skill_name": args.skill_name,
        "results": {},
        "summary": {"total_passed": 0, "total_failed": 0, "overall_accuracy": 1.0}
    }

    tests_dir = Path(skill.root_dir) / "tests"
    types_to_run = ["trigger", "contract", "golden", "judge", "trajectory", "adversarial"] if args.type == "all" else [args.type]

    for t in types_to_run:
        cand = tests_dir / f"{args.skill_name}_{t}.evalset.json"
        if not cand.exists():
            continue

        try:
            with open(cand, "r", encoding="utf-8") as f:
                cases_data = json.load(f)

            if t == "contract":
                c_runner = ContractTestRunner()
                res = c_runner.run_tests(skill=skill, test_cases_data=cases_data, env=env)
                report["results"]["contract"] = {
                    "passed": res.passed,
                    "failed": res.failed,
                    "total": res.total,
                    "accuracy": res.accuracy,
                    "detail_file_path": res.detail_file_path
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
                report["summary"]["total_passed"] += res.passed
                report["summary"]["total_failed"] += res.failed
        except Exception as e:
            report["results"][t] = {"error": str(e), "accuracy": 0.0}
            report["summary"]["total_failed"] += 1

    total_tests = report["summary"]["total_passed"] + report["summary"]["total_failed"]
    if total_tests > 0:
        report["summary"]["overall_accuracy"] = report["summary"]["total_passed"] / total_tests

    out_p = Path(args.report) if args.report else tests_dir / "results" / "latest_report.json"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Evaluation Results for '{args.skill_name}':")
    print(f"  • Total Passed: {report['summary']['total_passed']}")
    print(f"  • Total Failed: {report['summary']['total_failed']}")
    print(f"  • Overall Accuracy: {report['summary']['overall_accuracy']:.1%}")
    print(f"  • Report saved to: {out_p}")

    return 0 if report["summary"]["total_failed"] == 0 else 1


def cmd_tier_gate(args: argparse.Namespace) -> int:
    """Tier 昇格防壁テストを実行し、合否判定・ステータス更新を行います。"""
    state = SkillsState()
    skill = state.get_skill(args.skill_name)
    if not skill:
        print(f"❌ Error: Skill '{args.skill_name}' not found.", file=sys.stderr)
        return 1

    is_dag_valid, dag_errors = state.validate_dependency_graph()
    if not is_dag_valid:
        print(f"❌ Dependency DAG validation failed: {dag_errors}", file=sys.stderr)
        return 1

    env = LocalWorkspaceEnv()
    skill_tests_dir = Path(skill.root_dir) / "tests"

    def _find_evalset(test_type: str) -> Optional[Path]:
        cand = skill_tests_dir / f"{args.skill_name}_{test_type}.evalset.json"
        return cand if cand.exists() else None

    # Tier 1 判定: 契約テスト(100%) + トリガーテスト(90%)
    if args.tier >= 1:
        cf = _find_evalset("contract")
        if cf:
            with open(cf, "r", encoding="utf-8") as f:
                cases = json.load(f)
            c_res = ContractTestRunner().run_tests(skill=skill, test_cases_data=cases, env=env)
            if c_res.failed > 0 or c_res.accuracy < 1.0:
                print(f"❌ Tier 1 Contract tests failed: {c_res.passed}/{c_res.total} passed.", file=sys.stderr)
                return 1

        tf = _find_evalset("trigger")
        if tf:
            with open(tf, "r", encoding="utf-8") as f:
                cases = json.load(f)
            t_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if t_res.accuracy < 0.9:
                print(f"❌ Tier 1 Trigger test accuracy ({t_res.accuracy:.1%}) < 90%.", file=sys.stderr)
                return 1

    # Tier 2 判定: ゴールデン(90%) + ジャッジ(85%)
    if args.tier >= 2:
        gf = _find_evalset("golden")
        if gf:
            with open(gf, "r", encoding="utf-8") as f:
                cases = json.load(f)
            g_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
            if g_res.accuracy < 0.9:
                print(f"❌ Tier 2 Golden test accuracy ({g_res.accuracy:.1%}) < 90%.", file=sys.stderr)
                return 1

    # 昇格成功
    state.register_skill(skill_name=args.skill_name, tier=SkillTier(args.tier))
    print(f"🎉 Success: Skill '{args.skill_name}' successfully promoted to Tier {args.tier} ({SkillTier(args.tier).name})!")
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    """テスト結果レポートから失敗コンテキストを抽出し、Markdown/JSON で出力します。"""
    diagnoser = SkillDiagnoser()
    diagnosis = diagnoser.diagnose(
        skill_name=args.skill_name,
        report_path=args.report
    )

    if args.format == "json":
        print(json.dumps(diagnosis, ensure_ascii=False, indent=2))
    else:
        print(diagnoser.format_markdown(diagnosis))

    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    """静的検証、評価テスト、連鎖回帰テスト、Tier 昇格を一括実行します。"""
    optimizer = SkillOptimizer()
    res = optimizer.optimize_skill(
        skill_name=args.skill_name,
        target_tier=args.tier,
        run_cascade=not args.no_cascade
    )
    if res.get("status") == "promoted":
        print(f"🎉 Success: {res.get('message')}")
        return 0
    else:
        print(f"❌ Optimization / Promotion failed: {res.get('status')}", file=sys.stderr)
        print(f"Message: {res.get('message')}", file=sys.stderr)
        if "details" in res:
            print(json.dumps(res["details"], ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """利用可能なスキル一覧を表示します。"""
    state = SkillsState()
    skills = state.list_skills()
    print(f"\n📦 Available Agent Skills ({len(skills)} found):\n" + "=" * 60)
    for s in skills:
        if s.tier:
            val = s.tier.value if hasattr(s.tier, "value") else s.tier
            name = s.tier.name if hasattr(s.tier, "name") else f"Tier {s.tier}"
            tier_str = f"Tier {val} ({name})"
        else:
            tier_str = "Unranked"
        print(f"• \033[1m{s.name}\033[0m [{tier_str}]")
        print(f"  {s.description}")
        print(f"  Path: {s.root_dir}\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # 既知のトップレベルコマンド
    known_commands = {
        "run", "init", "validate", "package", "eval", "tier-gate", "diagnose", "optimize", "list",
        "-h", "--help", "-v", "--version"
    }

    # 動的ディスパッチ: 最初の引数が既知のサブコマンドでなく、スキル名に一致する場合は `run <skill_name>` に自動転送
    if argv and argv[0] not in known_commands and not argv[0].startswith("-"):
        candidate_skill = argv[0]
        state = SkillsState()
        if state.get_skill(candidate_skill) or (Path("src/skills") / candidate_skill).exists() or Path(candidate_skill).exists():
            argv = ["run", candidate_skill] + argv[1:]

    parser = argparse.ArgumentParser(
        prog="edd",
        description="EDD Agent Tools - Evaluation-Driven Development CLI for Agent Skills (Anthropic & Google ADK 2.0 Compliant)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. run
    p_run = subparsers.add_parser("run", help="Run a skill script with dynamic discovery and sandbox execution")
    p_run.add_argument("skill_name", help="Name or path of the target skill")

    # 2. init
    p_init = subparsers.add_parser("init", help="Initialize a new skill scaffold")
    p_init.add_argument("skill_name", help="Name of the skill in hyphen-case")
    p_init.add_argument("--path", "-p", default="src/skills", help="Target parent directory (default: src/skills)")
    p_init.add_argument("--pattern", choices=["workflow", "tool_wrapper", "reference_heavy", "template_generator"], default="workflow", help="Skill pattern template")

    # 3. validate
    p_val = subparsers.add_parser("validate", help="Statically validate SKILL.md and directory structure (Linter / AST)")
    p_val.add_argument("path", help="Path to the skill directory")

    # 4. package
    p_pkg = subparsers.add_parser("package", help="Validate and package a skill into a distributable zip archive")
    p_pkg.add_argument("path", help="Path to the skill directory")
    p_pkg.add_argument("--out", "-o", default="./dist", help="Output directory for zip file (default: ./dist)")

    # 5. eval
    p_eval = subparsers.add_parser("eval", help="Run contract and simulation evaluation tests on a skill")
    p_eval.add_argument("skill_name", help="Target skill name")
    p_eval.add_argument("--type", "-t", choices=["all", "contract", "trigger", "golden", "judge", "trajectory", "adversarial"], default="all", help="Evaluation test type")
    p_eval.add_argument("--report", "-r", help="Custom output report path")

    # 6. tier-gate
    p_tier = subparsers.add_parser("tier-gate", help="Run multi-layer test gates for Tier promotion (Tier 1~3)")
    p_tier.add_argument("skill_name", help="Target skill name")
    p_tier.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier to promote to (1: Production, 2: Verified, 3: Mastered)")

    # 7. diagnose
    p_diag = subparsers.add_parser("diagnose", help="Extract structured failure context from evaluation reports")
    p_diag.add_argument("skill_name", help="Target skill name")
    p_diag.add_argument("--report", "-r", help="Path to custom test report JSON")
    p_diag.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="Output format")

    # 8. optimize
    p_opt = subparsers.add_parser("optimize", help="Verify, evaluate, run cascade tests, and promote a skill")
    p_opt.add_argument("skill_name", help="Target skill name")
    p_opt.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier (default: 1)")
    p_opt.add_argument("--no-cascade", action="store_true", help="Skip cascade regression tests on dependents")

    # 9. list
    subparsers.add_parser("list", help="List all registered agent skills")

    # パース実行（run 用に未知の引数も許容）
    args, extra = parser.parse_known_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "run":
        return cmd_run(args, extra)
    elif args.command == "init":
        return cmd_init(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "package":
        return cmd_package(args)
    elif args.command == "eval":
        return cmd_eval(args)
    elif args.command == "tier-gate":
        return cmd_tier_gate(args)
    elif args.command == "diagnose":
        return cmd_diagnose(args)
    elif args.command == "optimize":
        return cmd_optimize(args)
    elif args.command == "list":
        return cmd_list(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
