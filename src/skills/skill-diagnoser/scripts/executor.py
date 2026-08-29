import os
import glob
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any

from edd_agent_tools.skills import SkillsState, Skill
from edd_agent_tools.evaluation.models import EvalDetailReport
from edd_agent_tools.gemini import GeminiClient

from .models import (
    DiagnoseSkillFailureOutput,
    ImprovementPlan,
    TargetLayer,
    FailureCategory
)
from .prompter import DiagnosisPrompter


class SkillExecutor:
    """テスト実行結果ログおよびスキルアセットを解析し、改善計画を策定する診断エグゼキューター。"""

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
        self._prompter = DiagnosisPrompter()

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
                    target_layer=TargetLayer.LOGIC,
                    failure_category=FailureCategory.LOGIC_EXCEPTION,
                    root_cause="すべてのテストケースが合格しており、修復すべき問題は検出されませんでした。",
                    recommended_action="追加の改善は不要です。Tier昇格または本番利用が可能です。"
                )
                return DiagnoseSkillFailureOutput(
                    status="success",
                    details="全テストが合格しているため、改善計画の策定をスキップしました。",
                    plan=plan
                )

            # 3. 関連アセット（design.json, SKILL.md, ソースコード）の収集
            design_content = ""
            if os.path.isfile(skill_obj.design_path):
                with open(skill_obj.design_path, "r", encoding="utf-8") as f:
                    design_content = f.read()

            spec_content = ""
            if os.path.isfile(skill_obj.spec_path):
                try:
                    spec_content = skill_obj.load_spec()
                except Exception:
                    pass

            source_files: Dict[str, str] = {}
            if os.path.isdir(skill_obj.source_code_dir):
                for py_file in glob.glob(os.path.join(skill_obj.source_code_dir, "**", "*.py"), recursive=True):
                    rel_path = os.path.relpath(py_file, skill_obj.root_dir).replace("\\", "/")
                    try:
                        with open(py_file, "r", encoding="utf-8") as f:
                            source_files[rel_path] = f.read()
                    except Exception:
                        pass

            # 4. 診断プロンプトの構築
            prompt = self._prompter.build_prompt(
                skill_name=self.skill_name,
                test_type=resolved_test_type,
                report=report,
                design_content=design_content,
                spec_content=spec_content,
                source_files=source_files
            )

            # 5. Gemini API の呼び出し
            # 5. Gemini API の呼び出し
            gemini_client = GeminiClient()
            try:
                from google.genai import types
                config = types.GenerateContentConfig(response_mime_type="application/json")
            except Exception:
                config = None

            response = gemini_client.generate_content(contents=prompt, config=config)
            raw_response = response.text if hasattr(response, "text") else str(response)

            # 6. レスポンスのパースと ImprovementPlan の構築
            plan_data = self._parse_json_safely(raw_response)

            # target_layer に応じたパッチデータのサニタイズ
            target_layer = plan_data.get("target_layer")
            if target_layer == "logic":
                plan_data["design_patch"] = None
                plan_data["test_case_patch"] = None
            elif target_layer == "design":
                plan_data["logic_patch"] = None
                plan_data["test_case_patch"] = None
            elif target_layer == "test_case":
                plan_data["design_patch"] = None
                plan_data["logic_patch"] = None

            improvement_plan = ImprovementPlan.model_validate(plan_data)

            return DiagnoseSkillFailureOutput(
                status="success",
                details=f"診断が完了しました。修正対象レイヤー: {improvement_plan.target_layer.value}, 原因: {improvement_plan.failure_category.value}",
                plan=improvement_plan
            )


        except Exception as e:
            import traceback
            traceback.print_exc()
            return DiagnoseSkillFailureOutput(
                status="failed",
                details=f"診断処理中に予期せぬエラーが発生しました: {e}",
                plan=None
            )

    def _parse_json_safely(self, text: str) -> dict[str, Any]:
        """LLMの返却テキストから JSON を安全にパースします。"""
        cleaned = text.strip()
        
        # ```json ... ``` または ``` ... ``` の除去
        if "```" in cleaned:
            # 最初のコードブロックを抽出
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
            else:
                cleaned = "\n".join([line for line in cleaned.splitlines() if not line.strip().startswith("```")])

        # 最初の { から 最後の } までを抽出
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 改行やエスケープ文字のクレンジング試行
            cleaned_escaped = re.sub(r'[\x00-\x1f\x7f-\x9f]', lambda m: ' ' if m.group(0) in '\n\r\t' else '', cleaned)
            return json.loads(cleaned_escaped)

