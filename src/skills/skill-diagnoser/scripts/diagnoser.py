#!/usr/bin/env python3
"""
Skill Failure Diagnoser & Context Extractor (Zero-Dependency)

テスト実行結果ログ（JSON）およびスキルアセット（SKILL.md, scripts/）を決定論的に解析し、
エージェントが自己修復・推論を行うための構造化失敗コンテキスト（Markdown/JSON）を出力します。
外部ライブラリ非依存（標準ライブラリのみ）で動作するため、単体でポータブルに利用可能です。

Usage:
    python diagnoser.py <skill-name> [--report <path>] [--test-type <type>] [--format {json,markdown}]
"""

import os
import sys
import glob
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List


def find_skill_directory(skill_name: str) -> Optional[Path]:
    """スキルディレクトリのパスを標準探索パスから解決します。"""
    # 1. 環境変数からの解決
    env_root = os.environ.get("EDD_SKILL_ROOT")
    if env_root and Path(env_root).exists() and Path(env_root).name == skill_name:
        return Path(env_root)

    # 2. 直接指定または相対パス
    cand_direct = Path(skill_name).resolve()
    if cand_direct.exists() and cand_direct.is_dir() and (cand_direct / "SKILL.md").exists():
        return cand_direct

    cand_skills = Path("src/skills") / skill_name
    if cand_skills.exists() and cand_skills.is_dir():
        return cand_skills.resolve()

    cand_skills_json = Path("skills_state.json")
    if cand_skills_json.exists():
        try:
            with open(cand_skills_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s in data.get("skills", []):
                if s.get("name") == skill_name and "path" in s:
                    p = Path(s["path"]).resolve()
                    if p.exists():
                        return p
        except Exception:
            pass

    return None


def extract_failure_context(
    skill_name: str,
    report_path: Optional[str] = None,
    test_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """テスト失敗コンテキストを決定論的に収集・整理します。"""
    skill_dir = find_skill_directory(skill_name)

    # 1. レポートファイルの解決
    report_data = None
    if report_path and os.path.isfile(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load report at {report_path}: {e}", file=sys.stderr)

    if not report_data and skill_dir:
        cand_report = skill_dir / "tests" / "results" / "latest_report.json"
        if cand_report.exists():
            try:
                with open(cand_report, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
            except Exception:
                pass

    if not report_data:
        report_data = {
            "skill_name": skill_name,
            "results": {},
            "summary": {"total_passed": 0, "total_failed": 0, "overall_accuracy": 1.0}
        }

    # 2. 仕様書（SKILL.md）の取得
    spec_content = ""
    if skill_dir and (skill_dir / "SKILL.md").exists():
        try:
            spec_content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        except Exception:
            pass

    # 3. 関連スクリプト（scripts/*.py）の収集
    source_files: Dict[str, str] = {}
    if skill_dir and (skill_dir / "scripts").exists():
        for py_file in (skill_dir / "scripts").glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            try:
                source_files[f"scripts/{py_file.name}"] = py_file.read_text(encoding="utf-8")
            except Exception:
                pass

    # 4. 失敗詳細のフォーマット
    failed_details = []
    summary = report_data.get("summary", {})
    results = report_data.get("results", {})

    target_layer = "script"
    if test_type == "trigger":
        target_layer = "spec"

    for t_name, t_info in results.items():
        if isinstance(t_info, dict):
            details = t_info.get("details", [])
            for d in details:
                if isinstance(d, dict):
                    failed_details.append(d)
                elif isinstance(d, str):
                    failed_details.append({"message": d, "test_type": t_name})

    total_passed = summary.get("total_passed", 0)
    total_failed = summary.get("total_failed", 0)
    total_cases = total_passed + total_failed
    accuracy = summary.get("overall_accuracy", 1.0)

    return {
        "skill_name": skill_name,
        "test_type": test_type or "all",
        "total_cases": total_cases,
        "passed_cases": total_passed,
        "failed_cases_count": total_failed,
        "accuracy": accuracy,
        "failed_details": failed_details,
        "spec_snippet": spec_content[:1500] if spec_content else None,
        "relevant_source_files": source_files,
        "suggested_target_layer": target_layer
    }


def main():
    parser = argparse.ArgumentParser(description="Skill Failure Diagnoser & Context Extractor (Zero-Dependency)")
    parser.add_argument("skill", type=str, help="対象スキルの論理名またはパス")
    parser.add_argument("--report", "-r", type=str, default=None, help="テストレポート JSON のパス")
    parser.add_argument("--test-type", "-t", type=str, default=None, help="テスト種別 (contract, trigger, all)")
    parser.add_argument("--format", "-f", type=str, choices=["json", "markdown"], default="json", help="出力フォーマット")

    args = parser.parse_args()

    context = extract_failure_context(
        skill_name=args.skill,
        report_path=args.report,
        test_type=args.test_type
    )

    if not context:
        print(f"Error: Could not extract diagnostic context for '{args.skill}'.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(context, indent=2, ensure_ascii=False))
    else:
        print(f"# 🔍 Failure Diagnostic Report: `{context['skill_name']}`")
        print(f"- **Test Type**: {context['test_type']}")
        print(f"- **Accuracy**: {context['accuracy'] * 100:.1f}% ({context['passed_cases']}/{context['total_cases']} passed)")
        print(f"- **Suggested Target Layer**: `{context['suggested_target_layer']}`\n")

        print("## Failed Cases")
        if not context["failed_details"]:
            print("No failed cases detected.")
        else:
            for fd in context["failed_details"]:
                print(f"### Case: {fd.get('case_id', 'unknown')}")
                if "input_params" in fd:
                    print(f"- **Input**: `{fd.get('input_params')}`")
                if "expected_output" in fd:
                    print(f"- **Expected**: `{fd.get('expected_output')}`")
                if "actual_output" in fd:
                    print(f"- **Actual**: `{fd.get('actual_output')}`")
                if "error_message" in fd:
                    print(f"- **Error**: {fd.get('error_message')}")
                if "message" in fd:
                    print(f"- **Message**: {fd.get('message')}")

        print("\n## Available Source Files")
        for fn in context["relevant_source_files"].keys():
            print(f"- `{fn}`")


if __name__ == "__main__":
    main()
