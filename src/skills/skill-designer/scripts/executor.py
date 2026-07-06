import os
import json
from google.adk.tools import ToolContext
from .models import Input, Output
from .client import GeminiDesignClient
from .prompter import DesignPrompter
from .resolver import PathResolver
from .parser import ConstraintParser
from .cleanser import DesignCleanser

class SkillExecutor:
    """
    自然言語の要件や既存のソースコードから ADK 2.0 互換の design.json を設計して出力する
    オブジェクト指向エグゼキューター。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context

    def execute(self) -> Output:
        prompt = self.params.prompt
        summary_override = self.params.summary
        output_dir = self.params.output_dir
        skill = self.params.skill
        source_code_dir = self.params.source_code_dir

        # 1. パス解決
        path_resolver = PathResolver()
        resolved_paths = path_resolver.resolve_paths(skill_name=skill, output_dir=output_dir, source_code_dir=source_code_dir)
        
        existing_name = resolved_paths["existing_name"]
        # ここで output_dir を更新する。元のparams.output_dirではなく解決されたパスを使用
        output_dir = resolved_paths["output_dir"]
        scan_target = resolved_paths["scan_target"]
        skill_directory = resolved_paths["skill_directory"]

        # 2. 既存の制約事項を抽出
        constraint_parser = ConstraintParser()
        existing_constraints_str = constraint_parser.get_existing_constraints(existing_name)

        # 3. Gemini API クライアントの初期化
        gemini_client = GeminiDesignClient()

        # 4. プロンプトコンテンツ (GeminiRequest) の構築
        from edd_agent_tools.skills import SkillsState
        state = SkillsState()
        designer_skill = state.get_skill("skill-designer")
        design_prompter = DesignPrompter(designer_skill=designer_skill)
        request = design_prompter.build_request(
            client=gemini_client._client,
            prompt=prompt,
            existing_name=existing_name,
            existing_constraints=existing_constraints_str,
            scan_target=scan_target,
            output_dir=output_dir
        )

        # 既存の design.json があれば LLM に対し参考コンテキストとして添付提供する
        assets_output_dir = os.path.join(output_dir, "assets")
        output_file_path = os.path.join(assets_output_dir, "design.json")
        if os.path.exists(output_file_path):
            request.add_file(output_file_path, ref_root=output_dir)

        try:
            response_text = gemini_client.generate_design(contents=request)
        except Exception as e:
            return Output(status="failed", message=f"Gemini API 呼び出しエラー: {e}", output_dir="")

        # 5. レスポンスのパースとdesign.json の保存
        try:
            design_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            return Output(status="failed", message=f"Gemini API レスポンスのパースエラー: {e}", output_dir="")

        # 5.2. 決定論的クレンジング（自動補正）
        design_data = DesignCleanser().clean(design_data)

        # 概要 (summary) フィールドの処理
        # ユーザーから明示的な summary が指定されている場合は、それを最優先で上書き
        if summary_override:
            design_data["summary"] = summary_override

        # 5.5. Pydantic モデルによるスキーマバリデーション (スキルとワークフローの切り分けチェック)
        from edd_agent_tools.models import ModuleDesign
        from pydantic import TypeAdapter
        try:
            TypeAdapter(ModuleDesign).validate_python(design_data)
        except Exception as e:
            return Output(
                status="failed", 
                message=f"設計データのバリデーションエラー（スキルとワークフローの構成不整合など）: {e}", 
                output_dir=""
            )

        assets_output_dir = os.path.join(output_dir, "assets")
        output_file_path = os.path.join(assets_output_dir, "design.json")
        
        try:
            if not os.path.exists(assets_output_dir):
                os.makedirs(assets_output_dir)

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(design_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return Output(status="failed", message=f"design.json の保存エラー: {e}", output_dir="")

        message = f"design.json が '{output_file_path}' に正常に生成されました。"
        return Output(status="success", message=message, output_dir=output_dir)