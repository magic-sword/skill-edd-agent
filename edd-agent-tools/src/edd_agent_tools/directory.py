import os
from typing import Literal
from edd_agent_tools.models import SkillDesign

class SkillDirectory:
    """
    特定のスキルのフォルダ構造と各主要ファイルのパスを一元管理するオブジェクト指向クラス。
    """
    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    @property
    def name(self) -> str:
        try:
            return SkillDesign.load_from_file(self.design_path).name
        except Exception:
            return os.path.basename(self.root_dir)

    @property
    def design_path(self) -> str:
        """design.json の絶対パス"""
        return os.path.join(self.root_dir, "assets", "design.json")

    @property
    def source_code_dir(self) -> str:
        """scripts の絶対パス"""
        return os.path.join(self.root_dir, "scripts")

    @property
    def spec_path(self) -> str:
        """SKILL.md の絶対パス"""
        return os.path.join(self.root_dir, "SKILL.md")

    def load_design(self) -> SkillDesign:
        return SkillDesign.load_from_file(self.design_path)

    def load_asset(self, asset_filename: str) -> str:
        """
        自身の assets ディレクトリ配下の指定されたアセットファイルを読み込み、テキストとして返します。
        ファイルが存在しない、またはディレクトリの場合は FileNotFoundError をスローします。
        """
        asset_path = os.path.join(self.root_dir, "assets", asset_filename)
        if not os.path.exists(asset_path) or os.path.isdir(asset_path):
            raise FileNotFoundError(f"Error: Required asset file not found at: {asset_path}")
        with open(asset_path, "r", encoding="utf-8") as f:
            return f.read()

    @property
    def tests_dir(self) -> str:
        """tests ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "tests")

    def get_test_filepath(self, filename: str) -> str:
        """
        tests ディレクトリ配下のテスト用ファイルの絶対パスを取得し、
        tests ディレクトリが存在しない場合は自動で作成します。
        """
        tests_dir = self.tests_dir
        os.makedirs(tests_dir, exist_ok=True)
        return os.path.join(tests_dir, filename)

    def load_spec(self) -> str:
        """
        仕様書（SKILL.md）のファイル内容を読み込み、テキストとして返します。
        ファイルが存在しない場合は FileNotFoundError をスローします。
        """
        spec_path = self.spec_path
        if not os.path.exists(spec_path):
            raise FileNotFoundError(f"Error: Skill specification not found at: {spec_path}")
        with open(spec_path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_filename(self, test_type: str, suffix: str) -> str:
        """一貫した命名規則に従ってテストファイル名を生成します"""
        skill_name_underscore = self.name.replace('-', '_')
        return f"{skill_name_underscore}_{test_type}.{suffix}"

    def get_eval_set_path(self, test_type: Literal["unit", "trigger"] | str = "unit") -> str:
        """
        評価用のテストケースファイル (*.evalset.json) の絶対パスを返します。
        """
        filename = self._get_filename(test_type, "evalset.json")
        return self.get_test_filepath(filename)

    def get_eval_config_path(self, test_type: Literal["unit", "trigger"] | str = "unit") -> str:
        """
        評価用の設定ファイル (*.evalset.config.json) の絶対パスを返します。
        """
        filename = self._get_filename(test_type, "evalset.config.json")
        return self.get_test_filepath(filename)

    def resolve_eval_config_path(self, eval_set_path: str) -> str:
        """
        テストケースファイルの絶対/相対パスから、対応する設定ファイルの絶対パスを逆引き解決します。
        """
        basename = os.path.basename(eval_set_path)
        test_type = "trigger" if "trigger" in basename else "unit"
        return self.get_eval_config_path(test_type)

    def save_eval_set(self, data: dict, test_type: Literal["unit", "trigger"] | str = "unit") -> str:
        """
        テストケースファイルを保存し、保存先パスを返します。
        """
        import json
        path = self.get_eval_set_path(test_type)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def save_eval_config(self, data: dict, test_type: Literal["unit", "trigger"] | str = "unit") -> str:
        """
        テスト構成ファイルを保存し、保存先パスを返します。
        """
        import json
        path = self.get_eval_config_path(test_type)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path
