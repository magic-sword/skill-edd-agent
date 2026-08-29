import os
import re
from pathlib import Path
from typing import NamedTuple
from pydantic import BaseModel, Field
import yaml
from .models import SkillSpec, SkillPattern

class ValidationIssue(BaseModel):
    category: str = Field(..., description="エラーまたは警告のカテゴリ (frontmatter, structure, resources, tone)")
    severity: str = Field(..., description="'error' または 'warning'")
    message: str = Field(..., description="具体的な問題点の説明")
    line_number: int | None = Field(None, description="発生行番号（特定可能な場合）")


class ValidationResult(BaseModel):
    """スキルの静的検証結果オブジェクト"""
    skill_name: str
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)

    def add_error(self, category: str, message: str, line_number: int | None = None):
        self.is_valid = False
        self.errors.append(f"[{category.upper()}] {message}")
        self.issues.append(ValidationIssue(category=category, severity="error", message=message, line_number=line_number))

    def add_warning(self, category: str, message: str, line_number: int | None = None):
        self.warnings.append(f"[{category.upper()}] {message}")
        self.issues.append(ValidationIssue(category=category, severity="warning", message=message, line_number=line_number))


class SkillValidator:
    """SKILL.md およびスキルディレクトリ構造の静的バリデータ"""

    @classmethod
    def validate_directory(cls, skill_dir: str | Path) -> ValidationResult:
        """スキルディレクトリ全体（SKILL.md + リソース）を静的検証します。"""
        skill_path = Path(skill_dir).resolve()
        skill_name = skill_path.name
        res = ValidationResult(skill_name=skill_name, is_valid=True)

        if not skill_path.exists() or not skill_path.is_dir():
            res.add_error("directory", f"Skill directory does not exist: {skill_path}")
            return res

        skill_md_path = skill_path / "SKILL.md"
        if not skill_md_path.exists():
            res.add_error("structure", f"Missing required 'SKILL.md' at: {skill_md_path}")
            return res

        content = skill_md_path.read_text(encoding="utf-8")
        return cls.validate_content(content, skill_dir=skill_path)

    @classmethod
    def validate_content(cls, content: str, skill_dir: Path | None = None) -> ValidationResult:
        """SKILL.md のテキスト内容を静的検証します。"""
        skill_name = skill_dir.name if skill_dir else "unknown"
        res = ValidationResult(skill_name=skill_name, is_valid=True)

        # 1. Frontmatter 境界チェック
        if not content.startswith("---"):
            res.add_error("frontmatter", "Missing YAML frontmatter start marker ('---')")
            return res

        match = re.match(r"^---\n(.*?)\n---\n*(.*)$", content, re.DOTALL)
        if not match:
            res.add_error("frontmatter", "Invalid YAML frontmatter boundary format (must start and end with '---')")
            return res

        fm_str = match.group(1)
        body_str = match.group(2)

        # 2. YAML パース検証
        try:
            fm = yaml.safe_load(fm_str)
            if not isinstance(fm, dict):
                res.add_error("frontmatter", "YAML frontmatter must be a key-value mapping")
                return res
        except Exception as e:
            res.add_error("frontmatter", f"YAML parsing error in frontmatter: {e}")
            return res

        # 3. 必須フィールド検証
        name = fm.get("name")
        if not name:
            res.add_error("frontmatter", "Missing required 'name' field in frontmatter")
        else:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                res.add_error("frontmatter", f"Name '{name}' must be lowercase hyphen-case (e.g. 'data-analyzer') without consecutive hyphens")
            if skill_dir and skill_dir.name != name:
                res.add_warning("frontmatter", f"Directory name '{skill_dir.name}' does not match skill name '{name}'")

        desc = fm.get("description")
        if not desc:
            res.add_error("frontmatter", "Missing required 'description' field in frontmatter")
        else:
            if "<" in desc or ">" in desc:
                res.add_error("frontmatter", "Description cannot contain angle brackets ('<' or '>')")
            if len(desc) > 500:
                res.add_warning("frontmatter", f"Description is overly long ({len(desc)} chars). Keep under 500 chars / ~100 words.")

        deps = fm.get("dependencies")
        if deps is not None:
            if not isinstance(deps, list):
                res.add_error("frontmatter", "'dependencies' in frontmatter must be a list of skill names")
            else:
                for dep in deps:
                    if not isinstance(dep, str) or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", dep):
                        res.add_error("frontmatter", f"Invalid dependency name '{dep}': must be lowercase hyphen-case")

        # 4. 見出し構造検証
        if not re.search(r"^#\s+", body_str, re.MULTILINE):
            res.add_error("structure", "Missing level-1 title heading ('# <Title>')")
        if not re.search(r"^##\s+Overview", body_str, re.MULTILINE | re.IGNORECASE):
            res.add_warning("structure", "Recommended '## Overview' section is missing")

        # 5. リソース参照の整合性検証 (実在チェック)
        if skill_dir:
            referenced_scripts = re.findall(r"`?scripts/([a-zA-Z0-9_\-\./]+)`?", body_str)
            for s in referenced_scripts:
                target = skill_dir / "scripts" / s
                if not target.exists():
                    res.add_error("resources", f"Referenced script does not exist on disk: scripts/{s}")

            referenced_refs = re.findall(r"`?references/([a-zA-Z0-9_\-\./]+)`?", body_str)
            for r in referenced_refs:
                target = skill_dir / "references" / r
                if not target.exists():
                    res.add_error("resources", f"Referenced documentation does not exist on disk: references/{r}")

            referenced_assets = re.findall(r"`?assets/([a-zA-Z0-9_\-\./]+)`?", body_str)
            for a in referenced_assets:
                target = skill_dir / "assets" / a
                if not target.exists():
                    res.add_error("resources", f"Referenced asset does not exist on disk: assets/{a}")

        # 6. 文体・トーン検証 (Imperative / 客観的指示)
        # 会話調・冗長指示の検知
        non_imperative_patterns = [
            (r"〜してください", "Avoid conversational '〜してください'. Use imperative form (e.g. '〜を実行する')."),
            (r"必要があります", "Avoid passive '必要があります'. State direct actions."),
            (r"\bYou should\b", "Avoid second-person 'You should'. Use verb-first instructions (e.g. 'To do X, execute Y')."),
            (r"\bPlease\b", "Avoid polite requests 'Please'. Use objective command form.")
        ]

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            for pattern, msg in non_imperative_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    res.add_warning("tone", f"Line {idx}: {msg}")

        return res
