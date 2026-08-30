"""
Core Skill Entity for edd-agent-tools

Markdown-First & Progressive Disclosure に準拠したスキルパッケージ管理ドメインクラス。
"""

import os
import sys
import json
import datetime
import types
import inspect
import importlib.util
from pathlib import Path
from typing import Literal, Any, Optional

from .models import SkillSpec, SkillPattern, ModuleType, SkillMetadata


class Skill:
    """Markdown-First & Progressive Disclosure に準拠したスキルパッケージ管理ドメインクラス。
    
    SKILL.md を単一真実源（Single Source of Truth）とし、
    3層リソース（scripts, references, assets）およびテスト環境（tests）を型安全にカプセル化します。
    """
    def __init__(self, root_dir: str | Path, tier: int = 0, last_tested: str | None = None):
        self.root_dir = os.path.abspath(str(root_dir))
        self._tier = tier
        self._last_tested = last_tested
        self._spec: Optional[SkillSpec] = None
        self._metadata: Optional[SkillMetadata] = None

    @property
    def tier(self) -> int:
        """このスキルの Tier (0: SANDBOX, 1: READ_ONLY, 2: DRAFT_ONLY, 3: ACTION_ALLOWED)"""
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
    def tests(self) -> Any:
        """テスト定義および実行ログ管理インターフェースを取得"""
        from edd_agent_tools.skills.tests import SkillTests
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

    def get_eval(self) -> Any:
        """SimulationEval インスタンスを取得"""
        from edd_agent_tools.evaluation.evaluation import SimulationEval
        return SimulationEval(self)

    # ==========================================
    # 決定論的スクリプト実行 & モジュールロード
    # ==========================================

    def get_script_path(self, script_name: str) -> str:
        """scripts/ 配下の指定スクリプトの絶対パスを取得します。"""
        target = os.path.join(self.scripts_dir, script_name)
        if not os.path.exists(target):
            raise FileNotFoundError(f"Error: Script '{script_name}' not found in: {self.scripts_dir}")
        return target

    def load_module(self, script_name: str | None = None):
        """scripts/ 配下の指定スクリプト（省略時は最初に見つかった .py ファイル）を直接ロードしてモジュールを返します。"""
        if not os.path.exists(self.scripts_dir):
            raise FileNotFoundError(f"Error: scripts/ directory not found in: {self.root_dir}")

        if script_name:
            script_abs_path = self.get_script_path(script_name)
        else:
            py_files = sorted([f for f in os.listdir(self.scripts_dir) if f.endswith(".py") and not f.startswith("__")])
            if not py_files:
                raise FileNotFoundError(f"Error: No valid Python script found in: {self.scripts_dir}")
            script_abs_path = os.path.join(self.scripts_dir, py_files[0])

        module_name = f"edd_skills.{self.name.replace('-', '_')}.{Path(script_abs_path).stem}"
        if module_name in sys.modules:
            return sys.modules[module_name]

        if self.root_dir not in sys.path:
            sys.path.insert(0, self.root_dir)
        if self.scripts_dir not in sys.path:
            sys.path.insert(0, self.scripts_dir)

        spec = importlib.util.spec_from_file_location(module_name, script_abs_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {script_abs_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
