import os
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
