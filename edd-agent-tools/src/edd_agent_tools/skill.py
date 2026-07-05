import os
from typing import Literal
from edd_agent_tools.models import SkillDesign

class Skill:
    """
    特定のスキルパッケージ全体のモデル（フォルダ構造、アセット、動的ロード、ツール化など）を表現・管理するドメインクラス。
    """
    def __init__(self, root_dir: str, tier: int = 0, last_tested: str | None = None):
        self.root_dir = os.path.abspath(root_dir)
        self._tier = tier
        self._last_tested = last_tested
        self._metadata = None

    @property
    def metadata(self) -> "SkillMetadata":
        """
        レジストリ JSON の登録情報と design.json の設計情報を統合した
        型安全な SkillMetadata インスタンスをロードして返します。
        """
        if self._metadata is None:
            # 1. design.json から設計データをロード
            try:
                design = self.load_design()
                module_type = design.module_type
                execution_type = design.execution_type
                description = design.description
                dependencies = design.dependencies
            except Exception:
                import json
                from edd_agent_tools.models import ModuleType
                
                # 物理配置または design.json の構造からワークフローを自動検出
                has_workflow_indicator = False
                try:
                    if os.path.exists(self.design_path):
                        with open(self.design_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "edges" in data or "agents" in data:
                                has_workflow_indicator = True
                except Exception:
                    pass

                if "src/agents" in self.root_dir or "/agents/" in self.root_dir or has_workflow_indicator:
                    module_type = ModuleType.WORKFLOW
                else:
                    module_type = ModuleType.SKILL

                execution_type = "tool"
                description = ""
                dependencies = []

            # 2. 統合
            from edd_agent_tools.models import SkillMetadata
            self._metadata = SkillMetadata(
                name=self.name,
                tier=self._tier,
                last_tested=self._last_tested,
                module_type=module_type,
                execution_type=execution_type,
                description=description,
                dependencies=dependencies
            )
        return self._metadata

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

    def load(self):
        """
        このスキルパッケージの scripts/__init__.py を、
        一意の名前空間の下でキャッシュの干渉なくロードし、モジュールオブジェクトを返します。
        """
        import sys
        import types
        import importlib.util

        script_abs_path = os.path.join(self.root_dir, "scripts", "__init__.py")
        if not os.path.exists(script_abs_path):
            raise FileNotFoundError(f"エラー: scripts/__init__.py が存在しません: {script_abs_path}")

        # 一意の名前空間（仮想FQDN）の組み立て
        skill_name_under = self.name.replace('-', '_')
        parent_pkg = f"edd_agent_tools.dynamic_skills.{skill_name_under}"
        package_name = f"{parent_pkg}.scripts"
        module_name = package_name

        # すでにロードされている場合はキャッシュを返す
        if module_name in sys.modules:
            return sys.modules[module_name]

        # 相対インポートを正常に解決するため sys.path を調整
        if self.root_dir not in sys.path:
            sys.path.insert(0, self.root_dir)

        # 仮想パッケージモジュールの動的登録 (相対インポート解決用)
        if parent_pkg not in sys.modules:
            sys.modules[parent_pkg] = types.ModuleType(parent_pkg)
        if package_name not in sys.modules:
            pkg_module = types.ModuleType(package_name)
            pkg_module.__path__ = [os.path.join(self.root_dir, "scripts")]
            pkg_module.__package__ = package_name
            sys.modules[package_name] = pkg_module

        # ロード実行
        spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {script_abs_path}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = package_name  # 相対インポートに必須
        sys.modules[module_name] = module

        spec.loader.exec_module(module)
        return module

    def get_tool(self):
        """
        このスキルに対応する ADK の FunctionTool オブジェクトをロード・構築して返します。
        """
        from google.adk.tools import FunctionTool

        # モジュールをロード
        skill_module = self.load()
        process_func = getattr(skill_module, "process_message")

        # 設計定義（design.json）から説明を取得
        try:
            design_data = self.load_design()
            description = design_data.description
        except Exception:
            description = f"Execute {self.name} skill"

        # 関数の属性を動的に書き換えることで、FunctionTool がツール名と説明を正しく解決できるようにする
        process_func.__name__ = self.name.replace("-", "_")
        process_func.__doc__ = description

        return FunctionTool(func=process_func)
