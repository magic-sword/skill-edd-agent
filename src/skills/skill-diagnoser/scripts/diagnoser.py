#!/usr/bin/env python3
"""
テスト実行結果ログおよびスキルアセットを解析し、根本原因と改善計画（ImprovementPlan）を策定する診断スクリプト。
Anthropic 標準および Progressive Disclosure 規約に準拠したフラットな実装。
"""

import os
import sys
import glob
import json
import re
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from enum import StrEnum
from pydantic import BaseModel, Field

from edd_agent_tools.skills import SkillsState, Skill
from edd_agent_tools.evaluation.models import EvalDetailReport
from edd_agent_tools.gemini import client, GeminiRequest


class TargetLayer(StrEnum):
    """修正を適用すべきシステムの階層・レイヤー。"""
    SPEC = "spec"              # SKILL.md の修正（トリガー説明文、意思決定ツリー、手順）
    SCRIPT = "script"          # scripts/*.py の実装ロジック修正
    REFERENCE = "reference"    # references/*.md のドキュメント修正
    ASSET = "asset"            # assets/ のテンプレート修正
    TEST_CASE = "test_case"    # tests/*.evalset.json の不備・期待値修正


class FailureCategory(StrEnum):
    """テスト失敗の原因分類。"""
    TRIGGER_MISMATCH = "trigger_mismatch"            # トリガー説明とテストクエリの不一致
    SCHEMA_VALIDATION_ERROR = "schema_validation"    # 入出力型・必須チェック違反
    LOGIC_EXCEPTION = "logic_exception"              # ゼロ除算、KeyError、IndexError等の実行時例外
    MOCK_UNHANDLED = "mock_unhandled"                # GeminiClient等の外部モック未設定
    MISSING_IMPLEMENTATION = "missing_implementation"# 関数や変数の未定義
    TEST_EXPECTATION_BUG = "test_expectation_bug"    # テスト期待値側の誤り


class SpecPatch(BaseModel):
    """SKILL.md に対する修正データモデル。"""
    model_config = {"extra": "ignore"}
    description_patch: str | None = Field(
        None, description="更新後のスキル説明文（トリガー精度向上用）"
    )
    decision_tree_patch: list[dict[str, str]] | None = Field(
        None, description="更新後の意思決定ツリー項目（condition, action）"
    )
    instructions_patch: list[str] | None = Field(
        None, description="更新後の手順指示"
    )


class ScriptPatchInstruction(BaseModel):
    """scripts/*.py に対するコード修正指示モデル。"""
    model_config = {"extra": "ignore"}
    target_file: str = Field(
        ..., description="修正対象ファイルの相対パス（例: scripts/run.py, scripts/converter.py）"
    )
    problematic_code_snippet: str | None = Field(
        None, description="問題のある既存コード箇所"
    )
    fix_instructions: str = Field(
        "", description="どのようにコードを修正すべきかの具体的指示"
    )
    suggested_code: str | None = Field(
        None, description="推奨される修正後コードスニペット"
    )


class TestCasePatch(BaseModel):
    """テストケース定義（evalset.json）に対する修正指示モデル。"""
    model_config = {"extra": "ignore"}
    evalset_path: str | None = Field(None, description="修正対象の evalset.json パス")
    case_id: str | None = Field(None, description="修正対象のテストケースID")
    suggested_fix: str | None = Field(None, description="テストケースの修正指示")


class ImprovementPlan(BaseModel):
    """診断結果および構造化された改善計画モデル。"""
    model_config = {"extra": "ignore"}
    skill_name: str = Field(..., description="診断対象スキルの論理名")
    test_type: str = Field(..., description="失敗したテスト種別（例: contract, trigger）")
    verdict: Literal["needs_improvement", "no_issues_found", "unrecoverable"] = Field(
        "needs_improvement", description="診断判定結果 ('needs_improvement', 'no_issues_found', 'unrecoverable')"
    )
    target_layer: TargetLayer = Field(..., description="修正対象レイヤー")
    failure_category: FailureCategory = Field(..., description="失敗の原因カテゴリ")
    root_cause: str = Field(..., description="根本原因の分析詳細サマリー")
    recommended_action: str = Field(..., description="後続フェーズで実行すべき推奨アクション")
    spec_patch: SpecPatch | None = Field(
        None, description="仕様層（SKILL.md）修正時の差分データ"
    )
    script_patch: ScriptPatchInstruction | None = Field(
        None, description="ロジック層（scripts/*.py）修正時の指示データ"
    )
    test_case_patch: TestCasePatch | None = Field(
        None, description="テストケース層修正時の指示データ"
    )


