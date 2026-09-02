"""
Unified Skill Validator for edd-agent-tools

Anthropic Markdown-First & Google ADK 2.0 準拠の静的バリデータ。
AST解析による Python スクリプト検証、Frontmatter 構文検査、3層リソース整合性検査を提供します。
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
import yaml

from ..models.spec import SkillSpec, SkillPattern


class ValidationIssue(BaseModel):
    category: str = Field(..., description="エラーまたは警告のカテゴリ (frontmatter, structure, resources, tone, cli)")
    severity: str = Field(..., description="'error' または 'warning'")
    message: str = Field(..., description="具体的な問題点の説明")
    line_number: Optional[int] = Field(None, description="発生行番号（特定可能な場合）")


class ValidationResult(BaseModel):
    """スキルの静的検証結果オブジェクト"""
    skill_name: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    issues: List[ValidationIssue] = Field(default_factory=list)

    def add_error(self, category: str, message: str, line_number: Optional[int] = None):
        self.is_valid = False
        self.errors.append(f"[{category.upper()}] {message}")
        self.issues.append(ValidationIssue(category=category, severity="error", message=message, line_number=line_number))

    def add_warning(self, category: str, message: str, line_number: Optional[int] = None):
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

        # ディレクトリの整合性および不要空ディレクトリ検証
        cls._validate_directory_cleanliness(skill_path, base_res)

        # Python スクリプトの CLI / Black-box Tooling ハーネス検証 (AST静的解析)
        # Python スクリプトの CLI / Black-box Tooling ハーネス検証 (AST静的解析)
        cls._validate_python_scripts_harness(skill_path, base_res)

        # 外部依存ライブラリ (Requirements & Prerequisites) の照合検証
        cls._validate_prerequisites_and_imports(skill_path, content, base_res)

        return base_res

    @classmethod
    def _validate_directory_cleanliness(cls, skill_dir: Path, res: ValidationResult) -> None:
        """空ディレクトリの残存を検知します。"""
        for item in skill_dir.iterdir():
            if item.is_dir() and item.name not in ["__pycache__", ".pytest_cache"]:
                files = [f for f in item.rglob("*") if f.is_file() and not f.name.endswith((".pyc", ".gitkeep"))]
                if not files:
                    res.add_warning("structure", f"Empty resource directory detected: '{item.name}/'. Unused directories should be removed to reduce context noise.")

    @classmethod
    def _validate_prerequisites_and_imports(cls, skill_dir: Path, skill_md_content: str, res: ValidationResult) -> None:
        """scripts/ 配下の Python スクリプトがインポートする外部ライブラリが SKILL.md に記載されているかを検証します。"""
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return

        stdlib = getattr(sys, "stdlib_module_names", set())
        # 既知のローカルまたは共通モジュール除外
        ignored_modules = {"edd_agent_tools", skill_dir.name.replace("-", "_")}

        imported_external_pkgs = set()

        for py_file in scripts_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0]
                        if top_pkg not in stdlib and top_pkg not in ignored_modules:
                            imported_external_pkgs.add((top_pkg, py_file.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_pkg = node.module.split(".")[0]
                        if top_pkg not in stdlib and top_pkg not in ignored_modules:
                            imported_external_pkgs.add((top_pkg, py_file.name))

        if not imported_external_pkgs:
            return

        # SKILL.md 本文の Requirements & Prerequisites セクションを抽出
        req_match = re.search(r"##\s+(?:Requirements\s+&\s+Prerequisites|Prerequisites|Requirements)(.*?)(?=##|\Z)", skill_md_content, re.DOTALL | re.IGNORECASE)
        req_text = req_match.group(1).lower() if req_match else ""

        for pkg, script_name in imported_external_pkgs:
            # 白書 Don't: Reinvent MCP as scripts の検知
            if pkg in ["requests", "httpx", "aiohttp", "urllib3"]:
                res.add_warning(
                    "anti_pattern",
                    f"Script '{script_name}' imports network HTTP client '{pkg}'. Remember: 'Don't reinvent MCP as scripts' (Whitepaper Appendix A). Skills are for procedural know-how; external API integrations should be handled via MCP tools."
                )

            # パッケージ名（小文字やアンダースコア・ハイフン違い）が含まれているか照合
            pkg_clean = pkg.lower().replace("_", "-")
            pkg_raw = pkg.lower()
            if not req_text or (pkg_clean not in req_text and pkg_raw not in req_text):
                res.add_warning(
                    "prerequisites",
                    f"Script '{script_name}' imports external package '{pkg}', but it is not documented in SKILL.md under 'Requirements & Prerequisites'."
                )

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
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        left_name = getattr(node.test.left, "id", None)
                        if left_name == "__name__":
                            for comp in node.test.comparators:
                                if isinstance(comp, ast.Constant) and comp.value == "__main__":
                                    has_main_block = True
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ["argparse", "sys", "click"]:
                            has_argparse_or_cli = True
                if isinstance(node, ast.ImportFrom):
                    if node.module in ["argparse", "sys", "click"]:
                        has_argparse_or_cli = True

            if not has_main_block:
                res.add_warning("cli", f"Script '{py_file.name}' is missing an 'if __name__ == \"__main__\":' block for standalone execution.")
            if not has_argparse_or_cli:
                res.add_warning("cli", f"Script '{py_file.name}' does not appear to use argparse/sys/click for CLI arguments.")

    @classmethod
    def validate_content(cls, content: str, skill_dir: Optional[Path] = None) -> ValidationResult:
        """SKILL.md の文字列コンテンツを静的検証します。"""
        res = ValidationResult(skill_name="unknown", is_valid=True)
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # 1. YAML Frontmatter の存在検査
        if not content.startswith("---"):
            res.add_error("frontmatter", "Missing YAML frontmatter start marker ('---') at line 1", line_number=1)
            return res

        match = re.match(r"^---\n(.*?)\n---\n*(.*)$", content, re.DOTALL)
        if not match:
            res.add_error("frontmatter", "Invalid YAML frontmatter boundary format")
            return res

        fm_str = match.group(1)
        body_str = match.group(2)

        try:
            fm = yaml.safe_load(fm_str)
            if not isinstance(fm, dict):
                res.add_error("frontmatter", "YAML frontmatter is not a key-value mapping")
                return res
        except Exception as e:
            res.add_error("frontmatter", f"Failed to parse YAML frontmatter: {e}")
            return res

        # 2. 必須フィールド (name, description) の検査
        name = fm.get("name")
        if not name or not isinstance(name, str):
            res.add_error("frontmatter", "Missing required field 'name' in YAML frontmatter")
        else:
            res.skill_name = name
            if "--" in name:
                res.add_error("frontmatter", f"Skill name '{name}' must not contain consecutive hyphens ('--')")
            elif not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
                res.add_error("frontmatter", f"Skill name '{name}' must be hyphen-case (lowercase letters, digits, single hyphens)")
            if len(name) > 64:
                res.add_error("frontmatter", f"Skill name '{name}' exceeds ADK 2.0 limit of 64 characters ({len(name)} chars)")
            if any(name.startswith(p) for p in ["claude-", "gemini-", "anthropic-", "google-"]):
                res.add_warning("frontmatter", f"Skill name '{name}' contains vendor prefix. Best practice is vendor-neutral naming (e.g., 'converting-case' rather than 'gemini-case-converter').")
            if name in ["utils", "tools", "helper", "data", "misc"]:
                res.add_warning("frontmatter", f"Skill name '{name}' is too generic. Use specific domain naming (e.g. 'processing-pdfs').")
            if skill_dir and skill_dir.name != name:
                res.add_warning("frontmatter", f"Directory name '{skill_dir.name}' does not match skill name '{name}'")

        desc = fm.get("description")
        if not desc or not isinstance(desc, str):
            res.add_error("frontmatter", "Missing required field 'description' in YAML frontmatter")
        else:
            if "<" in desc or ">" in desc:
                res.add_error("frontmatter", "Description must not contain angle brackets ('<' or '>')")
            if len(desc) > 1024:
                res.add_error("frontmatter", f"Description exceeds ADK 2.0 limit of 1024 characters ({len(desc)} chars)")
            elif len(desc) > 500:
                res.add_warning("frontmatter", f"Description is relatively long ({len(desc)} chars). Recommended: <500 chars (~50-100 words)")
            
            # ルーティングアルゴリズムとしての品質検査 (Agent Skills 白書 & Anthropic/ADK 標準)
            desc_lower = desc.lower()
            if desc_lower.startswith("a helpful skill") or desc_lower.startswith("helps with"):
                res.add_warning("frontmatter", "Description should be verb-led (e.g., 'Converts...', 'Generates...') and front-load trigger keywords instead of vague phrases like 'helps with'.")
            
            if "when" not in desc_lower and "use" not in desc_lower:
                res.add_warning("frontmatter", "Description should include clear trigger conditions (e.g., 'Use when the user asks to...').")

            if "do not" not in desc_lower and "not use" not in desc_lower and "not for" not in desc_lower:
                res.add_warning("frontmatter", "Description should include a 'Do NOT use for...' clause to prevent over-triggering and boundary confusion.")

        # 3. Context Rot (コンテキスト腐敗) 対策: SKILL.md 本文のサイズ検査
        word_count = len(body_str.split())
        if word_count > 5000:
            res.add_warning("context_rot", f"SKILL.md body exceeds 5,000 words ({word_count} words). Move detailed reference material to references/ to avoid context rot.")
        elif len(body_str) > 15000:
            res.add_warning("context_rot", f"SKILL.md body is very large ({len(body_str)} chars). Consider progressive disclosure by moving detailed documentation to references/.")

        # 4. リソース実在参照の検証
        if skill_dir and skill_dir.exists():
            scripts = sorted(list(set(re.findall(r"`?scripts/([a-zA-Z0-9_\-\./]+)", body_str))))
            for s in scripts:
                clean_s = s.rstrip(".,;:)[]`'\"")
                if clean_s and not (skill_dir / "scripts" / clean_s).exists():
                    res.add_error("resources", f"Referenced script does not exist: scripts/{clean_s}")

            refs = sorted(list(set(re.findall(r"`?references/([a-zA-Z0-9_\-\./]+)", body_str))))
            for r in refs:
                clean_r = r.rstrip(".,;:)[]`'\"")
                if clean_r and not (skill_dir / "references" / clean_r).exists():
                    res.add_error("resources", f"Referenced documentation does not exist: references/{clean_r}")

            assets = sorted(list(set(re.findall(r"`?assets/([a-zA-Z0-9_\-\./]+)", body_str))))
            for a in assets:
                clean_a = a.rstrip(".,;:)[]`'\"")
                if clean_a and not (skill_dir / "assets" / clean_a).exists():
                    res.add_error("resources", f"Referenced asset does not exist: assets/{clean_a}")

            examples = sorted(list(set(re.findall(r"`?examples/([a-zA-Z0-9_\-\./]+)", body_str))))
            for e in examples:
                clean_e = e.rstrip(".,;:)[]`'\"")
                if clean_e and not (skill_dir / "examples" / clean_e).exists():
                    res.add_error("resources", f"Referenced example does not exist: examples/{clean_e}")

        # 5. 文体（Imperative / 客観的指示）の検査 (指示手順部を対象とし、ユーザー発話例セクションは除外)
        instruction_body = re.sub(r"## Usage Scenarios & Trigger Examples.*?(?=##|\Z)", "", body_str, flags=re.DOTALL)
        second_person_patterns = [
            r"\byou should\b", r"\byou can\b", r"\byou must\b", r"\byou will\b",
            r"\bif you\b", r"\bplease\b", r"してください", r"してくださいね"
        ]
        for pat in second_person_patterns:
            matches = list(re.finditer(pat, instruction_body, re.IGNORECASE))
            if matches:
                res.add_warning("tone", f"Found conversational phrasing '{matches[0].group(0)}' in instructions. Use objective imperative instructions ('To accomplish X, do Y').")
                break

        # 6. Context Debt (大文字命令の乱用) 対策
        uppercase_imperatives = re.findall(r"\b(ALWAYS|NEVER|MUST NOT)\b", instruction_body)
        if len(uppercase_imperatives) >= 5:
            res.add_warning("context_debt", f"Detected frequent uppercase imperatives ({len(uppercase_imperatives)} occurrences: {set(uppercase_imperatives)}). 'Give the reason, not just the rule' to avoid context debt and improve generalization.")

        return res
