import os
import re
import ast
from pathlib import Path
from typing import NamedTuple
from pydantic import BaseModel, Field
import yaml
from .models import SkillSpec, SkillPattern

class ValidationIssue(BaseModel):
    category: str = Field(..., description="エラーまたは警告のカテゴリ (frontmatter, structure, resources, tone, cli)")
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
        """スキルディレクトリ全体（SKILL.md + リソース + CLIハーネス）を静的検証します。"""
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
        base_res = cls.validate_content(content, skill_dir=skill_path)

        # 7. ディレクトリの整合性および不要空ディレクトリ検証
        cls._validate_directory_cleanliness(skill_path, base_res)

        # 8. Python スクリプトの CLI / Black-box Tooling ハーネス検証 (AST静的解析)
        cls._validate_python_scripts_harness(skill_path, base_res)

        return base_res

    @classmethod
    def _validate_directory_cleanliness(cls, skill_dir: Path, res: ValidationResult) -> None:
        """空ディレクトリの残存を検知します。"""
        for item in skill_dir.iterdir():
            if item.is_dir() and item.name not in ["__pycache__", ".pytest_cache"]:
                # ディレクトリ配下に何かしらのファイルが存在するか確認
                files = [f for f in item.rglob("*") if f.is_file() and not f.name.endswith((".pyc", ".gitkeep"))]
                if not files:
                    res.add_warning("structure", f"Empty resource directory detected: '{item.name}/'. Unused directories should be removed to reduce context noise.")

    @classmethod
    def _validate_python_scripts_harness(cls, skill_dir: Path, res: ValidationResult) -> None:
        """scripts/ 配下の Python スクリプトが決定論的 CLI ツールとして実装されているかを AST 解析で検証します。"""
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return

        for py_file in scripts_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            except SyntaxError as e:
                res.add_error("cli", f"Syntax error in script '{py_file.name}': {e}", line_number=e.lineno)
                continue

            has_main_block = False
            has_argparse_or_cli = False

            for node in ast.walk(tree):
                # if __name__ == '__main__': のチェック
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        # __name__ == '__main__' または '__main__' == __name__
                        left_name = getattr(node.test.left, "id", None)
                        for comparator in node.test.comparators:
                            if isinstance(comparator, ast.Constant) and comparator.value == "__main__" and left_name == "__name__":
                                has_main_block = True
                            elif isinstance(comparator, ast.Name) and comparator.id == "__name__" and isinstance(node.test.left, ast.Constant) and node.test.left.value == "__main__":
                                has_main_block = True

                # import argparse / sys.argv / click / typer のチェック
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name for alias in node.names]
                    module_name = getattr(node, "module", "") or ""
                    if "argparse" in names or module_name == "argparse" or "click" in names or "typer" in names or "sys" in names:
                        has_argparse_or_cli = True

            if not has_main_block:
                res.add_warning("cli", f"Script 'scripts/{py_file.name}' lacks 'if __name__ == \"__main__\":' block. Deterministic scripts should be directly executable via CLI.")

            if not has_argparse_or_cli:
                res.add_warning("cli", f"Script 'scripts/{py_file.name}' does not import 'argparse' or CLI parser. Scripts should support --help and CLI arguments.")

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

        # 3. 必須フィールド検証 (ADK 2.0 / Agent Skills Specification 準拠)
        name = fm.get("name")
        if not name:
            res.add_error("frontmatter", "Missing required 'name' field in frontmatter")
        else:
            if not isinstance(name, str) or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                res.add_error("frontmatter", f"Name '{name}' must be lowercase hyphen-case (e.g. 'data-analyzer') without consecutive hyphens")
            if len(name) > 64:
                res.add_error("frontmatter", f"Name '{name}' exceeds ADK 2.0 maximum length of 64 characters ({len(name)} chars)")
            if skill_dir and skill_dir.name != name:
                res.add_warning("frontmatter", f"Directory name '{skill_dir.name}' does not match skill name '{name}'")

        desc = fm.get("description")
        if not desc:
            res.add_error("frontmatter", "Missing required 'description' field in frontmatter")
        else:
            if not isinstance(desc, str) or len(desc.strip()) == 0:
                res.add_error("frontmatter", "Description must be a non-empty string")
            else:
                if "<" in desc or ">" in desc:
                    res.add_error("frontmatter", "Description cannot contain angle brackets ('<' or '>')")
                if len(desc) > 1024:
                    res.add_error("frontmatter", f"Description exceeds ADK 2.0 maximum length of 1024 characters ({len(desc)} chars)")
                elif len(desc) > 500:
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
        if not re.search(r"^##\s+When NOT to Use", body_str, re.MULTILINE | re.IGNORECASE):
            res.add_warning("structure", "Recommended '## When NOT to Use This Skill' section is missing. Specifying exclusion criteria prevents model over-triggering.")

        # 5. リソース参照の整合性検証 (実在チェック)
        if skill_dir:
            referenced_scripts = [s.rstrip(".,;:)[]`'\"") for s in re.findall(r"`?scripts/([a-zA-Z0-9_\-\./]+)", body_str)]
            for s in referenced_scripts:
                if not s:
                    continue
                target = skill_dir / "scripts" / s
                if not target.exists():
                    res.add_error("resources", f"Referenced script does not exist on disk: scripts/{s}")

            referenced_refs = [r.rstrip(".,;:)[]`'\"") for r in re.findall(r"`?references/([a-zA-Z0-9_\-\./]+)", body_str)]
            for r in referenced_refs:
                if not r:
                    continue
                target = skill_dir / "references" / r
                if not target.exists():
                    res.add_error("resources", f"Referenced documentation does not exist on disk: references/{r}")

            referenced_assets = [a.rstrip(".,;:)[]`'\"") for a in re.findall(r"`?assets/([a-zA-Z0-9_\-\./]+)", body_str)]
            for a in referenced_assets:
                if not a:
                    continue
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
