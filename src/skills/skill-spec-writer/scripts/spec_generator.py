import os
import sys
import json
from .models import Input, Output
from .writer.factory import SpecWriterFactory

# 循環参照を避けるため、edd_agent_tools のインポートはここに集約
from edd_agent_tools import SkillDesign
from edd_agent_tools.skills import SkillsState

class SpecGenerator:
    def __init__(self, params: Input):
        self.params = params
        self.state = SkillsState() # SkillsStateは一度だけ初期化

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

            skill_obj = self.state.get_skill(name=skill, design_path=design_path)
            design_data = skill_obj.load_design()

            # 2. オプションパラメータのフォールバック解決
            output_dir = os.path.abspath(output_dir or skill_obj.root_dir)
            scan_target = os.path.abspath(source_code_dir or skill_obj.source_code_dir)

            print(f"Starting specification generation for skill: {design_data.name}")
            print(f"Design Path: {design_path}")
            print(f"Output Directory: {output_dir}")

            # 適切な具象ライターを構築して実行
            writer = SpecWriterFactory.create(
                design_data=design_data,
                source_code_dir=scan_target,
                prompt=self.params.prompt
            )
            
            output_file_path = writer.generate(output_dir)
            
            print(f"🎉 Successfully generated specification at: {output_file_path}")
            
            message = f"Successfully generated specification at: {output_file_path}"
            
            return Output(
                status="success",
                message=message,
                output_dir=output_dir
            )

        except Exception as e:
            print(f"❌ Error during specification generation: {e}", file=sys.stderr)
            err_output_dir = output_dir if output_dir else ""
            return Output(
                status="failed",
                message=f"Specification generation failed: {e}",
                output_dir=err_output_dir
            )
