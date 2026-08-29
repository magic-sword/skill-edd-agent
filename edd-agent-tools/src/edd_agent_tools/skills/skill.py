import os
import sys
import json
import datetime
import types
import inspect
import importlib.util
from pathlib import Path
from typing import Literal, Any, Optional

from google.adk.tools import FunctionTool
from .models import SkillSpec, SkillPattern, ModuleType, SkillMetadata
from edd_agent_tools.evaluation import SimulationEval

class Skill:
    """Markdown-First & Progressive Disclosure に準拠したスキルパッケージ管理ドメインクラス。
    
    SKILL.md を単一真実源（Single Source of Truth）とし、
    3層リソース（scripts, references, assets）およびテスト環境（tests）を型安全にカプセル化します。

    Examples:
        >>> from edd_agent_tools.skills import SkillsState
        >>> state = SkillsState()
        >>> skill = state.get_skill("sample-skill")  # doctest: +SKIP
        >>> skill.name  # doctest: +SKIP
        'sample-skill'
        >>> skill.spec.description  # doctest: +SKIP
        'This skill should be used when...'
    """
    def __init__(self, root_dir: str | Path, tier: int = 0, last_tested: str | None = None):
        self.root_dir = os.path.abspath(str(root_dir))
        self._tier = tier
        self._last_tested = last_tested
        self._spec: Optional[SkillSpec] = None
        self._metadata: Optional[SkillMetadata] = None

    @property
    def tier(self) -> int:
        """このスキルの Tier (0: UNVALIDATED, 1: TIER1, 2: TIER2, 3: TIER3)"""
        return self._tier

    def set_tier(self, tier: int):
        """このスキルの Tier を設定し、テスト時刻を更新します。"""
        if tier not in [0, 1, 2, 3]:
            raise ValueError("Error: Tier must be 0, 1, 2, or 3.")
        self._tier = tier
        self._last_tested = datetime.datetime.now().isoformat() + "Z"
        self._metadata = None

    @property
    def spec_path(self) -> str:
        """SKILL.md の絶対パス"""
        return os.path.join(self.root_dir, "SKILL.md")

    @property
    def spec(self) -> SkillSpec:
        """SKILL.md をパースした SkillSpec インスタンスを取得（キャッシュ付き）"""
        if self._spec is None:
            if not os.path.exists(self.spec_path):
                # フォールバック用仮スペック
                from .models import SkillFrontmatter
                self._spec = SkillSpec(
                    frontmatter=SkillFrontmatter(name=os.path.basename(self.root_dir), description=""),
                    title=os.path.basename(self.root_dir),
                    overview="",
                    body=""
                )
            else:
                self._spec = SkillSpec.load_from_file(self.spec_path)
        return self._spec

    @property
    def name(self) -> str:
        """スキル名"""
        try:
            return self.spec.name
        except Exception:
            return os.path.basename(self.root_dir)

    @property
    def dependencies(self) -> list[str]:
        """このスキルが依存している他のスキル名のリスト"""
        try:
            return self.spec.dependencies
        except Exception:
            return []

    @property
    def description(self) -> str:
        """スキルの説明（Frontmatter の description）"""
        try:
            return self.spec.description
        except Exception:
            return ""

    @property
    def pattern(self) -> SkillPattern:
        """スキルパターン"""
        try:
            return self.spec.pattern
        except Exception:
            return SkillPattern.WORKFLOW

    # ==========================================
    # 3層リソース ディレクトリ・ファイルアクセス
    # ==========================================

    @property
    def scripts_dir(self) -> str:
        """scripts/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "scripts")

    @property
    def references_dir(self) -> str:
        """references/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "references")

    @property
    def assets_dir(self) -> str:
        """assets/ ディレクトリの絶対パス"""
        return os.path.join(self.root_dir, "assets")

    def list_scripts(self) -> list[str]:
        """内包されている実行スクリプトの相対ファイル名リストを取得"""
        if not os.path.exists(self.scripts_dir):
            return []
        return sorted([f for f in os.listdir(self.scripts_dir) if not f.startswith("__") and not f.startswith(".")])

    def list_references(self) -> list[str]:
        """内包されている参照資料の相対ファイル名リストを取得"""
        if not os.path.exists(self.references_dir):
            return []
        return sorted([f for f in os.listdir(self.references_dir) if not f.startswith(".")])

    def list_assets(self) -> list[str]:
        """内包されているアセット（テンプレート等）の相対ファイル名リストを取得"""
        if not os.path.exists(self.assets_dir):
            return []
        return sorted([f for f in os.listdir(self.assets_dir) if not f.startswith(".")])

    def load_spec(self) -> str:
        """SKILL.md のファイル内容をそのままテキストとして返します。"""
        if not os.path.exists(self.spec_path):
            raise FileNotFoundError(f"Error: SKILL.md not found at: {self.spec_path}")
        with open(self.spec_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_reference(self, filename: str) -> str:
        """references/ ディレクトリ配下の指定ドキュメントを読み込みます。"""
        ref_path = os.path.join(self.references_dir, filename)
        if not os.path.exists(ref_path) or os.path.isdir(ref_path):
            raise FileNotFoundError(f"Error: Required reference file not found at: {ref_path}")
        with open(ref_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_asset(self, asset_filename: str) -> str:
        """assets/ ディレクトリ配下の指定ファイルを読み込みます。"""
        asset_path = os.path.join(self.assets_dir, asset_filename)
        if not os.path.exists(asset_path) or os.path.isdir(asset_path):
            raise FileNotFoundError(f"Error: Required asset file not found at: {asset_path}")
        with open(asset_path, "r", encoding="utf-8") as f:
            return f.read()

    @property
    def tests(self) -> "SkillTests":
        """テスト定義および実行ログ管理インターフェースを取得"""
        from .tests import SkillTests
        return SkillTests(self.root_dir)

    @property
    def metadata(self) -> SkillMetadata:
        """統合メタデータを取得"""
        if self._metadata is None:
            self._metadata = SkillMetadata(
                name=self.name,
                tier=self._tier,
                last_tested=self._last_tested,
                module_type=ModuleType.SKILL,
                pattern=self.pattern,
                description=self.description,
                scripts=self.list_scripts(),
                references=self.list_references(),
                assets=self.list_assets()
            )
        return self._metadata

    def get_eval(self) -> "SimulationEval":
        """SimulationEval インスタンスを取得"""
        return SimulationEval(self)

    # ==========================================
    # 動的ツール化 (FunctionTool Generation)
    # ==========================================

    def load_module(self):
        """scripts/__init__.py または主要スクリプトをロードしモジュールオブジェクトを返します。"""
        script_abs_path = os.path.join(self.scripts_dir, "__init__.py")
        
        # scripts/__init__.py がない場合は単体スクリプトを自動探索
        if not os.path.exists(script_abs_path):
            py_files = [f for f in os.listdir(self.scripts_dir) if f.endswith(".py") and not f.startswith("__")] if os.path.exists(self.scripts_dir) else []
            if py_files:
                script_abs_path = os.path.join(self.scripts_dir, py_files[0])
            else:
                raise FileNotFoundError(f"Error: No valid Python script found in: {self.scripts_dir}")

        skill_name_under = self.name.replace('-', '_')
        parent_pkg = f"edd_agent_tools.dynamic_skills.{skill_name_under}"
        package_name = f"{parent_pkg}.scripts"
        module_name = package_name

        if module_name in sys.modules:
            return sys.modules[module_name]

        if self.root_dir not in sys.path:
            sys.path.insert(0, self.root_dir)

        if parent_pkg not in sys.modules:
            sys.modules[parent_pkg] = types.ModuleType(parent_pkg)
        if package_name not in sys.modules:
            pkg_module = types.ModuleType(package_name)
            pkg_module.__path__ = [self.scripts_dir]
            pkg_module.__package__ = package_name
            sys.modules[package_name] = pkg_module

        spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {script_abs_path}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = package_name
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def get_tools(self) -> list[FunctionTool]:
        """このスキルの scripts/ 配下から公開関数をスキャンし、FunctionTool のリストとして構築して返します。"""
        if not os.path.exists(self.scripts_dir):
            return []

        try:
            skill_module = self.load_module()
        except FileNotFoundError:
            return []

        tools = []
        # 1. __all__ が定義されている場合はそれを優先
        if hasattr(skill_module, "__all__"):
            export_names = getattr(skill_module, "__all__")
        else:
            # 2. 定義されていない場合はアンダースコア始まりでない関数を抽出
            export_names = [n for n, obj in inspect.getmembers(skill_module, inspect.isfunction) if not n.startswith("_")]

        for name in export_names:
            obj = getattr(skill_module, name, None)
            if obj and inspect.isfunction(obj):
                obj.__name__ = name
                if not obj.__doc__:
                    obj.__doc__ = self.description or f"Execute {name} task"
                tools.append(FunctionTool(func=obj))

        return tools

    def get_tool(self) -> FunctionTool:
        """単一の FunctionTool を取得します。"""
        tools = self.get_tools()
        if not tools:
            raise AttributeError(f"Error: Skill '{self.name}' provides no executable tool functions in scripts/.")
        if len(tools) == 1:
            return tools[0]
        raise ValueError(
            f"Error: Skill '{self.name}' exports multiple tools ({[t.name for t in tools]}). "
            "Please use get_tools() instead."
        )
