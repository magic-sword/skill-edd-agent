"""
Evaluation Diagnoser for edd-agent-tools

テスト失敗コンテキスト（テスト結果、SKILL.md、関連ソースコード）を構造化して抽出・出力する診断エンジン。
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from edd_agent_tools.state import SkillsState


class SkillDiagnoser:
    """スキルのテスト失敗原因とコンテキストを決定論的に抽出する診断クラス。"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.state = SkillsState(project_root=self.project_root)

    def diagnose(
        self,
        skill_name: str,
        report_path: Optional[str] = None,
        test_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """スキルのテスト結果およびソースコードを収集し、診断レポートを生成します。"""
        skill = self.state.get_skill(skill_name)
        skill_dir = Path(skill.root_dir) if skill else None

        if not skill_dir:
            cand = self.project_root / "src" / "skills" / skill_name
            if cand.exists():
                skill_dir = cand

        report_data = None
        if report_path and os.path.isfile(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
            except Exception as e:
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
            if test_type and t_type != test_type:
                continue
            if isinstance(res, dict) and res.get("failed", 0) > 0:
                failures.append({
                    "test_type": t_type,
                    "failed_count": res.get("failed"),
                    "passed_count": res.get("passed", 0),
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

    def format_markdown(self, diagnosis: Dict[str, Any]) -> str:
        """診断結果をエージェント向け Markdown 形式にフォーマットします。"""
        skill_name = diagnosis["skill_name"]
        summary = diagnosis["summary"]
        failures = diagnosis["failures"]

        lines = [
            f"# 🔍 Failure Diagnosis for Skill: `{skill_name}`",
            "",
            "## 1. Executive Summary",
            f"- **Overall Passed**: {summary.get('total_passed', 0)}",
            f"- **Overall Failed**: {summary.get('total_failed', 0)}",
            f"- **Pass Rate**: {summary.get('overall_accuracy', 1.0):.1%}",
            "",
            "## 2. Failure Details & Error Analysis"
        ]

        if not failures:
            lines.append("✅ All tests passed! No failures detected.")
        else:
            for f in failures:
                lines.append(f"### Test Type: `{f['test_type']}` ({f['failed_count']} failed)")
                for d in f.get("details", []):
                    lines.append(f"- **Detail**: {d}")
                lines.append("")

        lines.append("## 3. Current Specification (SKILL.md)")
        lines.append("```markdown")
        lines.append(diagnosis.get("spec_content", "").strip())
        lines.append("```")
        lines.append("")

        lines.append("## 4. Current Scripts")
        for p, code in diagnosis.get("source_files", {}).items():
            lines.append(f"### `{p}`")
            lines.append("```python")
            lines.append(code.strip())
            lines.append("```")
            lines.append("")

        return "\n".join(lines)
