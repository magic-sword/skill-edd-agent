import os
import sys
import json
from google.adk.tools import ToolContext
from .models import Input, Output
from .writer.factory import SpecWriterFactory

# 循環参照を避けるため、edd_agent_tools のインポートはここに集約
from edd_agent_tools.models import SkillDesign
from edd_agent_tools.registry import SkillRegistry

class SpecGenerator:
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context
        self.registry = SkillRegistry() # SkillRegistryは一度だけ初期化

    def generate(self) -> Output:
        design_path = self.params.design_path
        skill = self.params.skill
        output_dir = self.params.output_dir
        source_code_dir = self.params.source_code_dir

        try:
            # 1. ディレクトリ構造の特定とメタデータのロード
            # skill と design_path のいずれか一方は必ず指定する必要があるため、ここでバリデーション
            if not skill and not design_path:
                raise ValueError("Skill name or design path must be provided.")

            directory = self.registry.get_skill_directory(name=skill, design_path=design_path)
            design_data = directory.load_design()

            # 2. オプションパラメータのフォールバック解決
            output_dir = os.path.abspath(output_dir or directory.root_dir)
            scan_target = os.path.abspath(source_code_dir or directory.source_code_dir)

            print(f"Starting specification generation for skill: {design_data.name}")
            print(f"Design Path: {design_path}")
            print(f"Output Directory: {output_dir}")

            # execution_type に基づいて適切な具象ライターを構築して実行
            writer = SpecWriterFactory.create(
                execution_type=design_data.execution_type,
                design_data=design_data,
                source_code_dir=scan_target,
                tool_context=self.tool_context,
                prompt=self.params.prompt
            )
            
            output_file_path = writer.generate(output_dir)
            
            print(f"🎉 Successfully generated specification at: {output_file_path}")
            
            message = f"Successfully generated specification at: {output_file_path}"
            
            return Output(
                status="success",
                message=message,
                output_file_path=output_file_path
            )

        except Exception as e:
            print(f"❌ Error during specification generation: {e}", file=sys.stderr)
            return Output(
                status="failed",
                message=f"Specification generation failed: {e}",
                output_file_path=None
            )
