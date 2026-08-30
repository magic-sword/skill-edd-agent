#!/usr/bin/env python3
"""
Skill Diagnoser - テスト失敗コンテキスト抽出 CLI (Zero-Dependency)

テスト実行結果ログ（JSON）およびスキルアセット（SKILL.md, scripts/）を決定論的に解析し、
エージェントが自己修復・推論を行うための構造化失敗コンテキスト（Markdown/JSON）を出力します。
外部ライブラリ非依存（標準ライブラリのみ）で動作します。

Usage:
    python diagnoser.py <skill-name> [--report <path>] [--format {markdown,json}]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List


def find_skill_directory(skill_name: str) -> Optional[Path]:
    """スキルディレクトリのパスを標準探索パスから解決します。"""
    env_root = os.environ.get("EDD_SKILL_ROOT")
    if env_root and Path(env_root).exists() and Path(env_root).name == skill_name:
        return Path(env_root)

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
    report_path: Optional[str] = None
) -> Dict[str, Any]:
    """テスト失敗コンテキストを収集・整理します。"""
    skill_dir = find_skill_directory(skill_name)

    report_data = None
    if report_path and os.path.isfile(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
        except Exception:
            pass

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

    spec_content = ""
    if skill_dir and (skill_dir / "SKILL.md").exists():
        try:
            spec_content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        except Exception:
            pass

    source_files: Dict[str, str] = {}
    if skill_dir and (skill_dir / "scripts").exists():
        for py_file in (skill_dir / "scripts").glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            try:
                source_files[f"scripts/{py_file.name}"] = py_file.read_text(encoding="utf-8")
            except Exception:
                pass

    failures = []
    for t_type, res in report_data.get("results", {}).items():
        if isinstance(res, dict):
            if res.get("failed", 0) > 0 or "error" in res:
                failures.append({
                    "test_type": t_type,
                    "failed_count": res.get("failed", 1 if "error" in res else 0),
                    "passed_count": res.get("passed", 0),
                    "error": res.get("error"),
                    "details": res.get("details", [])
                })

    return {
        "skill_name": skill_name,
        "skill_dir": str(skill_dir) if skill_dir else None,
        "summary": report_data.get("summary", {}),
        "failures": failures,
        "spec_content": spec_content,
        "source_files": source_files
    }


def format_markdown(ctx: Dict[str, Any]) -> str:
    """診断結果を Markdown 形式にフォーマットします。"""
    lines = [
        f"# 🔍 Failure Diagnosis for Skill: `{ctx.get('skill_name')}`\n",
        "## 1. Executive Summary",
        f"- **Overall Passed**: {ctx.get('summary', {}).get('total_passed', 0)}",
        f"- **Overall Failed**: {ctx.get('summary', {}).get('total_failed', 0)}",
        f"- **Pass Rate**: {ctx.get('summary', {}).get('overall_accuracy', 0.0):.1%}\n",
        "## 2. Failure Details & Error Analysis"
    ]

    failures = ctx.get("failures", [])
    if not failures:
        lines.append("✅ All tests passed! No failures detected.")
    else:
        for f in failures:
            lines.append(f"### ❌ Test Type: `{f.get('test_type')}`")
            if f.get("error"):
                lines.append(f"**Error**: ```\n{f.get('error')}\n```")
            lines.append(f"- Passed: {f.get('passed_count')}, Failed: {f.get('failed_count')}")
            for d in f.get("details", []):
                lines.append(f"- **Case ID**: `{d.get('eval_case_id')}`")
                if "error" in d:
                    lines.append(f"  - Error: `{d.get('error')}`")
                if "reason" in d:
                    lines.append(f"  - Reason: {d.get('reason')}")
            lines.append("")

    lines.append("## 3. Current Specification (SKILL.md)")
    lines.append(f"```markdown\n{ctx.get('spec_content', 'None')}\n```\n")

    lines.append("## 4. Current Scripts")
    for fname, code in ctx.get("source_files", {}).items():
        lines.append(f"### `{fname}`")
        lines.append(f"```python\n{code}\n```\n")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill Failure Diagnoser & Context Extractor")
    parser.add_argument("skill_name", help="Target skill name")
    parser.add_argument("--report", "-r", help="Path to test report JSON")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="Output format")
    args = parser.parse_args()

    ctx = extract_failure_context(args.skill_name, report_path=args.report)
    if args.format == "json":
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