class DiagnoseSkillFailureOutput(BaseModel):
    """diagnose_skill_failure 関数の返却出力モデル。"""
    status: Literal["success", "failed"] = Field(..., description="診断処理の実行ステータス")
    details: str = Field(..., description="診断結果サマリーまたはエラーメッセージ")
    plan: ImprovementPlan | None = Field(None, description="策定された改善計画オブジェクト")


class SkillDiagnoser:
    """テスト実行結果ログおよびスキルアセットを解析し、改善計画を策定する診断エンジン。"""

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
        self._client = client

    def execute(self) -> DiagnoseSkillFailureOutput:
        """診断処理を実行し、構造化された改善計画（ImprovementPlan）を返却します。"""
        try:
            # 1. SkillsState から対象スキルを取得
            skill_obj = self._skills_state.get_skill(self.skill_name)
            if not skill_obj:
                return DiagnoseSkillFailureOutput(
                    status="failed",
                    details=f"エラー: スキル '{self.skill_name}' が見つかりません。",
                    plan=None
                )

            # 2. テスト結果レポートの取得
            report: Optional[EvalDetailReport] = None
            if self.report_path and os.path.isfile(self.report_path):
                with open(self.report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report = EvalDetailReport.model_validate(data)
            else:
                if self.test_type:
                    report = skill_obj.tests.load_report(self.test_type)
                if not report:
                    report = skill_obj.tests.load_latest_report()

            if not report:
                return DiagnoseSkillFailureOutput(
                    status="failed",
                    details=f"エラー: スキル '{self.skill_name}' のテスト結果レポートが見つかりません。",
                    plan=None
                )

            resolved_test_type = self.test_type or report.test_type

            # 失敗ケースが存在しない場合（全テスト合格）
            if not report.failed_cases and report.accuracy >= 1.0:
                plan = ImprovementPlan(
                    skill_name=self.skill_name,
                    test_type=resolved_test_type,
                    verdict="no_issues_found",
                    target_layer=TargetLayer.SCRIPT,
                    failure_category=FailureCategory.LOGIC_EXCEPTION,
                    root_cause="すべてのテストケースが合格しており、修復すべき問題は検出されませんでした。",
                    recommended_action="追加の改善は不要です。Tier昇格または本番利用が可能です。"
                )
                return DiagnoseSkillFailureOutput(
                    status="success",
                    details="全テストが合格しているため、改善計画の策定をスキップしました。",
                    plan=plan
                )

            # 3. 関連アセット（SKILL.md, scripts/）の収集
            spec_content = ""
            if os.path.isfile(skill_obj.spec_path):
                try:
                    spec_content = skill_obj.load_spec()
                except Exception:
                    pass

            source_files: Dict[str, str] = {}
            if os.path.isdir(skill_obj.scripts_dir):
                for py_file in glob.glob(os.path.join(skill_obj.scripts_dir, "**", "*.py"), recursive=True):
                    rel_path = os.path.relpath(py_file, skill_obj.root_dir).replace("\\", "/")
                    try:
                        with open(py_file, "r", encoding="utf-8") as f:
                            source_files[rel_path] = f.read()
                    except Exception:
                        pass

            # 4. LLM用診断プロンプトの構築
            prompt = self._build_prompt(
                skill_name=self.skill_name,
                test_type=resolved_test_type,
                report=report,
                spec_content=spec_content,
                source_files=source_files
            )

            # 5. Gemini API による診断実行
            req = GeminiRequest(
                prompt=prompt,
                client=self._client
            )
            response = req.execute()

            # 6. レスポンスのパースと構造化モデル化
            raw_text = response.text if hasattr(response, "text") else str(response)
            parsed_json = self._extract_json(raw_text)

            if not parsed_json:
                return DiagnoseSkillFailureOutput(
                    status="failed",
                    details=f"LLMからのJSON応答抽出に失敗しました: {raw_text[:200]}...",
                    plan=None
                )

            plan = ImprovementPlan.model_validate(parsed_json)

            return DiagnoseSkillFailureOutput(
                status="success",
                details=f"スキル '{self.skill_name}' の改善計画が正常に策定されました（レイヤー: {plan.target_layer.value}）。",
                plan=plan
            )

        except Exception as e:
            return DiagnoseSkillFailureOutput(
                status="failed",
                details=f"診断処理中に予期せぬ例外が発生しました: {str(e)}",
                plan=None
            )

    def _build_prompt(
        self,
        skill_name: str,
        test_type: str,
        report: EvalDetailReport,
        spec_content: str,
        source_files: Dict[str, str]
    ) -> str:
        """診断プロンプトを構築します。"""
        failed_cases_formatted = []
        for fc in report.failed_cases:
            fc_dict = {
                "case_id": fc.case_id,
                "input_params": fc.input_params,
                "expected_output": fc.expected_output,
                "actual_output": fc.actual_output,
                "error_type": fc.error_type,
                "error_message": fc.error_message,
                "traceback": fc.traceback
            }
            failed_cases_formatted.append(fc_dict)

        failed_cases_json = json.dumps(failed_cases_formatted, indent=2, ensure_ascii=False)

        source_code_blocks = []
        for rel_path, content in source_files.items():
            source_code_blocks.append(f"### File: {rel_path}\n```python\n{content}\n```")
        source_code_str = "\n\n".join(source_code_blocks)

        prompt = f"""あなたは自己改善型AIエージェントの「根本原因診断および改善計画策定エンジン（Diagnostic Engine）」です。
提供されたテスト失敗レポート、仕様書（SKILL.md）、実装ソースコードを多角的に分析し、テストを確実に合格させるための構造化された改善計画（ImprovementPlan）を策定してください。

---

## 1. 診断対象情報
* **スキル名**: `{skill_name}`
* **実行テスト種別**: `{test_type}`
* **テスト結果サマリー**: 全 {report.total} 件中 {report.passed} 件合格 / {report.failed} 件不合格（合格精度: {report.accuracy:.2%}）
* **サマリー詳細**: {report.details}

---

## 2. 不合格となったテストケース一覧 (Failed Cases)
```json
{failed_cases_json}
```

---

## 3. スキルの仕様書 (SKILL.md)
```markdown
{spec_content}
```

---

## 4. スキルの実装ソースコード (scripts/ 配下)
{source_code_str}

---

## 5. 診断および改善計画の策定ルール (厳守事項)
1. **仕様層（SKILL.md）の修正**:
   * トリガー説明（description）、意思決定ツリー、または手順指示の不備が原因である場合は、`target_layer: "spec"` を選択し、`spec_patch` を提供してください。
2. **ロジック層（scripts/）の修正**:
   * `scripts/*.py` の実装ミス（ゼロ除算、KeyError、型変換漏れ、未ハンドルの条件分岐など）が原因である場合は、`target_layer: "script"` を選択し、修正対象ファイル名と修正指示（`script_patch`）を提供してください。
3. **テスト期待値側の誤り**:
   * スキルの実装や仕様が正しく、テストケース側の期待値指定ミスや不合理なアサーションが原因である場合は、`target_layer: "test_case"` を選択してください。

---

## 6. 出力フォーマット
必ず以下の JSON 構造（ImprovementPlan スキーマ）のみを出力してください。Markdown のコードブロック ```json ... ``` で囲んで出力してください。

```json
{{
  "skill_name": "{skill_name}",
  "test_type": "{test_type}",
  "verdict": "needs_improvement",
  "target_layer": "script",
  "failure_category": "logic_exception",
  "root_cause": "根本原因の詳細な分析サマリー",
  "recommended_action": "推奨される具体的アクション",
  "spec_patch": null,
  "script_patch": {{
    "target_file": "scripts/{skill_name.replace('-', '_')}.py",
    "problematic_code_snippet": "問題のあるコード",
    "fix_instructions": "具体的な修正指示",
    "suggested_code": "修正後コードスニペット"
  }},
  "test_case_patch": null
}}
```
"""
        return prompt

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """LLM応答テキストから JSON 辞書を抽出します。"""
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text.strip())
        except Exception:
            return None


