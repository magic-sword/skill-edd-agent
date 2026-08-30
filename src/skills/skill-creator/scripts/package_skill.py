#!/usr/bin/env python3
"""
Zero-dependency Skill Packager CLI
スキルの静的検証を行い、配布用 ZIP パッケージを出力する決定論的スクリプト。
Anthropic 標準および Awesome Claude Skills の package_skill.py に完全準拠。
"""

import os
import sys
import argparse
import zipfile
from pathlib import Path

# 同一ディレクトリの quick_validate をインポート（Zero-dependency）
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from quick_validate import validate_skill
except ImportError:
    validate_skill = None


def package_skill(skill_dir: str | Path, output_dir: str | Path | None = None) -> Path | None:
    """指定されたスキルディレクトリを検証し、配布用 ZIP パッケージを生成します。

    Args:
        skill_dir: 対象スキルのルートディレクトリ。
        output_dir: 出力先ディレクトリ（省略時は 'dist/' 配下）。

    Returns:
        Path | None: 生成された ZIP ファイルのパス。検証失敗時は None。
    """
    skill_path = Path(skill_dir).resolve()
    skill_name = skill_path.name

    print(f"🔍 Validating skill '{skill_name}' before packaging...")
    if validate_skill:
        is_valid, errors, warnings = validate_skill(skill_path)
    else:
        is_valid, errors, warnings = True, [], []

    if warnings:
        print("\n⚠️ Warnings:")
        for w in warnings:
            print(f"  - {w}")

    if not is_valid:
        print("\n❌ Validation Failed with Errors:")
        for e in errors:
            print(f"  - {e}")
        print("\nFix validation errors before packaging.")
        return None

    out_path = Path(output_dir).resolve() if output_dir else skill_path.parent / "dist"
    out_path.mkdir(parents=True, exist_ok=True)
    zip_file = out_path / f"{skill_name}.zip"

    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_path):
            # 一時ファイルや不要ディレクトリの除外
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".pytest_cache", "results"]]
            for file in files:
                if file.endswith((".pyc", ".pyo", ".gitkeep")):
                    continue
                full_path = Path(root) / file
                arcname = full_path.relative_to(skill_path.parent)
                zf.write(full_path, arcname)

    print(f"\n📦 Successfully packaged skill '{skill_name}' to: {zip_file}")
    return zip_file


def main():
    parser = argparse.ArgumentParser(description="Zero-dependency skill packager CLI")
    parser.add_argument("skill", type=str, nargs="?", default="", help="Path to the skill directory (e.g. src/skills/pdf-tools)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output directory for the generated ZIP (default: ./dist)")
    args = parser.parse_args()

    if not args.skill:
        parser.print_help()
        sys.exit(1)

    res = package_skill(skill_dir=args.skill, output_dir=args.output)
    if not res:
        sys.exit(1)


if __name__ == "__main__":
    main()
