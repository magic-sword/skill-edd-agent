"""
Skill Spec and Frontmatter Models for edd-agent-tools
"""

import os
import re
import yaml
from enum import StrEnum
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class SkillPattern(StrEnum):
    """4大スキル構造パターン"""
    WORKFLOW = "workflow"              # 順序立てられたステップや判断分岐がある作業 (Workflow-Based)
    TASK_BASED = "task_based"          # 独立した複数の操作・スクリプト群を提供するツール集 (Task-Based)
    REFERENCE = "reference"            # 規約・設計標準・ドメイン知識の提供 (Reference/Guidelines)
    CAPABILITIES = "capabilities"      # 複合的なシステム連携・包括的機能 (Capabilities-Based)


class ModuleType(StrEnum):
    """モジュールの分類"""
    SKILL = "skill"
    AGENT = "agent"


class SkillFrontmatter(BaseModel):
    """SKILL.md の YAML Frontmatter メタデータ"""
    name: str = Field(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="スキル識別子 (ハイフンケース)")
    description: str = Field(..., max_length=1024, description="トリガー条件を明記した第三者視点の説明")
    license: Optional[str] = Field("Complete terms in LICENSE.txt", description="ライセンス情報")
    pattern: Optional[SkillPattern] = Field(None, description="スキルパターン（任意）")
    dependencies: List[str] = Field(default_factory=list, description="依存するスキル一覧")


class SkillSpec(BaseModel):
    """パースされた SKILL.md の完全な仕様表現モデル"""
    frontmatter: SkillFrontmatter
    title: str = Field(..., description="スキルのタイトル")
    overview: str = Field(..., description="スキルの概要")
    body: str = Field(..., description="Frontmatterを除くMarkdown本文全体")
    pattern: SkillPattern = Field(SkillPattern.WORKFLOW, description="スキル構造パターン")
    when_not_to_use: List[str] = Field(default_factory=list, description="非適用条件のリスト")

    # 抽出されたリソース一覧（相対パス）
    scripts: List[str] = Field(default_factory=list, description="言及されている scripts/ 配下のファイル")
    references: List[str] = Field(default_factory=list, description="言及されている references/ 配下のファイル")
    assets: List[str] = Field(default_factory=list, description="言及されている assets/ 配下のファイル")

    @property
    def name(self) -> str:
        return self.frontmatter.name

    @property
    def description(self) -> str:
        return self.frontmatter.description

    @property
    def dependencies(self) -> List[str]:
        return self.frontmatter.dependencies

    @classmethod
    def parse_markdown(cls, content: str) -> "SkillSpec":
        """Markdown文字列をパースして SkillSpec インスタンスを生成します。"""
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        if not content.startswith("---"):
            raise ValueError("Invalid SKILL.md format: Missing YAML frontmatter start ('---')")

        match = re.match(r"^---\n(.*?)\n---\n*(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError("Invalid SKILL.md format: Could not parse YAML frontmatter boundary")

        fm_str = match.group(1)
        body_str = match.group(2)

        try:
            fm_dict = yaml.safe_load(fm_str)
            if not isinstance(fm_dict, dict):
                raise ValueError("Frontmatter is not a valid YAML mapping")
        except Exception as e:
            raise ValueError(f"Failed to parse YAML frontmatter: {e}")

        frontmatter = SkillFrontmatter.model_validate(fm_dict)

        # タイトルの抽出 (# Title)
        title_match = re.search(r"^#\s+(.+)$", body_str, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else frontmatter.name

        # Overview の抽出 (## Overview の次行から次の ## まで)
        overview_match = re.search(r"##\s+Overview\s*\n+(.*?)(?=\n##|\Z)", body_str, re.DOTALL | re.IGNORECASE)
        overview = overview_match.group(1).strip() if overview_match else ""

        # パターンの推定または取得 (frontmatterに明示されていればそれを最優先)
        if frontmatter.pattern:
            pattern = frontmatter.pattern
        elif re.search(r"^##\s+Workflow Decision Tree", body_str, re.MULTILINE | re.IGNORECASE):
            pattern = SkillPattern.WORKFLOW
        elif re.search(r"^##\s+Quick Start", body_str, re.MULTILINE | re.IGNORECASE) or re.search(r"^##\s+Available Tasks", body_str, re.MULTILINE | re.IGNORECASE):
            pattern = SkillPattern.TASK_BASED
        elif re.search(r"^##\s+Guidelines & Specifications", body_str, re.MULTILINE | re.IGNORECASE):
            pattern = SkillPattern.REFERENCE
        elif re.search(r"^##\s+Core Capabilities", body_str, re.MULTILINE | re.IGNORECASE):
            pattern = SkillPattern.CAPABILITIES
        else:
            pattern = SkillPattern.WORKFLOW

        # When NOT to use の抽出
        when_not_match = re.search(r"##\s+When NOT to Use[^\n]*\s*\n+(.*?)(?=\n##|\Z)", body_str, re.DOTALL | re.IGNORECASE)
        when_not_to_use = []
        if when_not_match:
            when_not_text = when_not_match.group(1).strip()
            for line in when_not_text.splitlines():
                line = line.strip()
                if line.startswith(("-", "*")):
                    when_not_to_use.append(line.lstrip("-* ").strip())

        # リソース言及の抽出 (scripts/..., references/..., assets/...)
        scripts = sorted(list(set(re.findall(r"`?scripts/([a-zA-Z0-9_\-\./]+)`?", body_str))))
        references = sorted(list(set(re.findall(r"`?references/([a-zA-Z0-9_\-\./]+)`?", body_str))))
        assets = sorted(list(set(re.findall(r"`?assets/([a-zA-Z0-9_\-\./]+)`?", body_str))))

        return cls(
            frontmatter=frontmatter,
            title=title,
            overview=overview,
            body=body_str,
            pattern=pattern,
            when_not_to_use=when_not_to_use,
            scripts=scripts,
            references=references,
            assets=assets
        )

    @classmethod
    def load_from_file(cls, filepath: str | Path) -> "SkillSpec":
        """SKILL.md ファイルから直接仕様をロードします。"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"SKILL.md not found at: {path}")
        return cls.parse_markdown(path.read_text(encoding="utf-8"))


class SkillMetadata(BaseModel):
    """レジストリ情報と仕様情報をマージした統合メタデータ"""
    name: str = Field(..., description="スキル名")
    tier: int = Field(0, description="スキルのTier（0から3）", ge=0, le=3)
    last_tested: Optional[str] = Field(None, description="最後にテストされた時刻")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの分類")
    pattern: SkillPattern = Field(SkillPattern.WORKFLOW, description="スキル構造パターン")
    description: str = Field("", description="スキルの目的や説明")
    scripts: List[str] = Field(default_factory=list, description="内包するスクリプト一覧")
    references: List[str] = Field(default_factory=list, description="内包する参照資料一覧")
    assets: List[str] = Field(default_factory=list, description="内包するアセット一覧")
