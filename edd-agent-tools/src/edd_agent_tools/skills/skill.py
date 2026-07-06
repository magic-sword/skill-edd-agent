import os
from typing import Literal, Any
from edd_agent_tools.models import SkillDesign
from edd_agent_tools.evaluation import SkillEval, UnitEval, TriggerEval

class Skill:
    """特定のスキルパッケージ全体のモデル（フォルダ構造、アセット、動的ロード、ツール化など）を表現・管理するドメインクラス。

    Examples:
        >>> from edd_agent_tools.skills import SkillsState
        >>> state = SkillsState()
        >>> skill = state.get_skill("skill-spec-writer")
        >>> print(skill.name)
        'skill-spec-writer'

        # 主要パスへのアクセス
        >>> design_path = skill.design_path
        >>> source_code_dir = skill.source_code_dir

        # アセットファイル（プロンプト等）の安全ロード
        >>> prompt_content = skill.load_asset("prompt.txt")
    """
    def __init__(self, root_dir: str, tier: int = 0, last_tested: str | None = None):
        self.root_dir = os.path.abspath(root_dir)
        self._tier = tier
        self._last_tested = last_tested
        self._metadata = None

    def set_tier(self, tier: int):
        """このスキルの Tier を設定し、テスト時間を更新します。

        Args:
            tier: 設定する Tier 値（0〜3）。

        Raises:
            ValueError: Tier が 0〜3 の範囲外の場合。
        """
        if tier not in [0, 1, 2, 3]:
            raise ValueError("Error: Tier must be 0, 1, 2, or 3.")
        self._tier = tier
        import datetime
        self._last_tested = datetime.datetime.now().isoformat() + "Z"
        self._metadata = None  # キャッシュクリア

    @property
    def metadata(self) -> "SkillMetadata":
        """型安全な SkillMetadata インスタンスをロードして返します。

        レジストリ JSON の登録情報と design.json の設計情報を統合します。

        Returns:
            統合された型安全な SkillMetadata。
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
        """自身の assets ディレクトリ配下の指定されたアセットファイルを読み込み、テキストとして返します。

        Args:
            asset_filename: 読み込むアセットファイルのファイル名。

        Returns:
            アセットファイルの内容文字列。

        Raises:
            FileNotFoundError: ファイルが存在しない、またはディレクトリである場合。
        """
        asset_path = os.path.join(self.root_dir, "assets", asset_filename)
        if not os.path.exists(asset_path) or os.path.isdir(asset_path):
            raise FileNotFoundError(f"Error: Required asset file not found at: {asset_path}")
        with open(asset_path, "r", encoding="utf-8") as f:
            return f.read()



    def load_spec(self) -> str:
        """仕様書（SKILL.md）のファイル内容を読み込み、テキストとして返します。

        Returns:
            仕様書（SKILL.md）の内容文字列。

        Raises:
            FileNotFoundError: 仕様書ファイルが存在しない場合。
        """
        spec_path = self.spec_path
        if not os.path.exists(spec_path):
            raise FileNotFoundError(f"Error: Skill specification not found at: {spec_path}")
        with open(spec_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_eval(self, eval_type_or_path: str) -> "SkillEval":
        """適切な SkillEval（UnitEval または TriggerEval）のインスタンスを取得します。

        Args:
            eval_type_or_path: 評価タイプ名（"unit" または "trigger"）、あるいは評価ケースファイルのパス。

        Returns:
            対応する SkillEval 派生クラスインスタンス（UnitEval または TriggerEval）。
        """
        basename = os.path.basename(eval_type_or_path)
        if "trigger" in basename or eval_type_or_path == "trigger":
            return TriggerEval(self)
        return UnitEval(self)

    def load_module(self):
        """このスキルパッケージの scripts/__init__.py をロードしモジュールオブジェクトを返します。

        他スキルの相対インポートとの名前空間の競合を防ぐため、
        一意の仮想パッケージの階層（edd_agent_tools.dynamic_skills.<name>.scripts）を構築してキャッシュします。

        Returns:
            ロードされた `scripts/__init__.py` のモジュールオブジェクト。

        Examples:
            >>> from edd_agent_tools.skills import SkillsState
            >>> state = SkillsState()
            >>> skill = state.get_skill("my-sample-skill")
            >>> handler_module = skill.load_module()
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
        skill_module = self.load_module()
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

