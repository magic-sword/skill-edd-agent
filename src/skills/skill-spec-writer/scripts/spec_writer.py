import os
import sys
import json
from google.adk.tools import ToolContext
from .writer.factory import SpecWriterFactory
from .models import Input

def process_message(params: Input, tool_context: ToolContext) -> str:
    """
    spec-writer のメインビジネスロジック。
    仕様書 (SKILL.md) を自動生成します。
    """
    design_path = params.design_path
    skill = params.skill
    output_dir = params.output_dir
    source_code_dir = params.source_code_dir

    from edd_agent_tools.models import SkillDesign
    from edd_agent_tools.registry import SkillRegistry

    # スキルレジストリ
    registry = SkillRegistry()

    # 1. ディレクトリ構造の特定とメタデータのロード
    directory = registry.get_skill_directory(name=skill, design_path=design_path)
    design_data = directory.load_design()

    # 2. オプションパラメータのフォールバック解決
    output_dir = os.path.abspath(output_dir or directory.root_dir)
    scan_target = os.path.abspath(source_code_dir or directory.source_code_dir)

    print(f"Starting specification generation for skill: {design_data.name}")
    print(f"Design Path: {design_path}")
    print(f"Output Directory: {output_dir}")

    # execution_type に基づいて適切な具象ライターを構築して実行
    try:
        writer = SpecWriterFactory.create(
            execution_type=design_data.execution_type,
            design_data=design_data,
            source_code_dir=scan_target,
            tool_context=tool_context
        )
        
        output_file_path = writer.generate(output_dir)
        
        print(f"🎉 Successfully generated specification at: {output_file_path}")
        
        message = f"Successfully generated specification at: {output_file_path}"
        tool_context.state.update({
            "status": "success",
            "message": message,
            "output_file_path": output_file_path
        })
        return message
    except Exception as e:
        print(f"❌ Error during specification generation: {e}", file=sys.stderr)
        tool_context.state.update({
            "status": "failed",
            "message": str(e)
        })
        raise e
