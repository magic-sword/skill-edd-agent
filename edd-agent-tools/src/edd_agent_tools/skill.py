"""
Unified Skill Entity for edd-agent-tools

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
from typing import Literal, Any, Optional, List, Dict

from .models.spec import SkillSpec, SkillPattern, ModuleType, SkillMetadata
from .models.state import SkillTier


class Skill:
    """Markdown-First & Progressive Disclosure に準拠したスキルパッケージ管理ドメインクラス。

    SKILL.md を単一真実源（Single Source of Truth）とし、
    3層リソース（scripts, references, assets）およびテスト環境（tests）を型安全にカプセル化します。
    """
    def __init__(self, root_dir: str | Path, tier: int = 0, last_tested: Optional[str] = None):
        self.root_dir = os.path.abspath(str(root_dir))
        self._tier = tier
        self._last_tested = last_tested
        self._spec: Optional[SkillSpec] = None
        self._metadata: Optional[SkillMetadata] = None
        self._tests = None

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
                from .models.spec import SkillFrontmatter
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
    def dependencies(self) -> List[str]:
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

    @property
    def tests(self):
        """テスト管理オブジェクト（SkillTests）を取得"""
        if self._tests is None:
            from .skills.tests import SkillTests
            self._tests = SkillTests(self.root_dir)
        return self._tests

    # ==========================================
    # 3層リソース探索・取得メソッド群
    # ==========================================

    def list_scripts(self) -> List[str]:
        """内包するスクリプト（ファイル名ベース）の一覧を取得"""
        scripts_dir = Path(self.root_dir) / "scripts"
        if not scripts_dir.exists():
            return []
        return sorted([f.name for f in scripts_dir.glob("*.py") if f.name != "__init__.py"])

    def list_references(self) -> List[str]:
        """内包する参照資料（ファイル名ベース）の一覧を取得"""
        ref_dir = Path(self.root_dir) / "references"
        if not ref_dir.exists():
            return []
        return sorted([f.name for f in ref_dir.glob("*") if f.is_file()])

    def list_assets(self) -> List[str]:
        """内包するアセット（ファイル名ベース）の一覧を取得"""
        assets_dir = Path(self.root_dir) / "assets"
        if not assets_dir.exists():
            return []
        return sorted([f.name for f in assets_dir.glob("*") if f.is_file()])

    def read_reference(self, rel_path: str) -> str:
        """指定された参照資料のコンテンツを読み込みます。"""
        target = Path(self.root_dir) / rel_path
        if not target.exists():
            cand = Path(self.root_dir) / "references" / rel_path
            if cand.exists():
                target = cand
        if not target.exists():
            raise FileNotFoundError(f"Reference '{rel_path}' not found in skill '{self.name}'.")
        return target.read_text(encoding="utf-8")

    def load_reference(self, rel_path: str) -> str:
        """指定された参照資料のコンテンツを読み込みます（read_reference のエイリアス）。"""
        return self.read_reference(rel_path)

    def get_script_path(self, script_name: str) -> str:
        """指定されたスクリプトの絶対パスを返します。"""
        scripts_dir = Path(self.root_dir) / "scripts"
        cand = scripts_dir / script_name
        if cand.exists():
            return str(cand)
        cand_py = scripts_dir / f"{script_name}.py"
        if cand_py.exists():
            return str(cand_py)
        return str(cand)

    def load_module(self, script_name: Optional[str] = None) -> types.ModuleType:
        """スキルのスクリプトを動的に Python モジュールとしてインポート・ロードします。"""
        scripts_dir = Path(self.root_dir) / "scripts"
        if not scripts_dir.exists():
            raise FileNotFoundError(f"Scripts directory not found for skill: {self.name}")

        script_path = None
        if script_name:
            cand = scripts_dir / script_name
            if cand.exists():
                script_path = cand
            else:
                cand_py = scripts_dir / f"{script_name}.py"
                if cand_py.exists():
                    script_path = cand_py

        if not script_path:
            cand1 = scripts_dir / f"{self.name.replace('-', '_')}.py"
            cand2 = scripts_dir / f"{self.name}.py"
            cand3 = scripts_dir / "main.py"
            for c in [cand1, cand2, cand3]:
                if c.exists():
                    script_path = c
                    break

        if not script_path:
            py_files = [f for f in scripts_dir.glob("*.py") if f.name != "__init__.py"]
            if py_files:
                script_path = py_files[0]

        if not script_path or not script_path.exists():
            raise FileNotFoundError(f"No executable script found for skill: {self.name}")

        module_name = f"edd_skill_{self.name.replace('-', '_')}_{script_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, str(script_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load module spec for: {script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def get_metadata(self) -> SkillMetadata:
        """レジストリ・評価・仕様をマージした統合メタデータを返します。"""
        if self._metadata is None:
            self._metadata = SkillMetadata(
                name=self.name,
                tier=self.tier,
                last_tested=self._last_tested,
                module_type=ModuleType.SKILL,
                pattern=self.pattern,
                description=self.description,
                scripts=self.list_scripts(),
                references=self.list_references(),
                assets=self.list_assets()
            )
        return self._metadata

    def __repr__(self) -> str:
        return f"<Skill name='{self.name}' tier={self.tier} path='{self.root_dir}'>"
