import os
import json
from typing import List

from edd_agent_tools.registry import SkillDirectory
from edd_agent_tools.models import SkillDesign
from .writer import PydanticModelWriter, HandlerWriter

class CodeGenerator:
    """
    スキル実装に必要なコードファイル（models.py, handler.py, __init__.py）を
    決定論的に自動生成するクラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_directory: SkillDirectory):
        self._design = design
        self._target_root_dir = target_root_dir
        self._scripts_dir = os.path.join(self._target_root_dir, "scripts")
        self._coder_directory = coder_directory

    def generate_all(self) -> List[str]:
        """
        すべての決定論的ファイルを生成します。
        生成されたファイルの相対パスリストを返します。
        """
        generated_files = []

        # 1. 必要なディレクトリ構成の確保
        os.makedirs(self._scripts_dir, exist_ok=True)
        os.makedirs(os.path.join(self._target_root_dir, "assets"), exist_ok=True)
        os.makedirs(os.path.join(self._target_root_dir, "references"), exist_ok=True)
            
        # 2. models.py の自動生成
        models_tmpl = self._coder_directory.load_asset("models.py.template")
        models_code = PydanticModelWriter(self._design, models_tmpl).write()
        models_path = os.path.join(self._scripts_dir, "models.py")
        with open(models_path, "w", encoding="utf-8") as f:
            f.write(models_code)
        print(f"決定論的モデルファイルを生成しました: {models_path}")
        generated_files.append(os.path.relpath(models_path, self._target_root_dir))
    
        # 3. handler.py の自動生成
        handler_tmpl = self._coder_directory.load_asset("handler.py.template")
        handler_code = HandlerWriter(self._design, handler_tmpl).write()
        handler_path = os.path.join(self._scripts_dir, "handler.py")
        with open(handler_path, "w", encoding="utf-8") as f:
            f.write(handler_code)
        print(f"決定論的ハンドラーファイルを生成しました: {handler_path}")
        generated_files.append(os.path.relpath(handler_path, self._target_root_dir))

        # 4. __init__.py の決定論的自動生成 (テンプレートのコピー)
        init_tmpl = self._coder_directory.load_asset("__init__.py.template")
        init_path = os.path.join(self._scripts_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(init_tmpl)
        print(f"決定論的パッケージ初期化ファイルを生成しました: {init_path}")
        generated_files.append(os.path.relpath(init_path, self._target_root_dir))

        # 5. logic.py のプレースホルダー配置（存在しない場合のみ）
        logic_path = os.path.join(self._scripts_dir, "logic.py")
        if not os.path.exists(logic_path):
            logic_tmpl = self._coder_directory.load_asset("logic.py.template")
            with open(logic_path, "w", encoding="utf-8") as f:
                f.write(logic_tmpl)
            print(f"logic.py のプレースホルダーを配置しました: {logic_path}")
            generated_files.append(os.path.relpath(logic_path, self._target_root_dir))
            
        return generated_files
