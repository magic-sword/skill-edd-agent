#!/usr/bin/env python3
"""
Skill Diagnoser CLI Wrapper (Thin Convention-Based Client)

テスト失敗コンテキストの決定論的解析と出力を edd 統合 CLI / 診断エンジンに委譲します。
外部ライブラリ非依存の CLI 実行と Python 呼び出しの両方に対応します。

Usage:
    python diagnoser.py <skill-name> [--report <path>] [--format {markdown,json}]
"""

import sys
import subprocess
from typing import Dict, Any, Optional


def extract_failure_context(skill_name: str, report_path: Optional[str] = None) -> Dict[str, Any]:
    """テスト失敗コンテキストを抽出します（edd_agent_tools.evaluation.SkillDiagnoser に委譲）。"""
    try:
        from edd_agent_tools.evaluation.diagnoser import SkillDiagnoser
        diagnoser = SkillDiagnoser()
        return diagnoser.diagnose(skill_name, report_path=report_path)
    except Exception as e:
        return {
            "skill_name": skill_name,
            "error": str(e),
            "failures": [],
            "summary": {"total_passed": 0, "total_failed": 0}
        }


def format_markdown(diagnosis: Dict[str, Any]) -> str:
    """診断結果を Markdown にフォーマットします。"""
    try:
        from edd_agent_tools.evaluation.diagnoser import SkillDiagnoser
        diagnoser = SkillDiagnoser()
        return diagnoser.format_markdown(diagnosis)
    except Exception:
        return f"# Diagnostic Report for {diagnosis.get('skill_name', 'Unknown')}\n\nNo details available."


def get_edd_cmd() -> list[str]:
    """edd コマンドの実行形式を解決します。"""
    try:
        res = subprocess.run(["edd", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            return ["edd"]
    except Exception:
        pass
    return [sys.executable, "-m", "edd_agent_tools.cli"]


def main():
    base_cmd = get_edd_cmd()
    cmd = base_cmd + ["diagnose"] + sys.argv[1:]
    res = subprocess.run(cmd)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
