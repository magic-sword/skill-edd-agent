#!/usr/bin/env python3
"""
Test Evaluation Runner & Structured Logger (Zero-Dependency CLI)

スキルのテスト（Contract / Simulation / Trigger 等）を実行し、評価結果レポートを永続化します。
`edd eval` 統合 CLI を透過的に呼び出す軽量ブラックボックススクリプトです。

Usage:
    python run_eval.py <skill_name> [--type <type>] [--report <path>]
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def run_evaluation(
    skill_name: str,
    test_type: str = "all",
    eval_set_path: Optional[str] = None,
    report_output_path: str = "tests/results/latest_report.json"
) -> Dict[str, Any]:
    """指定されたスキルのテストを実行し、評価結果レポートを出力・永続化します。"""
    # 統合 CLI `edd eval` の呼び出し
    cmd = ["edd", "eval", skill_name, "--type", test_type, "--report", report_output_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if Path(report_output_path).exists():
            with open(report_output_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            return {
                "status": "success" if proc.returncode == 0 else "failed",
                "report": report_data,
                "report_path": report_output_path,
                "stdout": proc.stdout
            }
    except FileNotFoundError:
        # edd コマンドが PATH にない場合、python -m edd_agent_tools.cli eval を試行
        cmd_py = [sys.executable, "-m", "edd_agent_tools.cli", "eval", skill_name, "--type", test_type, "--report", report_output_path]
        try:
            proc = subprocess.run(cmd_py, capture_output=True, text=True)
            if Path(report_output_path).exists():
                with open(report_output_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                return {
                    "status": "success" if proc.returncode == 0 else "failed",
                    "report": report_data,
                    "report_path": report_output_path,
                    "stdout": proc.stdout
                }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"Execution error: {e}",
                "report_path": report_output_path
            }

    return {
        "status": "failed",
        "message": f"Failed to execute evaluation for '{skill_name}'.",
        "report_path": report_output_path
    }


def main():
    parser = argparse.ArgumentParser(description="Run evaluation tests for a skill (Zero-Dependency CLI)")
    parser.add_argument("skill_name", help="Name of the skill to test")
    parser.add_argument("--type", choices=["trigger", "contract", "golden", "judge", "trajectory", "adversarial", "all"], default="all", help="Test type to run")
    parser.add_argument("--evalset", help="Path to specific evalset.json file")
    parser.add_argument("--report", default="tests/results/latest_report.json", help="Path to save report JSON")

    args = parser.parse_args()
    res = run_evaluation(args.skill_name, test_type=args.type, eval_set_path=args.evalset, report_output_path=args.report)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
