import os
import re
import json
from enum import StrEnum, IntEnum
from pathlib import Path
from typing import Literal, Union, Any, Optional
import yaml
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

# ==========================================
# 1. 状態・品質管理用モデル (skills_state.json 用)
# ==========================================

class SkillTier(IntEnum):
    """スキルのセキュリティ・権限階層を定義する列挙型"""
    SANDBOX = 0          # 暫定 / 新規スキルのテスト用
    READ_ONLY = 1        # Read-Only: ファイルの読み込みのみ許可
    DRAFT_ONLY = 2       # Draft-Only: 提案ファイルの作成のみ許可
    ACTION_ALLOWED = 3   # Action-Allowed: すべての実アクションを許可


class SkillEntry(BaseModel):
    """スキルまたはエージェントのディレクトリパス"""
    path: Path = Field(..., description="カスタムスキルフォルダへのパス")
    name: str | None = Field(None, description="探索エントリの論理名（別名）")


class InheritEntry(BaseModel):
    """継承元のマニフェスト定義ファイルパス"""
    path: Path = Field(..., description="継承元の共通マニフェストファイルへのパス")


class ProjectSkillInfo(BaseModel):
    """skills_state.json で管理される各スキル/エージェントのプロジェクト品質メタデータ"""
    tier: SkillTier = Field(SkillTier.SANDBOX, description="スキルの権限階層")


class SkillsStateJson(BaseModel):
    """ADK公式仕様に準拠した、3つの基本フィールドを持つ skills_state.json 用の基本スキーマモデル。"""
    entries: list[SkillEntry] = Field(..., description="スキル探索対象のパスリスト")
    inherits: list[InheritEntry] = Field(default_factory=list, description="継承元設定ファイルのリスト")
    exclude: list[str] = Field(default_factory=list, description="除外するスキル名のリスト")

    skills: dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各スキルの品質ステータス情報")
    agents: dict[str, ProjectSkillInfo] = Field(default_factory=dict, description="登録されている各自律エージェントの品質ステータス情報")


# ==========================================
# 2. Markdown-First & Progressive Disclosure 設計モデル
# ==========================================

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


class DecisionBranch(BaseModel):
    """意思決定ツリーの分岐ルール"""
    condition: str = Field(..., description="分岐条件 (例: 入力ファイルがPDF形式の場合)")
    action: str = Field(..., description="実行するアクションまたは参照先 (例: scripts/rotate_pdf.py を実行)")


class StepInstruction(BaseModel):
    """動詞起点 (Imperative) の実行手順"""
    step_number: int = Field(..., description="ステップ番号 (1始まり)")
    title: str = Field(..., description="ステップの見出し (動詞起点)")
    action_imperative: str = Field(..., description="具体的な手順指示 (To do X, execute Y 形式)")
    target_resource: str | None = Field(None, description="使用するスクリプトまたは参照資料の相対パス")


class ResourcePlan(BaseModel):
    """3層リソース (scripts, references, assets) の計画定義"""
    rel_path: str = Field(..., description="ファイル相対パス (例: scripts/convert.py, references/schema.md)")
    type: Literal["script", "reference", "asset"] = Field(..., description="リソース種別")
    purpose: str = Field(..., description="このリソースが果たす役割と内容")


class SkillLogicDraft(BaseModel):
    """Stage 1: LLMが要件から抽出する論理設計データモデル。
    
    Markdownのレイアウトに依存せず、設計の骨子（認知的知識、決定木、リソース計画）のみを型安全に抽出します。
    """
    name: str = Field(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="ハイフンケースのスキル名 (例: pdf-tools, api-helper)")
    pattern: SkillPattern = Field(..., description="4パターンのいずれか")
    description_third_person: str = Field(..., max_length=500, description="第三者視点でのトリガー説明 ('This skill should be used when...')")
    concrete_trigger_examples: list[str] = Field(..., min_length=2, max_length=6, description="具体的なユーザー発話・トリガー例")
    overview_summary: str = Field(..., description="スキルの目的・提供価値の簡潔な要約 (1〜2文)")
    decision_tree: list[DecisionBranch] = Field(default_factory=list, description="条件分岐ルール")
    execution_steps: list[StepInstruction] = Field(..., min_length=1, description="動詞起点の実行手順リスト")
    dependencies: list[str] = Field(default_factory=list, description="依存する他のスキル名のリスト")
    resources_plan: list[ResourcePlan] = Field(default_factory=list, description="3層リソースの計画一覧")
    guidelines: list[str] = Field(default_factory=list, description="実行時の注意点・ベストプラクティス")


# ==========================================
# 3. SKILL.md 仕様モデル (SkillSpec)
# ==========================================

class SkillFrontmatter(BaseModel):
    """SKILL.md の YAML Frontmatter メタデータ"""
    name: str = Field(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="スキル識別子 (ハイフンケース)")
    description: str = Field(..., max_length=500, description="トリガー条件を明記した第三者視点の説明")
    license: str | None = Field("Complete terms in LICENSE.txt", description="ライセンス情報")
    pattern: SkillPattern | None = Field(None, description="スキルパターン（任意）")
    dependencies: list[str] = Field(default_factory=list, description="依存するスキル一覧")


class SkillSpec(BaseModel):
    """パースされた SKILL.md の完全な仕様表現モデル"""
    frontmatter: SkillFrontmatter
    title: str = Field(..., description="スキルのタイトル")
    overview: str = Field(..., description="スキルの概要")
    body: str = Field(..., description="Frontmatterを除くMarkdown本文全体")
    pattern: SkillPattern = Field(SkillPattern.WORKFLOW, description="スキル構造パターン")
    
    # 抽出されたリソース一覧（相対パス）
    scripts: list[str] = Field(default_factory=list, description="言及されている scripts/ 配下のファイル")
    references: list[str] = Field(default_factory=list, description="言及されている references/ 配下のファイル")
    assets: list[str] = Field(default_factory=list, description="言及されている assets/ 配下のファイル")

    @property
    def name(self) -> str:
        return self.frontmatter.name

    @property
    def description(self) -> str:
        return self.frontmatter.description

    @property
    def dependencies(self) -> list[str]:
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
            scripts=scripts,
            references=references,
            assets=assets
        )

    @classmethod
    def load_from_file(cls, filepath: str) -> "SkillSpec":
        """SKILL.md ファイルから直接仕様をロードします。"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"SKILL.md not found at: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.parse_markdown(f.read())


class SkillMetadata(BaseModel):
    """レジストリ情報と仕様情報をマージした統合メタデータ"""
    name: str = Field(..., description="スキル名")
    tier: int = Field(0, description="スキルのTier（0から3）", ge=0, le=3)
    last_tested: str | None = Field(None, description="最後にテストされた時刻")
    module_type: ModuleType = Field(ModuleType.SKILL, description="モジュールの分類")
    pattern: SkillPattern = Field(SkillPattern.WORKFLOW, description="スキル構造パターン")
    description: str = Field("", description="スキルの目的や説明")
    scripts: list[str] = Field(default_factory=list, description="内包するスクリプト一覧")
    references: list[str] = Field(default_factory=list, description="内包する参照資料一覧")
    assets: list[str] = Field(default_factory=list, description="内包するアセット一覧")
