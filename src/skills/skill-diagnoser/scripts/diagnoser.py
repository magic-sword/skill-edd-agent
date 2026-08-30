#!/usr/bin/env python3
"""
Skill Failure Diagnoser & Context Extractor
テスト実行結果ログおよびスキルアセット（SKILL.md, scripts/）を決定論的に解析し、
エージェントが推論・修正方針を立案するための構造化コンテキスト（Failure Context）を出力します。
Anthropic / Google ADK 規約に準拠（Zero LLM dependency in scripts）。

Usage:
    diagnoser.py <skill-name> [--report <path>] [--test-type <type>] [--format {json,markdown}]
"""

import os
import sys
import glob
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import StrEnum
from pydantic import BaseModel, Field

from edd_agent_tools.skills import SkillsState, Skill
from edd_agent_tools.evaluation.models import EvalDetailReport, FailedCaseDetail


class TargetLayer(StrEnum):
    """修正を適用すべきシステムの階層・レイヤー。"""
    SPEC = "spec"              # SKILL.md の修正（トリガー説明文、意思決定ツリー、手順）
    SCRIPT = "script"          # scripts/*.py の実装ロジック修正
    REFERENCE = "reference"    # references/*.md のドキュメント修正
    ASSET = "asset"            # assets/ のテンプレート修正
    TEST_CASE = "test_case"    # tests/*.evalset.json の不備・期待値修正


class ExtractedFailureContext(BaseModel):
    """エージェント向け構造化失敗コンテキストモデル。"""
    skill_name: str
    test_type: str
    total_cases: int
    passed_cases: int
    failed_cases_count: int
    accuracy: float
    failed_details: List[Dict[str, Any]]
    spec_snippet: Optional[str] = None
    relevant_source_files: Dict[str, str] = Field(default_factory=dict)
    suggested_target_layer: TargetLayer


class SkillDiagnoser:
    """テスト実行結果とスキルリソースを決定論的に解析・抽出する診断エンジン。"""

    def __init__(
        self,
        skill: str,
        report_path: Optional[str] = None,
        test_type: Optional[str] = None
    ):
        self.skill_name = skill
        self.report_path = report_path
        self.test_type = test_type
        self._skills_state = SkillsState()

    def extract_context(self) -> Optional[ExtractedFailureContext]:
        """テスト失敗コンテキストを決定論的に収集・整理します。"""
        skill_obj = self._skills_state.get_skill(self.skill_name)
        if not skill_obj:
            return None

        # 1. テスト結果レポートの取得
        report: Optional[EvalDetailReport] = None
        if self.report_path and os.path.isfile(self.report_path):
            try:
                with open(self.report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report = EvalDetailReport.model_validate(data)
            except Exception:
                pass
        else:
            if self.test_type:
                report = skill_obj.tests.load_report(self.test_type)
            if not report:
                report = skill_obj.tests.load_latest_report()

        if not report:
            # レポートが存在しない場合のフォールバック空レポート
            report = EvalDetailReport(
                skill_name=self.skill_name,
                test_type=self.test_type or "all",
                passed=0,
                failed=0,
                total=0,
                accuracy=1.0,
                failed_cases=[]
            )

        resolved_test_type = self.test_type or report.test_type

        # 2. 仕様書（SKILL.md）の取得
        spec_content = ""
        if os.path.isfile(skill_obj.spec_path):
            try:
                spec_content = skill_obj.load_spec()
            except Exception:
                pass

        # 3. 関連スクリプト（scripts/*.py）の収集
        source_files: Dict[str, str] = {}
        if os.path.isdir(skill_obj.scripts_dir):
            for py_file in glob.glob(os.path.join(skill_obj.scripts_dir, "**", "*.py"), recursive=True):
                rel_path = os.path.relpath(py_file, skill_obj.root_dir).replace("\\", "/")
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        source_files[rel_path] = f.read()
                except Exception:
                    pass

        # 4. 失敗詳細のフォーマットとレイヤー推定（ルールベース）
        failed_details = []
        target_layer = TargetLayer.SCRIPT
        if resolved_test_type == "trigger":
            target_layer = TargetLayer.SPEC

        for fc in report.failed_cases:
            failed_details.append({
                "case_id": fc.case_id,
                "input_params": fc.input_params,
                "expected_output": fc.expected_output,
                "actual_output": fc.actual_output,
                "error_message": fc.error_message,
                "stack_trace": fc.stack_trace
            })

        return ExtractedFailureContext(
            skill_name=self.skill_name,
            test_type=resolved_test_type,
            total_cases=report.total,
            passed_cases=report.passed,
            failed_cases_count=len(report.failed_cases),
            accuracy=report.accuracy,
            failed_details=failed_details,
            spec_snippet=spec_content[:1500] if spec_content else None,
            relevant_source_files=source_files,
            suggested_target_layer=target_layer
        )


def main():
    parser = argparse.ArgumentParser(description="Skill Failure Diagnoser & Context Extractor (Deterministic, Zero-LLM)")
    parser.add_argument("skill", type=str, help="対象スキルの論理名")
    parser.add_argument("--report", "-r", type=str, default=None, help="テストレポート JSON のパス")
    parser.add_argument("--test-type", "-t", type=str, default=None, help="テスト種別 (contract, trigger, all)")
    parser.add_argument("--format", "-f", type=str, choices=["json", "markdown"], default="json", help="出力フォーマット")

    args = parser.parse_args()

    diagnoser = SkillDiagnoser(
        skill=args.skill,
        report_path=args.report,
        test_type=args.test_type
    )
    context = diagnoser.extract_context()

    if not context:
        print(f"Error: Skill '{args.skill}' not found or context could not be extracted.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(context.model_dump(), indent=2, ensure_ascii=False))
    else:
        print(f"# Failure Diagnostic Report: {context.skill_name}")
        print(f"- **Test Type**: {context.test_type}")
        print(f"- **Accuracy**: {context.accuracy * 100:.1f}% ({context.passed_cases}/{context.total_cases} passed)")
        print(f"- **Suggested Target Layer**: `{context.suggested_target_layer.value}`\n")
        print("## Failed Cases")
        if not context.failed_details:
            print("No failed cases detected.")
        else:
            for fd in context.failed_details:
                print(f"### Case: {fd.get('case_id')}")
                print(f"- **Input**: `{fd.get('input_params')}`")
                print(f"- **Expected**: `{fd.get('expected_output')}`")
                print(f"- **Actual**: `{fd.get('actual_output')}`")
                if fd.get("error_message"):
                    print(f"- **Error**: {fd.get('error_message')}")
        print("\n## Available Source Files")
        for fn in context.relevant_source_files.keys():
            print(f"- `{fn}`")


if __name__ == "__main__":
    main()
