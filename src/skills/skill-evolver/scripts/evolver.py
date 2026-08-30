#!/usr/bin/env python3
"""
Skill Evolver & Self-Healing Orchestrator CLI (Zero-Dependency)

Agent Skills の静的検証、評価実行、失敗診断、連鎖回帰テスト、および Tier 昇格を統合オーケストレーションします。
統合 CLI `edd` と連携し、エージェントが自己改善ループを回すためのインターフェースを提供します。

Usage:
    python evolver.py eval <skill-name> [--type {all,contract,trigger,golden}]
    python evolver.py diagnose <skill-name> [--report <path>]
    python evolver.py optimize <skill-name> [--tier {1,2,3}] [--no-cascade]
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """コマンドを実行し、終了コード・stdout・stderr を返します。"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return -1, "", str(e)


def get_edd_base_cmd() -> List[str]:
    """edd コマンドの実行形式を解決します。"""
    code, _, _ = run_cmd(["edd", "--version"])
    if code == 0:
        return ["edd"]
    return [sys.executable, "-m", "edd_agent_tools.cli"]


def cmd_eval(args: argparse.Namespace) -> int:
    """評価テストを実行します。"""
    base = get_edd_base_cmd()
    cmd = base + ["eval", args.skill_name, "--type", args.type]
    if args.report:
        cmd.extend(["--report", args.report] )
    
    code, stdout, stderr = run_cmd(cmd)
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def cmd_diagnose(args: argparse.Namespace) -> int:
    """テスト失敗コンテキストを抽出して表示します。"""
    script_dir = Path(__file__).parent
    diag_script = script_dir / "diagnoser.py"
    
    cmd = [sys.executable, str(diag_script), args.skill_name, "--format", args.format]
    if args.report:
        cmd.extend(["--report", args.report])
    
    code, stdout, stderr = run_cmd(cmd)
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def cmd_optimize(args: argparse.Namespace) -> int:
    """静的検証、評価テスト、連鎖回帰テスト、Tier 昇格を実行します。"""
    base = get_edd_base_cmd()
    cmd = base + ["optimize", args.skill_name, "--tier", str(args.tier)]
    if args.no_cascade:
        cmd.append("--no-cascade")
    
    code, stdout, stderr = run_cmd(cmd)
    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="evolver.py",
        description="Skill Evolver & Self-Healing Orchestration CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # eval
    p_eval = subparsers.add_parser("eval", help="Run contract and simulation evaluation tests")
    p_eval.add_argument("skill_name", help="Target skill name")
    p_eval.add_argument("--type", "-t", choices=["all", "contract", "trigger", "golden", "judge", "trajectory", "adversarial"], default="all", help="Evaluation test type")
    p_eval.add_argument("--report", "-r", help="Path to custom report output")

    # diagnose
    p_diag = subparsers.add_parser("diagnose", help="Extract failure context and diagnosis")
    p_diag.add_argument("skill_name", help="Target skill name")
    p_diag.add_argument("--report", "-r", help="Path to custom test report JSON")
    p_diag.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="Output format")

    # optimize
    p_opt = subparsers.add_parser("optimize", help="Verify, evaluate, run cascade regression, and promote Tier")
    p_opt.add_argument("skill_name", help="Target skill name")
    p_opt.add_argument("--tier", type=int, choices=[1, 2, 3], default=1, help="Target Tier (default: 1)")
    p_opt.add_argument("--no-cascade", action="store_true", help="Skip cascade regression tests")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "eval":
        return cmd_eval(args)
    elif args.command == "diagnose":
        return cmd_diagnose(args)
    elif args.command == "optimize":
        return cmd_optimize(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
