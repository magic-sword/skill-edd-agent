import os
import sys
import json
from google.adk.tools import ToolContext
from .writer.factory import SpecWriterFactory

def process_message(tool_context: ToolContext):
    """
    spec-writer のメインビジネスロジック。
    仕様書 (SKILL.md) を自動生成します。
    """
    design_path = tool_context.state.get("design_path")
    skill = tool_context.state.get("skill")
    output_dir = tool_context.state.get("output_dir")
    source_code_dir = tool_context.state.get("source_code_dir")

    from edd_agent_tools.models import SkillDesign
    from edd_agent_tools.registry import SkillRegistry

    # スキルレジストリのロード
    registry = SkillRegistry()
    registry.load()

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
        
        tool_context.state.update({
            "status": "success",
            "message": f"Successfully generated specification at: {output_file_path}",
            "output_file_path": output_file_path
        })
    except Exception as e:
        print(f"❌ Error during specification generation: {e}", file=sys.stderr)
        tool_context.state.update({
            "status": "failed",
            "message": str(e)
        })
        raise e
