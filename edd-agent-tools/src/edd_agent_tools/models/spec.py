"""
Skill Spec and Frontmatter Models for edd-agent-tools
"""

import os
import re
import yaml
from enum import StrEnum
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


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


try:
    from google.adk.skills.models import Frontmatter as AdkFrontmatter
except ImportError:
    AdkFrontmatter = BaseModel


class SkillFrontmatter(AdkFrontmatter):
    """SKILL.md の YAML Frontmatter メタデータ (Google ADK 2.0 純正モデル完全継承 & 拡張)"""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str = Field(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="スキル識別子 (ハイフンケース)")
    description: str = Field(..., max_length=1024, description="トリガー条件を明記した第三者視点の説明 (1文動詞起点 + Use when + Do NOT use)")
    license: Optional[str] = Field("Complete terms in LICENSE.txt", description="ライセンス情報")
    compatibility: Optional[str] = Field(None, description="環境・プラットフォーム互換性要件")
    allowed_tools: Optional[Union[str, List[str]]] = Field(default=None, alias="allowed-tools", description="許可されたツール一覧 (スペース区切り文字列またはリスト)")
    pattern: Optional[SkillPattern] = Field(None, description="スキルパターン（任意）")
    dependencies: List[str] = Field(default_factory=list, description="依存するスキル一覧")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="追加のメタデータ辞書")

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def _normalize_allowed_tools(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
        if isinstance(v, str):
            return v.strip()
        return v


    @field_validator("metadata")
    @classmethod
    def _validate_metadata_adk_tools(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if "adk_additional_tools" in v:
            tools = v["adk_additional_tools"]
            if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
                raise ValueError("adk_additional_tools must be a list of strings")
        return v



class SkillSpec(BaseModel):
    """パースされた SKILL.md の完全な仕様表現モデル (白書 Appendix A & Google ADK 2.0 準拠)"""
    frontmatter: SkillFrontmatter
    title: str = Field(..., description="スキルのタイトル")
    overview: str = Field(..., description="スキルの概要")
    body: str = Field(..., description="Frontmatterを除くMarkdown本文全体")
    pattern: SkillPattern = Field(SkillPattern.WORKFLOW, description="スキル構造パターン")
    when_to_use: List[str] = Field(default_factory=list, description="適用条件のリスト (When to use)")
    when_not_to_use: List[str] = Field(default_factory=list, description="非適用条件のリスト (When NOT to use)")

    # 白書 Appendix A 準拠セクションの有無
    has_when_to_use: bool = Field(False, description="When to use セクションの有無")
    has_when_not_to_use: bool = Field(False, description="When NOT to use セクションの有無")
    has_workflow: bool = Field(False, description="Workflow / Available Tasks セクションの有無")
    has_examples: bool = Field(False, description="Examples セクションの有無")
    has_output_format: bool = Field(False, description="Output format セクションの有無")
    has_anti_patterns: bool = Field(False, description="Anti-patterns to avoid セクションの有無")

    # 抽出されたリソース一覧（相対パス）
    scripts: List[str] = Field(default_factory=list, description="言及されている scripts/ 配下のファイル")
    references: List[str] = Field(default_factory=list, description="言及されている references/ 配下のファイル")
    assets: List[str] = Field(default_factory=list, description="言及されている assets/ 配下のファイル")
    examples: List[str] = Field(default_factory=list, description="言及または配置されている examples/ 配下のファイル")

    @property
    def name(self) -> str:
        return self.frontmatter.name

    @property
    def description(self) -> str:
        return self.frontmatter.description

    @property
    def dependencies(self) -> List[str]:
        return self.frontmatter.dependencies

    @property
    def word_count(self) -> int:
        """SKILL.md 本文の語数（5000語上限の判定用）"""
        return len(self.body.split())

    @property
    def capitalized_imperatives(self) -> List[str]:
        """Context Debt の要因となる大文字強制命令（ALWAYS, NEVER 等）のリスト"""
        return re.findall(r"\b(ALWAYS|NEVER|MUST NOT|SHALL NOT|DO NOT MISS)\b", self.body)

    @property
    def is_description_compliant(self) -> bool:
        """白書規約（What it does, When to use, When NOT to use）を満たしているか"""
        desc_lower = self.description.lower()
        has_use = "use when" in desc_lower or "use this" in desc_lower or "when " in desc_lower
        has_not = "do not" in desc_lower or "not for" in desc_lower or "not use" in desc_lower
        return len(self.description) <= 1024 and has_use and has_not

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

        # 白書 Appendix A 準拠セクションの検出
        has_when_to = bool(re.search(r"^##\s+(When to [uU]se|Usage Scenarios)", body_str, re.MULTILINE))
        has_when_not = bool(re.search(r"^##\s+When NOT to [uU]se", body_str, re.MULTILINE))
        has_wf = bool(re.search(r"^##\s+(Workflow|Available Tasks|Quick Start|Core Capabilities|Guidelines)", body_str, re.MULTILINE))
        has_ex = bool(re.search(r"^##\s+Examples?", body_str, re.MULTILINE))
        has_out = bool(re.search(r"^##\s+Output [fF]ormat", body_str, re.MULTILINE))
        has_anti = bool(re.search(r"^##\s+Anti-patterns", body_str, re.MULTILINE))

        # When to use の抽出
        when_to_use = []
        when_to_match = re.search(r"##\s+(?:When to [uU]se|Usage Scenarios)[^\n]*\s*\n+(.*?)(?=\n##|\Z)", body_str, re.DOTALL | re.IGNORECASE)
        if when_to_match:
            for line in when_to_match.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith(("-", "*")):
                    when_to_use.append(line.lstrip("-* ").strip())

        # When NOT to use の抽出
        when_not_to_use = []
        when_not_match = re.search(r"##\s+When NOT to [uU]se[^\n]*\s*\n+(.*?)(?=\n##|\Z)", body_str, re.DOTALL | re.IGNORECASE)
        if when_not_match:
            for line in when_not_match.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith(("-", "*")):
                    when_not_to_use.append(line.lstrip("-* ").strip())

        # リソース言及の抽出 (scripts/..., references/..., assets/..., examples/...)
        scripts = sorted(list(set(re.findall(r"`?scripts/([a-zA-Z0-9_\-\./]+)`?", body_str))))
        references = sorted(list(set(re.findall(r"`?references/([a-zA-Z0-9_\-\./]+)`?", body_str))))
        assets = sorted(list(set(re.findall(r"`?assets/([a-zA-Z0-9_\-\./]+)`?", body_str))))
        examples = sorted(list(set(re.findall(r"`?examples/([a-zA-Z0-9_\-\./]+)`?", body_str))))

        return cls(
            frontmatter=frontmatter,
            title=title,
            overview=overview,
            body=body_str,
            pattern=pattern,
            when_to_use=when_to_use,
            when_not_to_use=when_not_to_use,
            has_when_to_use=has_when_to,
            has_when_not_to_use=has_when_not,
            has_workflow=has_wf,
            has_examples=has_ex,
            has_output_format=has_out,
            has_anti_patterns=has_anti,
            scripts=scripts,
            references=references,
            assets=assets,
            examples=examples
        )

    @classmethod
    def load_from_file(cls, filepath: str | Path) -> "SkillSpec":
        """SKILL.md ファイルから直接仕様をロードします。"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"SKILL.md not found at: {path}")
        return cls.parse_markdown(path.read_text(encoding="utf-8"))

    def to_adk_skill(self, skill_dir: Optional[str | Path] = None) -> Any:
        """google.adk.skills.models.Skill オブジェクトへ変換します。
        
        指定されたディレクトリが存在する場合は、Google ADK 2.0 公式の
        load_skill_from_dir を優先使用し、車輪の再発明を排除します。
        """
        try:
            from google.adk.skills import load_skill_from_dir
            from google.adk.skills import models as adk_models
        except ImportError:
            raise ImportError("google.adk is not installed.")

        # ディレクトリが存在し、SKILL.md がある場合は ADK 公式ローダーを最優先
        if skill_dir:
            dir_path = Path(skill_dir).resolve()
            if dir_path.is_dir() and (dir_path / "SKILL.md").exists():
                try:
                    # ディレクトリ名と Frontmatter 名が合致する場合は公式ローダーをそのまま利用
                    loaded = load_skill_from_dir(dir_path)
                    if self.pattern and "pattern" not in loaded.frontmatter.metadata:
                        loaded.frontmatter.metadata["pattern"] = str(self.pattern.value if hasattr(self.pattern, "value") else self.pattern)
                    if self.frontmatter.dependencies and "dependencies" not in loaded.frontmatter.metadata:
                        loaded.frontmatter.metadata["dependencies"] = self.frontmatter.dependencies
                    return loaded
                except Exception:
                    pass

        # メモリ上からの安全な合成フォールバック
        meta = dict(self.frontmatter.metadata or {})
        meta["pattern"] = str(self.pattern.value if hasattr(self.pattern, "value") else self.pattern)
        if self.frontmatter.dependencies:
            meta["dependencies"] = self.frontmatter.dependencies

        allowed_tools_val = None
        if self.frontmatter.allowed_tools is not None:
            if isinstance(self.frontmatter.allowed_tools, list):
                allowed_tools_val = " ".join(self.frontmatter.allowed_tools)
            else:
                allowed_tools_val = str(self.frontmatter.allowed_tools)

        adk_fm = adk_models.Frontmatter(
            name=self.frontmatter.name,
            description=self.frontmatter.description,
            license=self.frontmatter.license or "Complete terms in LICENSE.txt",
            compatibility=self.frontmatter.compatibility,
            allowed_tools=allowed_tools_val,
            metadata=meta
        )

        references = {}
        assets = {}
        scripts = {}

        if skill_dir:
            dir_path = Path(skill_dir).resolve()
            ref_dir = dir_path / "references"
            if ref_dir.exists():
                for f in ref_dir.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(ref_dir))
                        try:
                            references[rel] = f.read_text(encoding="utf-8")
                        except Exception:
                            references[rel] = ""

            ex_dir = dir_path / "examples"
            if ex_dir.exists():
                for f in ex_dir.rglob("*"):
                    if f.is_file():
                        rel = f"examples/{f.relative_to(ex_dir)}"
                        try:
                            references[rel] = f.read_text(encoding="utf-8")
                        except Exception:
                            references[rel] = ""

            asset_dir = dir_path / "assets"
            if asset_dir.exists():
                for f in asset_dir.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(asset_dir))
                        try:
                            assets[rel] = f.read_text(encoding="utf-8")
                        except Exception:
                            assets[rel] = ""

            scripts_dir = dir_path / "scripts"
            if scripts_dir.exists():
                for f in scripts_dir.rglob("*.py"):
                    if f.is_file():
                        rel = str(f.relative_to(scripts_dir))
                        try:
                            scripts[rel] = adk_models.Script(src=f.read_text(encoding="utf-8"))
                        except Exception:
                            scripts[rel] = adk_models.Script(src="")

        adk_resources = adk_models.Resources(
            references=references,
            assets=assets,
            scripts=scripts
        )

        return adk_models.Skill(
            frontmatter=adk_fm,
            instructions=self.body,
            resources=adk_resources
        )

    @classmethod
    def from_adk_skill(cls, skill: Any) -> "SkillSpec":
        """google.adk.skills.models.Skill オブジェクトから SkillSpec を生成します。"""
        fm = skill.frontmatter
        metadata = getattr(fm, "metadata", {}) or {}
        pattern_val = metadata.get("pattern", "workflow") if isinstance(metadata, dict) else "workflow"
        deps = metadata.get("dependencies", []) if isinstance(metadata, dict) else []
        try:
            pat = SkillPattern(pattern_val)
        except ValueError:
            pat = SkillPattern.WORKFLOW

        frontmatter = SkillFrontmatter(
            name=fm.name,
            description=fm.description,
            license=getattr(fm, "license", "Complete terms in LICENSE.txt"),
            compatibility=getattr(fm, "compatibility", None),
            allowed_tools=getattr(fm, "allowed_tools", None),
            pattern=pat,
            dependencies=deps,
            metadata=metadata if isinstance(metadata, dict) else {}
        )

        body_str = skill.instructions or ""
        title_match = re.search(r"^#\s+(.+)$", body_str, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else fm.name

        overview_match = re.search(r"##\s+Overview\s*\n+(.*?)(?=\n##|\Z)", body_str, re.DOTALL | re.IGNORECASE)
        overview = overview_match.group(1).strip() if overview_match else ""

        when_not_match = re.search(r"##\s+When NOT to Use[^\n]*\s*\n+(.*?)(?=\n##|\Z)", body_str, re.DOTALL | re.IGNORECASE)
        when_not_to_use = []
        if when_not_match:
            when_not_text = when_not_match.group(1).strip()
            for line in when_not_text.splitlines():
                line = line.strip()
                if line.startswith(("-", "*")):
                    when_not_to_use.append(line.lstrip("-* ").strip())

        scripts = list(skill.resources.scripts.keys()) if hasattr(skill.resources, "scripts") else []
        all_refs = list(skill.resources.references.keys()) if hasattr(skill.resources, "references") else []
        references = [r for r in all_refs if not r.startswith("examples/")]
        examples = [r.replace("examples/", "") for r in all_refs if r.startswith("examples/")]
        assets = list(skill.resources.assets.keys()) if hasattr(skill.resources, "assets") else []

        return cls(
            frontmatter=frontmatter,
            title=title,
            overview=overview,
            body=body_str,
            pattern=pat,
            when_not_to_use=when_not_to_use,
            scripts=scripts,
            references=references,
            assets=assets,
            examples=examples
        )


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
    examples: List[str] = Field(default_factory=list, description="内包する使用例一覧")
