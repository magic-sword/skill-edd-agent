#!/usr/bin/env python3
"""
Quick validation script for skills - Zero-dependency minimal validator.

Usage:
    python quick_validate.py <skill_directory>
"""

import sys
import os
import re
import argparse
from pathlib import Path

def validate_skill(skill_path: str | Path) -> tuple[bool, list[str], list[str]]:
    """スキルの基本整合性を外部依存なしで高速に静的検証します。"""
    skill_path = Path(skill_path).resolve()
    errors = []
    warnings = []

    if not skill_path.exists() or not skill_path.is_dir():
        return False, [f"ディレクトリが存在しません: {skill_path}"], []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, [f"必須ファイル SKILL.md が見つかりません: {skill_md}"], []

    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"SKILL.md の読み込みに失敗しました: {e}"], []

    if not content.startswith("---"):
        return False, ["YAML Frontmatter の開始マーカー ('---') がありません"], []

    match = re.match(r"^---\n(.*?)\n---\n*(.*)$", content, re.DOTALL)
    if not match:
        return False, ["無効な YAML Frontmatter 境界フォーマットです"], []

    frontmatter_str = match.group(1)
    body_str = match.group(2)

    # 1. 必須フィールド (name, description) の検査
    name_match = re.search(r"^name:\s*([^\n]+)", frontmatter_str, re.MULTILINE)
    if not name_match:
        errors.append("Frontmatter に 'name' フィールドがありません")
    else:
        name = name_match.group(1).strip().strip("\"'")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
            errors.append(f"スキル名 '{name}' はハイフンケース（英小文字、数字、ハイフン）である必要があります")
        if skill_path.name != name:
            warnings.append(f"ディレクトリ名 '{skill_path.name}' とスキル名 '{name}' が一致していません")

    desc_match = re.search(r"^description:\s*([^\n]+)", frontmatter_str, re.MULTILINE)
    if not desc_match:
        errors.append("Frontmatter に 'description' フィールドがありません")
    else:
        description = desc_match.group(1).strip().strip("\"'")
        if "<" in description or ">" in description:
            errors.append("description に不等号 ('<' または '>') を含めることはできません")
        if not description.startswith("This skill should be used when"):
            warnings.append("description は 'This skill should be used when...' で開始することを推奨します")

    # 2. リソース参照の実在検査
    referenced_scripts = [s.rstrip(".,;:)[]`'\"") for s in re.findall(r"`?scripts/([a-zA-Z0-9_\-\./]+)", body_str)]
    for s in referenced_scripts:
        if s and not (skill_path / "scripts" / s).exists():
            errors.append(f"参照されているスクリプトが存在しません: scripts/{s}")

    referenced_refs = [r.rstrip(".,;:)[]`'\"") for r in re.findall(r"`?references/([a-zA-Z0-9_\-\./]+)", body_str)]
    for r in referenced_refs:
        if r and not (skill_path / "references" / r).exists():
            errors.append(f"参照されているドキュメントが存在しません: references/{r}")

    referenced_assets = [a.rstrip(".,;:)[]`'\"") for a in re.findall(r"`?assets/([a-zA-Z0-9_\-\./]+)", body_str)]
    for a in referenced_assets:
        if a and not (skill_path / "assets" / a).exists():
            errors.append(f"参照されているアセットが存在しません: assets/{a}")

    # 3. 未使用の空ディレクトリ検知
    for item in skill_path.iterdir():
        if item.is_dir() and item.name not in ["__pycache__", ".pytest_cache"]:
            files = [f for f in item.rglob("*") if f.is_file() and not f.name.endswith((".pyc", ".gitkeep"))]
            if not files:
                warnings.append(f"空のリソースディレクトリを検知しました: '{item.name}/'")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Zero-dependency quick validator for skills.")
    parser.add_argument("skill_directory", help="検証対象のスキルディレクトリパス")
    args = parser.parse_args()

    valid, errors, warnings = validate_skill(args.skill_directory)
    if warnings:
        print("⚠️ Warnings:")
        for w in warnings:
            print(f"  - {w}")

    if not valid:
        print("❌ Validation Failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"✅ Skill '{Path(args.skill_directory).name}' is valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
