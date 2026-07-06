import os
import json
from abc import ABC, abstractmethod
from typing import List

from edd_agent_tools.skills import Skill
from edd_agent_tools.models import SkillDesign, ModuleType
from .writer import PydanticModelWriter, HandlerWriter

class BaseCodeGenerator(ABC):
    """
    コードファイル自動生成の抽象基底クラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_skill: Skill):
        self.design = design
        self.target_root_dir = target_root_dir
        self.scripts_dir = os.path.join(target_root_dir, "scripts")
        self.coder_skill = coder_skill

    def create_common_directories(self):
        """共通ディレクトリの作成"""
        os.makedirs(self.scripts_dir, exist_ok=True)
        os.makedirs(os.path.join(self.target_root_dir, "assets"), exist_ok=True)
        os.makedirs(os.path.join(self.target_root_dir, "references"), exist_ok=True)

    @abstractmethod
    def generate(self) -> List[str]:
        """各モジュールタイプに応じた具体的なコード生成処理"""
        pass


class ToolSkillCodeGenerator(BaseCodeGenerator):
    """
    決定論的スキル（従来どおりのtool）用のコードを生成する具象クラス。
    """
    def generate(self) -> List[str]:
        self.create_common_directories()
        generated_files = []

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

        # 3. __init__.py の決定論的自動生成 (テンプレートのコピー)
        init_tmpl = self.coder_skill.load_asset("templates/tool/__init__.py.template")
        init_path = os.path.join(self.scripts_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_tmpl)
        print(f"決定論的パッケージ初期化ファイルを生成しました: {init_path}")
        generated_files.append(os.path.relpath(init_path, self.target_root_dir))

        # 4. executor.py のプレースホルダー配置（存在しない場合のみ）
        executor_path = os.path.join(self.scripts_dir, "executor.py")
        if not os.path.exists(executor_path):
            executor_tmpl = self.coder_skill.load_asset("templates/tool/executor.py.template")
            with open(executor_path, "w", encoding="utf-8") as f:
                f.write(executor_tmpl)
            print(f"executor.py のプレースホルダーを配置しました: {executor_path}")
            generated_files.append(os.path.relpath(executor_path, self.target_root_dir))
            
        return generated_files


class WorkflowAgentCodeGenerator(BaseCodeGenerator):
    """
    ワークフローエージェント用のコードおよび決定論的ハーネスを生成する具象クラス。
    """
    def generate(self) -> List[str]:
        self.create_common_directories()
        generated_files = []

        # モジュール名や名前の取得
        workflow_name = self.design.name
        workflow_module_name = workflow_name.replace("-", "_")

        # 1. models.py の自動生成
        models_tmpl = self.coder_skill.load_asset("templates/workflow/models.py.template")
        models_code = PydanticModelWriter(self.design, models_tmpl).write()
        models_path = os.path.join(self.scripts_dir, "models.py")
        with open(models_path, "w", encoding="utf-8") as f:
            f.write(models_code)
        print(f"決定論的モデルファイルを生成しました (workflow): {models_path}")
        generated_files.append(os.path.relpath(models_path, self.target_root_dir))

        # 2. handler.py の自動生成 (templates/workflow/handler.py.template を展開)
        handler_tmpl = self.coder_skill.load_asset("templates/workflow/handler.py.template")
        handler_code = HandlerWriter(self.design, handler_tmpl).write()
        handler_path = os.path.join(self.scripts_dir, "handler.py")
        with open(handler_path, "w", encoding="utf-8") as f:
            f.write(handler_code)
        print(f"決定論的ハンドラーファイルを生成しました (workflow): {handler_path}")
        generated_files.append(os.path.relpath(handler_path, self.target_root_dir))

        # 3. __init__.py の自動生成 (templates/workflow/__init__.py.template を展開)
        init_tmpl = self.coder_skill.load_asset("templates/workflow/__init__.py.template")
        init_code = init_tmpl.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
        init_path = os.path.join(self.scripts_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_code)
        print(f"決定論的パッケージ初期化ファイルを生成しました (workflow): {init_path}")
        generated_files.append(os.path.relpath(init_path, self.target_root_dir))

        # 4. workflow.py のプレースホルダー配置（存在しない場合のみ）
        workflow_path = os.path.join(self.scripts_dir, "workflow.py")
        if not os.path.exists(workflow_path):
            workflow_tmpl = self.coder_skill.load_asset("templates/workflow/workflow.py.template")
            workflow_code = workflow_tmpl.replace("{workflow_name}", workflow_name).replace("{workflow_module_name}", workflow_module_name)
            with open(workflow_path, "w", encoding="utf-8") as f:
                f.write(workflow_code)
            print(f"workflow.py のプレースホルダーを配置しました: {workflow_path}")
            generated_files.append(os.path.relpath(workflow_path, self.target_root_dir))

        # 5. workflow_logic.py のプレースホルダー配置（存在しない場合のみ）
        logic_path = os.path.join(self.scripts_dir, "workflow_logic.py")
        if not os.path.exists(logic_path):
            logic_tmpl = self.coder_skill.load_asset("templates/workflow/workflow_logic.py.template")
            logic_code = logic_tmpl.replace("{workflow_name}", workflow_name)
            with open(logic_path, "w", encoding="utf-8") as f:
                f.write(logic_code)
            print(f"workflow_logic.py のプレースホルダーを配置しました: {logic_path}")
            generated_files.append(os.path.relpath(logic_path, self.target_root_dir))

        return generated_files


class CodeGenerator:
    """
    スキルまたはワークフローの実装に必要なコードファイルを
    決定論的に自動生成するファクトリラッッパークラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_skill: Skill):
        # module_type に応じて適切なジェネレータを選択
        if design.module_type == ModuleType.WORKFLOW:
            self._generator = WorkflowAgentCodeGenerator(design, target_root_dir, coder_skill)
        else:
            self._generator = ToolSkillCodeGenerator(design, target_root_dir, coder_skill)

    def generate_all(self) -> List[str]:
        """
        すべての決定論的ファイルを生成します。
        生成されたファイルの相対パスリストを返します。
        """
        return self._generator.generate()
