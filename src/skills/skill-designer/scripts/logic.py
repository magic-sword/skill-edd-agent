import os
import json
from google.adk.tools import ToolContext
from .models import Input, Output
from .client import GeminiDesignClient
from .prompter import DesignPrompter
from .resolver import PathResolver
from .parser import ConstraintParser

def process_message(params: Input, tool_context: ToolContext) -> Output:
    """
    skill-designer のメインビジネスロジック。
    自然言語の要件や既存のソースコードから ADK 2.0 互換 of design.json を設計して出力します。
    """
    requirement = params.requirement
    output_dir = params.output_dir
    skill = params.skill
    source_code_dir = params.source_code_dir

    # 1. パス解決
    path_resolver = PathResolver()
    resolved_paths = path_resolver.resolve_paths(skill_name=skill, output_dir=output_dir, source_code_dir=source_code_dir)
    
    existing_name = resolved_paths["existing_name"]
    # ここで output_dir を更新する。元のparams.output_dirではなく解決されたパスを使用
    output_dir = resolved_paths["output_dir"]
    scan_target = resolved_paths["scan_target"]

    # 2. 既存の制約事項を抽出
    constraint_parser = ConstraintParser()
    existing_constraints_str = constraint_parser.get_existing_constraints(existing_name)

    # 3. Gemini API クライアントの初期化
    gemini_client = GeminiDesignClient()

    # 4. プロンプトコンテンツ (GeminiRequest) の構築
    design_prompter = DesignPrompter()
    request = design_prompter.build_request(
        client=gemini_client._client,
        requirement=requirement,
        existing_name=existing_name,
        existing_constraints=existing_constraints_str,
        scan_target=scan_target,
        output_dir=output_dir
    )

    try:
        response_text = gemini_client.generate_design(contents=request)
    except Exception as e:
        return Output(status="failed", message=f"Gemini API 呼び出しエラー: {e}", output_file_path="")

    # 5. レスポンスのパースとdesign.json の保存
    try:
        design_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        return Output(status="failed", message=f"Gemini API レスポンスのパースエラー: {e}", output_file_path="")

    assets_output_dir = os.path.join(output_dir, "assets")
    output_file_path = os.path.join(assets_output_dir, "design.json")
    
    try:
        if not os.path.exists(assets_output_dir):
            os.makedirs(assets_output_dir)

        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(design_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return Output(status="failed", message=f"design.json の保存エラー: {e}", output_file_path="")

    message = f"design.json が '{output_file_path}' に正常に生成されました。"
    return Output(status="success", message=message, output_file_path=output_file_path)