def diagnose_skill_failure(
    skill: str,
    report_path: Optional[str] = None,
    test_type: Optional[str] = None
) -> DiagnoseSkillFailureOutput:
    """テスト実行結果レポートとスキルの設計・コードを分析し、失敗の根本原因と構造化改善計画を出力します。"""
    diagnoser = SkillDiagnoser(
        skill=skill,
        report_path=report_path,
        test_type=test_type
    )
    return diagnoser.execute()


def main():
    parser = argparse.ArgumentParser(description="Diagnose test failures of a skill and generate an ImprovementPlan.")
    parser.add_argument("skill", type=str, nargs="?", default="", help="Logical name of the target skill (e.g. pdf-tools)")
    parser.add_argument("--report", "-r", type=str, default=None, help="Path to test report JSON (default: latest_report.json)")
    parser.add_argument("--test-type", "-t", type=str, default=None, help="Test type (contract, trigger, golden, etc.)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save output ImprovementPlan JSON")
    args = parser.parse_args()

    if not args.skill:
        parser.print_help()
        sys.exit(1)

    res = diagnose_skill_failure(
        skill=args.skill,
        report_path=args.report,
        test_type=args.test_type
    )

    out_json = res.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(out_json, encoding="utf-8")
        print(f"✅ Saved diagnosis result to: {args.output}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()
