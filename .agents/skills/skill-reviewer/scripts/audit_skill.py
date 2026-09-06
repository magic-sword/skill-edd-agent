#!/usr/bin/env python3
"""
Skill Audit Tool for skill-reviewer

指定されたスキルディレクトリを走査し、白書『Agent Skills』（May 2026）および
ADK 2.0 に準拠したレビュー用サマリー・チェックリストを生成します。
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def analyze_scripts(scripts_dir: Path) -> List[Dict[str, Any]]:
    findings = []
    if not scripts_dir.exists():
        return findings

    for py_file in scripts_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
        except Exception as e:
            findings.append({"file": py_file.name, "issue": f"Syntax error: {e}", "severity": "ERROR"})
            continue

        # AST 解析: 疑わしいハードコード比較の検出
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    for comp in node.test.comparators:
                        if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                            if len(comp.value) > 30 and "\n" in comp.value:
                                findings.append({
                                    "file": py_file.name,
                                    "line": node.lineno,
                                    "issue": f"Potential test-overfitting detected: Multi-line string literal comparison ({len(comp.value)} chars)",
                                    "severity": "WARNING"
                                })

            # 変数名に pos_ や test_case が含まれているか
            if isinstance(node, ast.Name) and any(node.id.startswith(p) for p in ["pos_", "neg_", "test_case_"]):
                findings.append({
                    "file": py_file.name,
                    "line": node.lineno,
                    "issue": f"Potential test-overfitting detected: Test-specific variable name '{node.id}'",
                    "severity": "WARNING"
                })

    return findings


def analyze_testcases(tests_dir: Path) -> Dict[str, Any]:
    stats = {"positive": 0, "negative": 0, "total": 0, "cases": []}
    if not tests_dir.exists():
        return stats

    for tf in tests_dir.glob("*.test.json"):
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
            for c in data.get("eval_cases", []):
                stats["total"] += 1
                is_neg = c.get("is_negative", False)
                conv = c.get("conversation", [])
                has_tools = False
                if conv and len(conv) > 0 and isinstance(conv[0], dict):
                    inter = conv[0].get("intermediate_data", {})
                    if inter.get("tool_uses"):
                        has_tools = True
                if not is_neg and has_tools:
                    stats["positive"] += 1
                else:
                    stats["negative"] += 1
                stats["cases"].append(c.get("eval_id", "unknown"))
        except Exception:
            pass
    return stats


def generate_report(skill_dir: Path) -> str:
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    scripts_dir = skill_dir / "scripts"
    tests_dir = skill_dir / "tests"

    report = []
    report.append(f"# Skill Audit Report: `{skill_name}`")
    report.append(f"**Path**: `{skill_dir.resolve()}`\n")

    # 1. 構造チェック
    report.append("## 1. Directory Structure")
    report.append(f"- `SKILL.md`: {'✅ Present' if skill_md.exists() else '❌ MISSING'}")
    report.append(f"- `scripts/`: {'✅ Present' if scripts_dir.exists() else '⚠️ None'}")
    report.append(f"- `tests/`: {'✅ Present' if tests_dir.exists() else '⚠️ None'}\n")

    # 2. スクリプト監査（過学習チェック）
    report.append("## 2. Overfitting & Script Logic Audit")
    findings = analyze_scripts(scripts_dir)
    if not findings:
        report.append("✅ No obvious hardcoded test patterns or multi-line comparison leaks found.")
    else:
        report.append("⚠️ **Potential Concerns Detected**:")
        for f in findings:
            line_str = f" (line {f['line']})" if "line" in f else ""
            report.append(f"- `[{f['severity']}]` {f['file']}{line_str}: {f['issue']}")
    report.append("")

    # 3. テストカバレッジ
    report.append("## 3. Evaluation Coverage (EDD Inversion)")
    test_stats = analyze_testcases(tests_dir)
    report.append(f"- Total Test Cases: {test_stats['total']}")
    report.append(f"- Positive Triggers: {test_stats['positive']} (target: >= 3)")
    report.append(f"- Negative Triggers: {test_stats['negative']} (target: >= 3)")
    if test_stats['positive'] >= 3 and test_stats['negative'] >= 3:
        report.append("✅ Satisfies Whitepaper Page 22 requirement (3 positive + 3 negative).")
    else:
        report.append("⚠️ Does NOT satisfy 3+3 rule. Over-triggering or boundary drift may occur.")
    report.append("")

    # 4. レビュールーブリック判定
    report.append("## 4. Review Rubrics Assessment")
    report.append("- [ ] **Anti-Overfitting**: General multi-stage pipeline without test-input hardcoding")
    report.append("- [ ] **Deterministic Tooling**: Logic shifted to `scripts/` with zero-dependency where feasible")
    report.append("- [ ] **Quality Bar**: Verb-led description, When NOT to use, no placeholders")
    report.append("- [ ] **Robustness**: Safe handling of empty/malformed inputs without unhandled crash")
    report.append("")

    report.append("## 5. Next Actions")
    report.append("Please verify the checklist above. If any item is marked FAIL, provide actionable critique.")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Audit an Agent Skill for architectural soundness and overfitting.")
    parser.add_argument("--skill-dir", required=True, help="Path to the skill directory")
    args = parser.parse_args()

    skill_path = Path(args.skill_dir)
    if not skill_path.exists() or not skill_path.is_dir():
        print(f"Error: Skill directory not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    print(generate_report(skill_path))


if __name__ == "__main__":
    main()
