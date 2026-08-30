"""
Skill Packaging & Portability Utilities for edd-agent-tools

Anthropic Claude Skills / Google ADK 2.0 互換の ZIP パッケージ生成および整合性検証。
"""

import os
import sys
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..validation.validator import SkillValidator, ValidationResult


class SkillPackager:
    """スキルパッケージの作成、検証、および解凍を行うクラス。"""

    @classmethod
    def package(
        cls,
        skill_dir: str | Path,
        output_dir: Optional[str | Path] = None,
        validate: bool = True
    ) -> Path:
        """
        指定されたスキルディレクトリを Anthropic / Google ADK 準拠のポータブル ZIP パッケージに固めます。
        """
        skill_path = Path(skill_dir).resolve()
        if not skill_path.exists() or not skill_path.is_dir():
            raise FileNotFoundError(f"Skill directory not found: {skill_path}")

        skill_name = skill_path.name

        # 1. バリデーションの実行
        if validate:
            val_res = SkillValidator.validate_directory(skill_path)
            if not val_res.is_valid:
                err_msg = "\n".join(val_res.errors)
                raise ValueError(f"Cannot package invalid skill '{skill_name}':\n{err_msg}")

        # 2. 出力先の決定
        if output_dir:
            out_path = Path(output_dir).resolve()
        else:
            out_path = Path("dist").resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        zip_path = out_path / f"{skill_name}.zip"

        # 3. ZIP アーカイブの生成
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(skill_path):
                # 不要なキャッシュや隠しディレクトリを除外
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != "results"]
                for file in files:
                    if file.startswith(".") or file.endswith(".pyc"):
                        continue
                    full_path = Path(root) / file
                    # アーカイブ内では <skill-name>/... の相対パス
                    rel_to_skill = full_path.relative_to(skill_path)
                    arcname = Path(skill_name) / rel_to_skill
                    zf.write(full_path, arcname=str(arcname))

        return zip_path

    @classmethod
    def inspect_package(cls, zip_path: str | Path) -> Dict[str, Any]:
        """ZIP パッケージの内容と構造健全性を検査します。"""
        zpath = Path(zip_path).resolve()
        if not zpath.exists() or not zpath.is_file():
            raise FileNotFoundError(f"Package file not found: {zpath}")

        with zipfile.ZipFile(zpath, "r") as zf:
            names = zf.namelist()

        has_skill_md = any(n.endswith("SKILL.md") for n in names)
        scripts = [n for n in names if "/scripts/" in n and n.endswith(".py")]
        references = [n for n in names if "/references/" in n]
        assets = [n for n in names if "/assets/" in n]
        tests = [n for n in names if "/tests/" in n]

        return {
            "package_path": str(zpath),
            "file_count": len(names),
            "has_skill_md": has_skill_md,
            "scripts": scripts,
            "references": references,
            "assets": assets,
            "tests": tests,
            "is_valid_structure": has_skill_md
        }
