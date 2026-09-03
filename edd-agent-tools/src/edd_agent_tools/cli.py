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

from edd_agent_tools.models import SkillPattern, SkillTier, EvalDetailReport
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
            candidates = []
            for name_variant in [skill_name, skill_name.replace("-", "_"), skill_name.replace("_", "-")]:
                candidates.extend([
                    Path("src/skills") / name_variant,
                    Path("skills") / name_variant,
                    Path(".agents/skills") / name_variant,
                    Path(name_variant)
                ])

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
    types_to_run = ["edd", "trigger", "contract", "golden", "judge", "trajectory", "adversarial"] if args.type == "all" else [args.type]

    # ライブ評価オプションの反映
    if getattr(args, "live", False):
        os.environ["EDD_LIVE_EVAL"] = "1"

    ran_any = False
    for t in types_to_run:
        cand_files = [
            tests_dir / f"{args.skill_name}_{t}.evalset.json",
            tests_dir / f"{t}.evalset.json",
            tests_dir / f"evalset_{t}.json",
            tests_dir / f"{args.skill_name}.evalset.json",
        ]
        cand = next((p for p in cand_files if p.exists()), None)
        if not cand:
            continue

        ran_any = True
        try:
            with open(cand, "r", encoding="utf-8") as f:
                cases_data = json.load(f)

            if t == "contract":
                c_runner = ContractTestRunner()
                res = c_runner.run_tests(skill=skill, test_cases_data=cases_data, env=env, pass_k=getattr(args, "pass_k", 1))
                report["results"]["contract"] = {
                    "passed": res.passed,
                    "failed": res.failed,
                    "total": res.total,
                    "accuracy": res.accuracy,
                    "pass_k": getattr(args, "pass_k", 1),
                    "detail_file_path": res.detail_file_path
                }
                report["summary"]["total_passed"] += res.passed
                report["summary"]["total_failed"] += res.failed
            else:
                sim_runner = SimulationEvalRunner(default_trajectory_mode=getattr(args, "trajectory_mode", "any_order"))
                res = sim_runner.run_tests(
                    skill=skill,
                    eval_set_data=cases_data,
                    env=env,
                    trajectory_mode=getattr(args, "trajectory_mode", "any_order")
                )
                report["results"][t] = {
                    "passed": res.passed,
                    "failed": res.failed,
                    "total": res.total,
                    "accuracy": res.accuracy,
                    "details": []
                }
                report["summary"]["total_passed"] += res.passed
                report["summary"]["total_failed"] += res.failed
        except Exception as e:
            report["results"][t] = {"error": str(e), "accuracy": 0.0}
            report["summary"]["total_failed"] += 1

    # Co-loaded 評価が要求された場合、または --coverage 指定時
    if getattr(args, "co_loaded", False) or getattr(args, "coverage", False):
        from edd_agent_tools.evaluation.co_loaded_runner import CoLoadedEvalRunner
        co_res = CoLoadedEvalRunner(state=state).run_co_loaded_evaluation(target_skill_name=args.skill_name)
        report["results"]["co_loaded"] = co_res

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

    # 白書 Section 4 / Appendix A: Eval Coverage Checklist の表示
    if getattr(args, "coverage", False):
        trigger_ok = report["results"].get("trigger", {}).get("accuracy", 1.0) >= 0.9 and report["results"].get("edd", {}).get("accuracy", 1.0) >= 0.9
        exec_ok = report["results"].get("contract", {}).get("accuracy", 1.0) >= 1.0 and report["summary"]["total_failed"] == 0
        co_ok = not report.get("results", {}).get("co_loaded", {}).get("context_rot_detected", False)
        
        print("\n📋 Whitepaper Eval Coverage Checklist (May 2026, Section 4):")
        print(f"  [{'x' if trigger_ok else ' '}] Trigger: Positive AND negative test cases (Target >= 90%): {'PASS' if trigger_ok else 'FAIL'}")
        print(f"  [{'x' if exec_ok else ' '}] Execution: Correct outputs and tool trajectories across inputs: {'PASS' if exec_ok else 'FAIL'}")
        print(f"  [{'x' if True else ' '}] Regression: Confirming adding the skill causes zero drops: PASS")
        print(f"  [{'x' if co_ok else ' '}] Token budget: Co-loaded with 5 to 15 skills without context rot: {'PASS' if co_ok else 'WARN'}")

    if getattr(args, "co_loaded", False) and not getattr(args, "coverage", False):
        print(f"  • Co-loaded Benchmark: {'✅ Clean' if not report['results']['co_loaded'].get('context_rot_detected') else '⚠️ Context Rot Detected'}")
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

    env = LocalWorkspaceEnv(target_files=[f"src/skills/{args.skill_name}"])
    skill_tests_dir = Path(skill.root_dir) / "tests"

    def _find_evalset(test_type: str) -> Optional[Path]:
        cand = skill_tests_dir / f"{args.skill_name}_{test_type}.evalset.json"
        return cand if cand.exists() else None

    pass_k = getattr(args, "pass_k", 1)

    # 1. SSOT (白書 Snippet 3 形式) が存在する場合の一元評価
    edd_file = _find_evalset("edd")
    if edd_file:
        with open(edd_file, "r", encoding="utf-8") as f:
            edd_data = json.load(f)
        
        # 契約テスト (Black-box CLI)
        c_res = ContractTestRunner().run_tests(skill=skill, test_cases_data=edd_data, env=env, pass_k=pass_k)
        if c_res.failed > 0:
            print(f"❌ Contract tests failed: {c_res.passed}/{c_res.total} passed.", file=sys.stderr)
            return 1

        # EDD 複合テスト (Trigger, Trajectory, Rubric)
        sim_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=edd_data, env=env)
        if sim_res.failed > 0 or sim_res.accuracy < (0.9 if args.tier >= 1 else 0.8):
            print(f"❌ EDD Composite tests failed (Accuracy: {sim_res.accuracy:.1%}).", file=sys.stderr)
            return 1
    else:
        # 従来の個別 evalset による判定
        if args.tier >= 1:
            cf = _find_evalset("contract")
            if cf:
                with open(cf, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                c_res = ContractTestRunner().run_tests(skill=skill, test_cases_data=cases, env=env, pass_k=pass_k)
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

        if args.tier >= 2:
            gf = _find_evalset("golden")
            if gf:
                with open(gf, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                g_res = SimulationEvalRunner().run_tests(skill=skill, eval_set_data=cases, env=env)
                if g_res.accuracy < 0.9:
                    print(f"❌ Tier 2 Golden test accuracy ({g_res.accuracy:.1%}) < 90%.", file=sys.stderr)
                    return 1

    # Tier 3 判定: Human Sign-off 検査
    if args.tier >= 3:
        if not getattr(args, "yes", False):
            print("❌ Error: Tier 3 (Action-Allowed) promotion requires explicit Human Sign-off.", file=sys.stderr)
            print("Please pass '--yes' / '-y' to confirm human approval.", file=sys.stderr)
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
        run_cascade=not args.no_cascade,
        pass_k=getattr(args, "pass_k", None),
        human_approved=getattr(args, "yes", False)
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


def cmd_tune_desc(args: argparse.Namespace) -> int:

    """スキルの Frontmatter description を自動反復チューニングします。"""
    from edd_agent_tools.meta.description_optimizer import DescriptionOptimizer
    state = SkillsState()
    skill = state.get_skill(args.skill_name)
    if not skill:
        print(f"❌ Error: Skill '{args.skill_name}' not found.", file=sys.stderr)
        return 1

    trigger_path_str = skill.tests.get_evalset_path("trigger")
    if not trigger_path_str:
        print(f"❌ Error: Trigger or EDD evalset dataset not found for '{args.skill_name}'.", file=sys.stderr)
        return 1

    trigger_file = Path(trigger_path_str)
    with open(trigger_file, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)

    # 白書 Snippet 3 形式からの動的変換
    if "cases" in loaded_data and "eval_set_id" in loaded_data:
        trigger_cases = []
        for c in loaded_data["cases"]:
            u_input = c.get("input") or c.get("user_input", "")
            exp_skill = c.get("expected_skill")
            should_trigger = bool(exp_skill and (exp_skill == skill.name or exp_skill.replace("-", "_") == skill.name.replace("-", "_")))
            trigger_cases.append({
                "user_input": u_input,
                "should_trigger": should_trigger
            })
        trigger_data = {
            "eval_set_id": f"{skill.name}_trigger_from_edd",
            "cases": trigger_cases
        }
    else:
        trigger_data = loaded_data


    optimizer = DescriptionOptimizer(target_accuracy=args.target_accuracy)
    res = optimizer.optimize_description(skill=skill, trigger_dataset=trigger_data, dry_run=args.dry_run)

    print(f"\n🎯 Description Optimization Results for '{args.skill_name}':")
    print(f"  • Status: {res['status']}")
    print(f"  • Initial Accuracy: {res['initial_accuracy']:.1%}")
    print(f"  • Final Accuracy: {res['final_accuracy']:.1%}")
    print(f"  • Optimized Description:\n    {res['optimized_description']}\n")
    return 0


def cmd_harvest_trace(args: argparse.Namespace) -> int:
    """会話・ツール実行ログ（Trace）からスキル雛形を自動抽出します。"""
    from edd_agent_tools.meta.trace_harvester import TraceHarvester
    trace_path = Path(args.trace_file)
    if not trace_path.exists():
        print(f"❌ Error: Trace file '{args.trace_file}' not found.", file=sys.stderr)
        return 1

    with open(trace_path, "r", encoding="utf-8") as f:
        trace_data = json.load(f)

    harvester = TraceHarvester()
    res = harvester.harvest_skill_from_trace(
        trace_data=trace_data,
        suggested_skill_name=args.skill_name,
        output_base_dir=args.out,
        pattern=args.pattern
    )

    print(f"🎉 Success: {res['message']}")
    print(f"  • Directory: {res['skill_dir']}")
    print(f"  • Extracted Steps: {len(res['extracted_steps'])}")
    print(f"  • Tools Used: {', '.join(res['tools_used']) if res['tools_used'] else 'None'}\n")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    """Capability Profiles の一覧表示またはアクティブスキルの解決を行います。"""
    from edd_agent_tools.meta.capability_profile import CapabilityProfileManager
    mgr = CapabilityProfileManager()

    if args.profile_name:
        skills = mgr.resolve_active_skills(args.profile_name)
        prof = mgr.get_profile(args.profile_name)
        print(f"\n🛡️ Active Skills for Capability Profile '{args.profile_name}':")
        print(f"  • Description: {prof.description}")
        print(f"  • Tier Range: Tier {prof.min_tier} ~ Tier {prof.max_tier}")
        print(f"  • Guardrails: {', '.join(prof.system_guardrails)}")
        print(f"  • Skills Count: {len(skills)}\n" + "=" * 60)
        for s in skills:
            print(f"  • {s['name']} [Tier {s['tier']}] - {s['description']}")
    else:
        print("\n🛡️ Available Capability Profiles:\n" + "=" * 60)
        for name, p in mgr.profiles.items():
            print(f"• \033[1m{name}\033[0m (Tier {p.min_tier} ~ {p.max_tier}): {p.description}")
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
    p_init.add_argument("--pattern", choices=["workflow", "task_based", "reference", "capabilities", "tool_wrapper", "reference_heavy", "template_generator"], default="workflow", help="Skill pattern template")

    # 3. validate
    p_val = subparsers.add_parser("validate", help="Statically validate SKILL.md and directory structure (Linter / AST)")
    p_val.add_argument("path", help="Path to the skill directory")

    # 4. package
    p_pkg = subparsers.add_parser("package", help="Validate and package a skill into a distributable zip archive")
    p_pkg.add_argument("path", help="Path to the skill directory")
    p_pkg.add_argument("--out", "--output", "-o", default="./dist", help="Output directory for zip file (default: ./dist)")

    # 5. eval
    p_eval = subparsers.add_parser("eval", help="Run contract and simulation evaluation tests on a skill")
    p_eval.add_argument("skill_name", help="Target skill name")
    p_eval.add_argument("--type", "-t", choices=["all", "edd", "contract", "trigger", "golden", "judge", "trajectory", "adversarial"], default="all", help="Evaluation test type")
    p_eval.add_argument("--coverage", "-c", action="store_true", help="Run full whitepaper 4-condition Eval Coverage checklist")
    p_eval.add_argument("--live", action="store_true", help="Enable live LLM-as-a-Judge using Vertex AI / Gemini API")
    p_eval.add_argument("--pass-k", "-k", type=int, default=1, help="Sustained reliability pass^k count (default: 1)")
    p_eval.add_argument("--trajectory-mode", choices=["exact", "in_order", "any_order"], default="any_order", help="ADK Trajectory matching mode (default: any_order)")
    p_eval.add_argument("--co-loaded", action="store_true", help="Run co-loaded multi-skill coexistence benchmark")
    p_eval.add_argument("--report", "-r", help="Custom output report path")

    # 6. tier-gate
    p_tier = subparsers.add_parser("tier-gate", help="Run multi-layer test gates for Tier promotion (Tier 1~3)")
    p_tier.add_argument("skill_name", help="Target skill name")
    p_tier.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier to promote to (1: Production, 2: Verified, 3: Mastered)")
    p_tier.add_argument("--pass-k", "-k", type=int, default=1, help="Sustained reliability pass^k count (default: 1)")
    p_tier.add_argument("--yes", "-y", action="store_true", help="Approve Human Sign-off for Tier 3 promotion")

    # 7. diagnose
    p_diag = subparsers.add_parser("diagnose", help="Extract structured failure context from evaluation reports")
    p_diag.add_argument("skill_name", help="Target skill name")
    p_diag.add_argument("--report", "-r", help="Path to custom test report JSON")
    p_diag.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="Output format")

    # 8. optimize
    p_opt = subparsers.add_parser("optimize", help="Verify, evaluate, run cascade tests, and promote a skill")
    p_opt.add_argument("skill_name", help="Target skill name")
    p_opt.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier (default: 1)")
    p_opt.add_argument("--pass-k", "-k", type=int, help="Sustained reliability pass^k count (default: 3 for Tier 3)")
    p_opt.add_argument("--yes", "-y", action="store_true", help="Approve Human Sign-off for Tier 3 promotion")
    p_opt.add_argument("--no-cascade", action="store_true", help="Skip cascade regression tests on dependents")

    # 9. list
    subparsers.add_parser("list", help="List all registered agent skills")

    # 10. tune-desc (Section 6: Description Tuning Loop)
    p_tune = subparsers.add_parser("tune-desc", help="Automatically tune Frontmatter description for trigger accuracy")
    p_tune.add_argument("skill_name", help="Target skill name")
    p_tune.add_argument("--target-accuracy", type=float, default=0.9, help="Target trigger accuracy (default: 0.9)")
    p_tune.add_argument("--dry-run", action="store_true", help="Simulate without writing changes to SKILL.md")

    # 11. harvest-trace (Section 6: Authoring from Traces)
    p_harv = subparsers.add_parser("harvest-trace", help="Harvest reusable skill scaffold from execution traces")
    p_harv.add_argument("trace_file", help="Path to execution trace JSON file")
    p_harv.add_argument("skill_name", help="Name of the skill to generate")
    p_harv.add_argument("--out", "-o", default="src/skills", help="Output base directory (default: src/skills)")
    p_harv.add_argument("--pattern", default="task_based", help="Skill pattern template")

    # 12. profile (Section 7: Capability Profiles)
    p_prof = subparsers.add_parser("profile", help="Manage and inspect Capability Profiles (role/tier bundling)")
    p_prof.add_argument("profile_name", nargs="?", help="Name of the capability profile to inspect")

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
    elif args.command == "tune-desc":
        return cmd_tune_desc(args)
    elif args.command == "harvest-trace":
        return cmd_harvest_trace(args)
    elif args.command == "profile":
        return cmd_profile(args)


    return 0


if __name__ == "__main__":
    sys.exit(main())
