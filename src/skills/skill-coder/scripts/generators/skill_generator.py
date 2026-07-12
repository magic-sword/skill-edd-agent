import os
from typing import List

from edd_agent_tools.models import SkillDesign
from ..writer import PydanticModelWriter, HandlerWriter, ExecutorWriter
from .base import BaseCodeGenerator

class ToolSkillCodeGenerator(BaseCodeGenerator):
    """
    決定論的スキル用のコードを生成する具象クラス。
    """
    def generate(self) -> List[str]:
        self.create_common_directories()
        generated_files = []

        function_name = self.design.name.replace("-", "_")

        # 1. models.py の自動生成
        models_tmpl = self.coder_skill.load_asset("templates/tool/models.py.template")
        models_code = PydanticModelWriter(self.design, models_tmpl).write()
        models_path = os.path.join(self.scripts_dir, "models.py")
        with open(models_path, "w", encoding="utf-8") as f:
            f.write(models_code)
        print(f"決定論的モデルファイルを生成しました: {models_path}")
        generated_files.append(os.path.relpath(models_path, self.target_root_dir))

        # 2. handler.py の自動生成
        handler_tmpl = self.coder_skill.load_asset("templates/tool/handler.py.template")
        handler_code = HandlerWriter(self.design, handler_tmpl).write()
        handler_path = os.path.join(self.scripts_dir, "handler.py")
        with open(handler_path, "w", encoding="utf-8") as f:
            f.write(handler_code)
        print(f"決定論的ハンドラーファイルを生成しました: {handler_path}")
        generated_files.append(os.path.relpath(handler_path, self.target_root_dir))

        # 3. __init__.py の決定論的自動生成 (プレースホルダー展開)
        init_tmpl = self.coder_skill.load_asset("templates/tool/__init__.py.template")
        init_code = init_tmpl.replace("{function_name}", function_name)
        init_path = os.path.join(self.scripts_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_code)
        print(f"決定論的パッケージ初期化ファイルを生成しました: {init_path}")
        generated_files.append(os.path.relpath(init_path, self.target_root_dir))

        # 4. executor.py のプレースホルダー配置（存在しない場合のみ）
        executor_path = os.path.join(self.scripts_dir, "executor.py")
        if not os.path.exists(executor_path):
            executor_tmpl = self.coder_skill.load_asset("templates/tool/executor.py.template")
            executor_code = ExecutorWriter(self.design, executor_tmpl).write()
            with open(executor_path, "w", encoding="utf-8") as f:
                f.write(executor_code)
            print(f"executor.py のプレースホルダーを配置しました: {executor_path}")
            generated_files.append(os.path.relpath(executor_path, self.target_root_dir))
            
        return generated_files
